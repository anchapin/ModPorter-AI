import time
import psutil # This library might be useful for system metrics.

class PerformanceMetricsCollector:
    def __init__(self):
        print("PerformanceMetricsCollector initialized.")
        # Potentially initialize connections to game clients or monitoring tools if necessary

    def _get_process_info(self, process_name_keyword=None):
        """Helper to find a process by keyword (e.g., 'java', 'bedrock_server')."""
        if not process_name_keyword:
            return None
        for proc in psutil.process_iter(['pid', 'name', 'username']):
            try:
                # Check if process name contains the keyword (case-insensitive)
                if process_name_keyword.lower() in proc.info['name'].lower():
                    return proc
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                # These exceptions can occur if a process terminates while iterating
                pass
        print(f"Process with keyword '{process_name_keyword}' not found.")
        return None

    def collect_cpu_metrics(self, process_keyword=None):
        """Collects CPU metrics, optionally for a specific process."""
        # print(f"Collecting CPU metrics (process keyword: {process_keyword})...")
        target_process = self._get_process_info(process_keyword)
        if target_process:
            try:
                # cpu_percent can be blocking, interval=0.1 for a short sample
                cpu_percent = target_process.cpu_percent(interval=0.1)
                cpu_times = target_process.cpu_times()
                return {
                    "process_cpu_usage_percent": cpu_percent,
                    "process_cpu_time_user_seconds": cpu_times.user,
                    "process_cpu_time_system_seconds": cpu_times.system,
                    "process_num_threads": target_process.num_threads()
                }
            except psutil.NoSuchProcess:
                # print(f"Process with keyword '{process_keyword}' not found during CPU metric collection.")
                return {"error": f"Process {process_keyword} not found"}
            except Exception as e:
                # print(f"Error collecting CPU metrics for process '{process_keyword}': {e}")
                return {"error": str(e)}
        else:
            # System-wide CPU metrics if no process specified or process not found
            cpu_percent_system = psutil.cpu_percent(interval=0.1)
            # Initialize cpu_times_system to avoid potential UnboundLocalError
            cpu_times_system = None
            try:
                cpu_times_system = psutil.cpu_times_percent(interval=0.1)
                # It's possible the first call to cpu_times_percent after system boot or with a very short interval might return None
                # or not have all attributes. Adding a small delay and retrying once if needed.
                if cpu_times_system is None:
                    time.sleep(0.1)
                    cpu_times_system = psutil.cpu_times_percent(interval=0.1)
            except Exception as e:
                # print(f"Could not retrieve system CPU times percent: {e}")
                pass # Continue with what we have, or defaults

            return {
                "system_cpu_usage_percent": cpu_percent_system,
                "system_cpu_time_user_percent": cpu_times_system.user if hasattr(cpu_times_system, 'user') else 'N/A',
                "system_cpu_time_system_percent": cpu_times_system.system if hasattr(cpu_times_system, 'system') else 'N/A',
                "system_cpu_time_idle_percent": cpu_times_system.idle if hasattr(cpu_times_system, 'idle') else 'N/A'
            }

    def collect_memory_metrics(self, process_keyword=None):
        """Collects memory metrics, optionally for a specific process."""
        # print(f"Collecting memory metrics (process keyword: {process_keyword})...")
        target_process = self._get_process_info(process_keyword)
        if target_process:
            try:
                memory_info = target_process.memory_info()
                memory_percent = target_process.memory_percent()
                return {
                    "process_rss_mb": memory_info.rss / (1024 * 1024), # Resident Set Size
                    "process_vms_mb": memory_info.vms / (1024 * 1024), # Virtual Memory Size
                    "process_memory_percent": memory_percent
                }
            except psutil.NoSuchProcess:
                # print(f"Process with keyword '{process_keyword}' not found for memory metrics.")
                return {"error": f"Process {process_keyword} not found"}
            except Exception as e:
                # print(f"Error collecting memory metrics for process '{process_keyword}': {e}")
                return {"error": str(e)}
        else:
            # System-wide memory metrics
            virtual_mem = psutil.virtual_memory()
            swap_mem = psutil.swap_memory()
            return {
                "system_total_memory_mb": virtual_mem.total / (1024 * 1024),
                "system_available_memory_mb": virtual_mem.available / (1024 * 1024),
                "system_used_memory_percent": virtual_mem.percent,
                "system_swap_total_mb": swap_mem.total / (1024 * 1024) if swap_mem.total > 0 else 0,
                "system_swap_used_mb": swap_mem.used / (1024 * 1024) if swap_mem.total > 0 else 0,
                "system_swap_free_mb": swap_mem.free / (1024 * 1024) if swap_mem.total > 0 else 0,
                "system_swap_percent_used": swap_mem.percent if swap_mem.total > 0 else 0,
            }

    def collect_network_metrics(self, process_keyword=None):
        """Collects network metrics. Process-specific network I/O is generally not provided by psutil directly."""
        # print(f"Collecting network metrics (process keyword: {process_keyword})...")
        if process_keyword:
            # print(f"Note: Per-process network metrics for '{process_keyword}' are complex. Reporting system-wide stats.")
            pass

        try:
            net_io_counters = psutil.net_io_counters() # System-wide I/O
            return {
                "system_bytes_sent_mb": net_io_counters.bytes_sent / (1024*1024),
                "system_bytes_received_mb": net_io_counters.bytes_recv / (1024*1024),
                "system_packets_sent": net_io_counters.packets_sent,
                "system_packets_received": net_io_counters.packets_recv,
                "system_errors_in": net_io_counters.errin,
                "system_errors_out": net_io_counters.errout,
                "system_dropped_in": net_io_counters.dropin,
                "system_dropped_out": net_io_counters.dropout,
                "latency_ms": "not_implemented" # Placeholder
            }
        except Exception as e:
            # print(f"Error collecting network metrics: {e}")
            return {"error": str(e)}

    def collect_frame_rate_metrics(self):
        """Placeholder for collecting frame rate (FPS). Requires game client integration."""
        # print("Collecting frame rate metrics (placeholder)...")
        return {"fps_average": "not_implemented", "fps_min": "not_implemented", "fps_max": "not_implemented"}

    def collect_load_time_metrics(self, feature_name="general_load"):
        """Placeholder for collecting load times. Requires specific instrumentation points."""
        # print(f"Collecting load time metrics for '{feature_name}' (placeholder)...")
        return {f"{feature_name}_time_seconds": "not_implemented"}

    def collect_response_time_metrics(self, interaction_name="general_interaction"):
        """Placeholder for collecting response times. Requires UI or API interaction hooks."""
        # print(f"Collecting response time metrics for '{interaction_name}' (placeholder)...")
        return {f"{interaction_name}_response_ms": "not_implemented"}

    def collect_all_metrics_for_target(self, target_name="unknown", process_keyword=None):
        """Collects a standard set of metrics for a given target (e.g., 'java' or 'bedrock')."""
        # print(f"Collecting all metrics for target: {target_name} (process keyword: {process_keyword})")
        metrics = {
            "cpu": self.collect_cpu_metrics(process_keyword=process_keyword),
            "memory": self.collect_memory_metrics(process_keyword=process_keyword),
            "network": self.collect_network_metrics(process_keyword=process_keyword),
            "frame_rate": self.collect_frame_rate_metrics(),
            "load_time": self.collect_load_time_metrics(feature_name=f"{target_name}_load"),
            "response_time": self.collect_response_time_metrics(interaction_name=f"{target_name}_interaction")
        }
        return metrics

    def get_system_context_metrics(self):
        """Collects general system-wide metrics for context."""
        # print("Collecting system-wide context metrics...")
        return {
            "system_cpu_overview": self.collect_cpu_metrics(),
            "system_memory_overview": self.collect_memory_metrics(),
            "system_network_overview": self.collect_network_metrics()
        }

if __name__ == '__main__':
    collector = PerformanceMetricsCollector()

    print("\n--- Collecting System-Wide Context Metrics ---")
    system_context = collector.get_system_context_metrics()
    import json
    print(json.dumps(system_context, indent=2))

    print("\n--- Collecting Metrics for a Hypothetical 'python' Process (likely this script itself) ---")
    python_metrics = collector.collect_all_metrics_for_target(target_name="python_script", process_keyword="python")
    print(json.dumps(python_metrics, indent=2))

    print("\n--- Collecting Metrics for a non-existent 'nonexistentproc123' Process ---")
    non_existent_metrics = collector.collect_all_metrics_for_target(target_name="nonexistent", process_keyword="nonexistentproc123")
    print(json.dumps(non_existent_metrics, indent=2))

    print("\n--- Direct call examples ---")
    print("CPU (system):", json.dumps(collector.collect_cpu_metrics(), indent=2))
    print("Memory (system):", json.dumps(collector.collect_memory_metrics(), indent=2))
    # print("CPU (Java):", json.dumps(collector.collect_cpu_metrics(process_keyword="java"), indent=2))
