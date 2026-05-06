import type { Bridge } from "bridge.";
import type { Project } from "bridge.";

export interface ConversionResult {
  success: boolean;
  jobId?: string;
  error?: string;
  downloadUrl?: string;
}

export interface PluginConfig {
  apiEndpoint: string;
  apiKey?: string;
}

const DEFAULT_API_ENDPOINT = "https://api.portkit.com/api/v1/plugins";

export class PortKitPlugin {
  private config: PluginConfig;
  private bridge: Bridge | null = null;

  constructor(config: Partial<PluginConfig> = {}) {
    this.config = {
      apiEndpoint: config.apiEndpoint || DEFAULT_API_ENDPOINT,
      apiKey: config.apiKey,
    };
  }

  async onload(bridge: Bridge): Promise<void> {
    this.bridge = bridge;
    console.log("[PortKit] Plugin loaded successfully");

    this.registerActions();
    this.registerContextMenu();
  }

  private registerActions(): void {
    if (!this.bridge) return;

    this.bridge.action.registerAction({
      id: "portkit.convert",
      name: "Convert from Java",
      icon: "convert",
      description: "Convert a Java Edition mod to Bedrock Edition add-on",
      run: this.handleConvertAction.bind(this),
    });

    this.bridge.action.registerAction({
      id: "portkit.checkStatus",
      name: "Check Conversion Status",
      icon: "status",
      description: "Check the status of a PortKit conversion",
      run: this.handleStatusCheck.bind(this),
    });
  }

  private registerContextMenu(): void {
    if (!this.bridge) return;

    this.bridge.contextMenu.registerItem({
      id: "portkit.contextMenu.convert",
      name: "Convert to Bedrock",
      icon: "convert",
      filter: [{ type: "file", extensions: [".jar", ".zip"] }],
      run: this.handleConvertAction.bind(this),
    });
  }

  private async handleConvertAction(project: Project): Promise<void> {
    const selectedFiles = this.getSelectedFiles(project);

    if (selectedFiles.length === 0) {
      await this.showNotification("No mod file selected", "Please select a .jar or .zip file to convert.");
      return;
    }

    const file = selectedFiles[0];
    await this.convertFile(file.path, file.name);
  }

  private async handleStatusCheck(project: Project): Promise<void> {
    const jobId = await this.bridge?.storage.get("portkit_last_job_id");

    if (!jobId) {
      await this.showNotification("No conversion found", "No recent conversion job found.");
      return;
    }

    await this.checkConversionStatus(jobId);
  }

  private getSelectedFiles(project: Project): Array<{ path: string; name: string }> {
    const selected = project.browser.getSelectedFiles?.() || [];
    return selected.map((f: any) => ({
      path: f.path || f,
      name: f.name || f.path?.split("/").pop() || "unknown",
    }));
  }

  private async convertFile(filePath: string, fileName: string): Promise<void> {
    if (!this.bridge) return;

    try {
      await this.showNotification("Conversion started", `Converting ${fileName}...`);

      const fileData = await this.readFileAsBase64(filePath);
      const response = await this.callPortKitAPI({
        plugin_type: "bridge",
        file_data: fileData,
        file_name: fileName,
        target_version: "1.20.0",
      });

      if (response.job_id) {
        await this.bridge.storage.set("portkit_last_job_id", response.job_id);
        await this.pollConversionStatus(response.job_id, fileName);
      }
    } catch (error) {
      console.error("[PortKit] Conversion failed:", error);
      await this.showNotification(
        "Conversion failed",
        error instanceof Error ? error.message : "Unknown error occurred"
      );
    }
  }

