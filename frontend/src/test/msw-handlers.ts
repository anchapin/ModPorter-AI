import { http, HttpResponse, ws } from 'msw';
import { ConversionStatusEnum } from '../types/api';

const API_BASE_URL = 'http://localhost:8000/api/v1'; // Assuming this is the base URL

// Create server instance for WebSocket handling
let globalServer: any = null;

let conversionState: {
  status: ConversionStatusEnum;
  progress: number;
  conversionId?: string;
  error?: string | null;
  originalFilename?: string;
} = {
  status: ConversionStatusEnum.PENDING,
  progress: 0,
  error: null,
  originalFilename: undefined,
};

export const resetConversionState = () => {
  conversionState = {
    status: ConversionStatusEnum.PENDING,
    progress: 0,
    conversionId: undefined,
    error: null,
    originalFilename: undefined,
  };
};

export const setServerConversionId = (id: string) => {
  conversionState.conversionId = id;
};

export const handlers = [
  // Handles a GET /health request (backend health check)
  http.get(`${API_BASE_URL}/health`, () => {
    return HttpResponse.json({
      status: 'healthy',
      version: '1.0.0',
      timestamp: new Date().toISOString(),
    });
  }),

  // Handles a POST /api/v1/upload request
  http.post(`${API_BASE_URL}/upload`, async ({ request }) => {
    const formData = await request.formData();
    const file = formData.get('file') as File;

    if (!file) {
      return HttpResponse.json({ detail: 'No file provided' }, { status: 400 });
    }

    // Validate file type
    const allowedTypes = ['application/java-archive', 'application/zip', 'application/x-mcaddon'];
    if (!allowedTypes.includes(file.type)) {
      return HttpResponse.json({ detail: 'Invalid file type' }, { status: 400 });
    }

    const fileId = `mock-file-${Date.now()}`;
    // Use the filename from file, but fallback to a known value for test
    const filename = file.name === 'blob' ? 'test-mod.jar' : file.name;
    return HttpResponse.json({
      file_id: fileId,
      original_filename: filename,
      saved_filename: `${fileId}.jar`,
      size: file.size,
      content_type: file.type,
      message: `File '${filename}' saved successfully`,
    });
  }),

  // Handles a POST /api/v1/convert request
  http.post(`${API_BASE_URL}/convert`, async ({ request }) => {
    resetConversionState(); // Reset state for new conversion
    const body = await request.json() as { file_id: string; original_filename: string; target_version?: string; options?: any };
    
    if (!body.file_id || !body.original_filename) {
      return HttpResponse.json({ detail: 'file_id and original_filename are required' }, { status: 422 });
    }

    conversionState.conversionId = `mock-${Date.now()}`;
    conversionState.status = ConversionStatusEnum.PENDING; // Or ANALYZING if it starts quickly
    conversionState.progress = 10;
    conversionState.originalFilename = body.original_filename;

    return HttpResponse.json({
      job_id: conversionState.conversionId,
      status: conversionState.status,
      message: 'Conversion started',
      progress: conversionState.progress,
      overallSuccessRate: 0,
      convertedMods: [],
      failedMods: [],
      smartAssumptionsApplied: [],
      detailedReport: { stage: 'Pending', progress: 0, logs: [], technicalDetails: {} },
    });
  }),

  // Handles a GET /api/v1/convert/:id/status request
  http.get(`${API_BASE_URL}/convert/:id/status`, ({ params }) => {
    const { id } = params;
    if (id !== conversionState.conversionId) {
      return HttpResponse.json({ detail: 'Conversion not found' }, { status: 404 });
    }

    // Simulate progress
    if (conversionState.status === ConversionStatusEnum.PENDING) {
      conversionState.status = ConversionStatusEnum.ANALYZING;
      conversionState.progress = 25;
    } else if (conversionState.status === ConversionStatusEnum.ANALYZING) {
      conversionState.status = ConversionStatusEnum.CONVERTING;
      conversionState.progress = 50;
    } else if (conversionState.status === ConversionStatusEnum.CONVERTING) {
      conversionState.status = ConversionStatusEnum.PACKAGING;
      conversionState.progress = 75;
    } else if (conversionState.status === ConversionStatusEnum.PACKAGING) {
      conversionState.status = ConversionStatusEnum.COMPLETED;
      conversionState.progress = 100;
    }

    return HttpResponse.json({
      job_id: conversionState.conversionId,
      status: conversionState.status,
      progress: conversionState.progress,
      message: `Status: ${conversionState.status}`,
      stage: conversionState.status,
      created_at: new Date().toISOString(),
      // Other fields can be added as needed for COMPLETED state
      overallSuccessRate: conversionState.status === ConversionStatusEnum.COMPLETED ? 100 : 0,
      convertedMods: conversionState.status === ConversionStatusEnum.COMPLETED ? [{ name: 'Test Mod', version: '1.0', status: 'success', features: [], warnings: [] }] : [],
      failedMods: [],
      smartAssumptionsApplied: [],
      error: conversionState.error,
      detailedReport: { stage: conversionState.status, progress: conversionState.progress, logs: [], technicalDetails: {} },
    });
  }),

  // Handles a GET /api/v1/convert/:id/download request
  http.get(`${API_BASE_URL}/convert/:id/download`, ({ params }) => {
    const { id } = params;
    if (id !== conversionState.conversionId || conversionState.status !== ConversionStatusEnum.COMPLETED) {
      return HttpResponse.json({ detail: 'File not ready or not found' }, { status: 404 });
    }
    
    // Generate user-friendly filename from original filename
    const originalFilename = conversionState.originalFilename || 'unknown';
    const originalFilenameBase = originalFilename.split('.').slice(0, -1).join('.') || 'converted-mod';
    const downloadFilename = `${originalFilenameBase}_converted.mcaddon`;
    
    const blob = new Blob(['mock file content'], { type: 'application/octet-stream' });
    return new HttpResponse(blob, {
        headers: {
            'Content-Type': 'application/octet-stream',
            'Content-Disposition': `attachment; filename="${downloadFilename}"`,
        }
    });
  }),

  // Handles a DELETE /api/v1/convert/:id request
  http.delete(`${API_BASE_URL}/convert/:id`, ({ params }) => {
    const { id } = params;
    if (id !== conversionState.conversionId) {
      return HttpResponse.json({ detail: 'Conversion not found' }, { status: 404 });
    }
    conversionState.status = ConversionStatusEnum.CANCELLED;
    conversionState.progress = 0; // Or whatever progress it was at
    return HttpResponse.json(null, { status: 204 }); // No content
  }),

  // Handles a POST /api/v1/feedback request
  http.post(`${API_BASE_URL}/feedback`, async ({ request }) => {
    const body = await request.json();
    if (!body.feedback_type) {
      return HttpResponse.json({ detail: 'Feedback type is required' }, { status: 400 });
    }
    return HttpResponse.json({ message: 'Feedback submitted successfully' }, { status: 200 });
  }),

  // WebSocket handlers for conversion progress
  ws.link('ws://localhost:8080/ws/v1/convert/:jobId/progress', async ({ data, clientId }) => {
    const jobId = data.url.match(/\/ws\/v1\/convert\/(.+?)\/progress/)?.[1];
    if (!jobId) return;
    
    // Simulate progress updates
    const sendData = () => {
      const currentProgress = conversionState.progress + 10;
      if (currentProgress <= 100) {
        conversionState.progress = currentProgress;
        conversionState.status = currentProgress >= 100 ? ConversionStatusEnum.COMPLETED : ConversionStatusEnum.RUNNING;
        
        globalServer.send(clientId, {
          type: 'progress_update',
          data: {
            job_id: jobId,
            status: conversionState.status,
            progress: conversionState.progress,
            message: conversionState.status === ConversionStatusEnum.COMPLETED ? 'Conversion completed!' : 'Processing...',
            stage: conversionState.status === ConversionStatusEnum.COMPLETED ? 'Completed' : 'Processing',
          },
        });
        
        if (conversionState.status === ConversionStatusEnum.COMPLETED) {
          setTimeout(() => globalServer.close(clientId), 100);
          return;
        }
      }
    };

    // Send initial progress
    sendData();
    
    // Continue sending progress updates
    const interval = setInterval(sendData, 1000);
    
    // Store interval for cleanup
    (conversionState as any).interval = interval;
  }),
];

// Store server reference globally for WebSocket handlers
(global as any).server = globalServer;

// Export server for use in setup
export { globalServer as server };