  private async callPortKitAPI(data: {
    plugin_type: string;
    file_data: string;
    file_name: string;
    target_version: string;
  }): Promise<{ job_id?: string; status?: string; message?: string; error?: string }> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };

    if (this.config.apiKey) {
      headers["Authorization"] = `Bearer ${this.config.apiKey}`;
    }

    const response = await fetch(`${this.config.apiEndpoint}/convert`, {
      method: "POST",
      headers,
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`API error ${response.status}: ${errorText}`);
    }

    return response.json();
  }

  private async pollConversionStatus(jobId: string, fileName: string, maxAttempts = 60): Promise<void> {
    let attempts = 0;

    while (attempts < maxAttempts) {
      const status = await this.checkConversionStatus(jobId, true);

      if (status.completed) {
        await this.handleConversionComplete(jobId, fileName);
        return;
      }

      if (status.failed) {
        await this.showNotification(
          "Conversion failed",
          status.error || "The conversion process encountered an error."
        );
        return;
      }

      await this.delay(2000);
      attempts++;
    }

    await this.showNotification("Conversion timeout", "The conversion is taking longer than expected.");
  }

  private async checkConversionStatus(
    jobId: string,
    silent = false
  ): Promise<{ completed: boolean; failed: boolean; error?: string; downloadUrl?: string }> {
    try {
      const response = await fetch(
        `${this.config.apiEndpoint}/convert/${jobId}/status`,
        {
          method: "GET",
          headers: {
            "Content-Type": "application/json",
            ...(this.config.apiKey ? { Authorization: `Bearer ${this.config.apiKey}` } : {}),
          },
        }
      );

      if (!response.ok) {
        throw new Error(`Status check failed: ${response.status}`);
      }

      const data = await response.json();

      if (!silent) {
        await this.showNotification(
          "Conversion status",
          `Status: ${data.status}, Progress: ${data.progress}%`
        );
      }

      return {
        completed: data.status === "completed",
        failed: data.status === "failed",
        error: data.error,
        downloadUrl: data.result_url,
      };
    } catch (error) {
      console.error("[PortKit] Status check failed:", error);
      return {
        completed: false,
        failed: true,
        error: error instanceof Error ? error.message : "Unknown error",
      };
    }
  }

  private async handleConversionComplete(jobId: string, originalFileName: string): Promise<void> {
    if (!this.bridge) return;

    const baseName = originalFileName.replace(/\.(jar|zip)$/i, "");
    const downloadFileName = `${baseName}_converted.mcaddon`;

    try {
      const response = await fetch(`${this.config.apiEndpoint}/convert/${jobId}/download`);

      if (!response.ok) {
        throw new Error(`Download failed: ${response.status}`);
      }

      const blob = await response.blob();
      const outputPath = await this.saveConvertedFile(blob, downloadFileName);

      await this.showNotification(
        "Conversion complete!",
        `Saved to: ${outputPath}`
      );

      const project = this.bridge.project.getCurrentProject?.();
      if (project) {
        await project.importFile?.(outputPath);
      }
    } catch (error) {
      console.error("[PortKit] Download failed:", error);
      await this.showNotification(
        "Download failed",
        error instanceof Error ? error.message : "Could not download converted file"
      );
    }
  }

  private async readFileAsBase64(filePath: string): Promise<string> {
    const response = await fetch(`file://${filePath}`);
    const blob = await response.blob();
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const result = reader.result as string;
        resolve(result.split(",")[1]);
      };
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
  }

  private async saveConvertedFile(blob: Blob, fileName: string): Promise<string> {
    const path = await this.bridge?.dialog.showSaveDialog?.({
      defaultPath: fileName,
      filters: [{ name: "Minecraft Add-on", extensions: ["mcaddon"] }],
    });

    if (!path) {
      throw new Error("Save cancelled");
    }

    const buffer = await blob.arrayBuffer();
    await this.writeFile(path, new Uint8Array(buffer));

    return path;
  }

  private async writeFile(path: string, data: Uint8Array): Promise<void> {
    const stream = new WritableStream({
      write(chunk) {
        const blob = new Blob([chunk]);
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = path.split("/").pop() || "file";
        a.click();
        URL.revokeObjectURL(url);
      },
    });

    await stream.getWriter().write(data);
  }

  private async showNotification(title: string, message: string): Promise<void> {
    if (this.bridge?.notification) {
      await this.bridge.notification.show({
        title,
        message,
        duration: 5000,
      });
    } else {
      console.log(`[PortKit] ${title}: ${message}`);
    }
  }

  private delay(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  onunload(): void {
    console.log("[PortKit] Plugin unloaded");
  }
}

export default PortKitPlugin;