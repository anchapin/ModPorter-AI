import json # Added for potential debugging and for __main__
from .metrics_collector import PerformanceMetricsCollector as ExternalPerformanceMetricsCollector
# Note: The above import assumes metrics_collector.py is in the same directory (benchmarking)
# If it's ai_engine.src.benchmarking.metrics_collector, the import path might need adjustment
# based on how Python resolves modules in this project structure.
# For now, proceeding with the relative import.
import time
import os

class BenchmarkExecutor:
    def __init__(self):
        self.benchmark_results = {}
        self.active_benchmarks = {}

    def run_benchmark(self, scenario):
        """
        Execute performance benchmark for given scenario

        Args:
            scenario (dict): Benchmark scenario configuration

        Returns:
            dict: Performance metrics and results
        """
        scenario_id = scenario.get('scenario_id', 'unknown')
        scenario_name = scenario.get('scenario_name', 'Unknown Scenario')

        print(f"Running benchmark for scenario: {scenario_name} (ID: {scenario_id})")

        # Initialize results structure
        results = {
            'scenario_id': scenario_id,
            'scenario_name': scenario_name,
            'start_time': time.time(),
            'metrics': {},
            'status': 'running'
        }

        try:
            # Extract scenario parameters
            parameters = scenario.get('parameters', {})
            parameters.get('duration_seconds', 60)
            parameters.get('target_load', 'medium')

            # Simulate different benchmark types
            if scenario.get('type') == 'conversion':
                results['metrics'] = self._run_conversion_benchmark(scenario)
            elif scenario.get('type') == 'load':
                results['metrics'] = self._run_load_benchmark(scenario)
            elif scenario.get('type') == 'memory':
                results['metrics'] = self._run_memory_benchmark(scenario)
            else:
                results['metrics'] = self._run_generic_benchmark(scenario)

            results['status'] = 'completed'
            results['success'] = True

        except Exception as e:
            results['status'] = 'failed'
            results['error'] = str(e)
            results['success'] = False

        finally:
            results['end_time'] = time.time()
            results['duration'] = results['end_time'] - results['start_time']

        # Store results
        self.benchmark_results[scenario_id] = results

        return results

    def _run_conversion_benchmark(self, scenario):
        """Benchmark mod conversion performance"""
        parameters = scenario.get('parameters', {})
        mod_size = parameters.get('mod_size_mb', 10)
        complexity = parameters.get('complexity', 'medium')

        # Simulate conversion metrics
        base_time = mod_size * 2  # 2 seconds per MB base
        complexity_multiplier = {'simple': 0.5, 'medium': 1.0, 'complex': 2.0}.get(complexity, 1.0)

        processing_time = base_time * complexity_multiplier
        memory_usage = 50 + (mod_size * 5)  # MB

        return {
            'processing_time_seconds': processing_time,
            'memory_usage_mb': memory_usage,
            'cpu_usage_percent': min(90, 30 + (mod_size * 2)),
            'conversion_rate_mb_per_sec': mod_size / max(processing_time, 0.1),
            'success_rate': 0.95 + (0.04 * (1 / complexity_multiplier)),
            'files_processed': int(mod_size * 10),
            'errors_detected': max(0, int(mod_size * 0.1 * (1 - complexity_multiplier)))
        }

    def _run_load_benchmark(self, scenario):
        """Benchmark system under load"""
        parameters = scenario.get('parameters', {})
        concurrent_users = parameters.get('concurrent_users', 10)
        request_rate = parameters.get('requests_per_second', 100)

        # Simulate load test metrics
        base_latency = 50  # ms
        latency_increase = concurrent_users * 2  # ms per user
        avg_latency = base_latency + latency_increase

        return {
            'avg_response_time_ms': avg_latency,
            'p95_response_time_ms': avg_latency * 1.5,
            'p99_response_time_ms': avg_latency * 2.0,
            'throughput_rps': min(request_rate, 1000 / (avg_latency / 1000)),
            'cpu_usage_percent': min(95, 40 + (concurrent_users * 3)),
            'memory_usage_mb': 100 + (concurrent_users * 10),
            'error_rate_percent': max(0, (avg_latency - 200) / 100),
            'concurrent_users_handled': concurrent_users
        }

    def _run_memory_benchmark(self, scenario):
        """Benchmark memory usage patterns"""
        parameters = scenario.get('parameters', {})
        data_size = parameters.get('data_size_mb', 100)
        iterations = parameters.get('iterations', 1000)

        # Simulate memory metrics
        peak_memory = data_size * 1.5  # 50% overhead
        memory_efficiency = min(0.95, 0.7 + (1000 / iterations) * 0.1)

        return {
            'peak_memory_usage_mb': peak_memory,
            'avg_memory_usage_mb': peak_memory * 0.8,
            'memory_efficiency_percent': memory_efficiency * 100,
            'gc_frequency_per_minute': max(1, iterations / 100),
            'memory_leaks_detected': 0 if memory_efficiency > 0.9 else 1,
            'allocation_rate_mb_per_sec': data_size / 60,  # Assume 1 minute test
            'deallocation_rate_mb_per_sec': (data_size * memory_efficiency) / 60
        }

    def _run_generic_benchmark(self, scenario):
        """Generic benchmark for unknown scenarios"""
        return {
            'cpu_usage_percent': 45,
            'memory_usage_mb': 200,
            'disk_io_mb_per_sec': 50,
            'network_io_mb_per_sec': 25,
            'response_time_ms': 100,
            'throughput_ops_per_sec': 150,
            'error_rate_percent': 1.0,
            'availability_percent': 99.9
        }

# The old internal PerformanceMetricsCollector class is no longer needed here,
# as PerformanceBenchmarkingSystem now uses ExternalPerformanceMetricsCollector.
# Removing the old class definition.

class LoadTestGenerator:
    def __init__(self):
        self.active_loads = {}
        self.load_generators = {
            'cpu': self._generate_cpu_load,
            'memory': self._generate_memory_load,
            'io': self._generate_io_load,
            'network': self._generate_network_load,
            'entity': self._generate_entity_load
        }

    def generate_load(self, scenario):
        """Generates a simulated load based on scenario parameters."""
        scenario_name = scenario.get('scenario_name', 'Unknown Scenario')
        parameters = scenario.get('parameters', {})
        load_level = parameters.get('load_level', 'moderate')
        entity_count = parameters.get('entity_count')
        stress_type = scenario.get('type', 'general')

        print(f"Generating load for scenario: '{scenario_name}' (Type: {stress_type}, Level: {load_level})")

        load_details = {"load_level": load_level}

        if entity_count is not None:
            print(f"  Simulating {entity_count} entities of type '{parameters.get('entity_type', 'generic')}'")
            if parameters.get('enable_ai', False):
                print("    Entity AI enabled.")
            if parameters.get('start_interactions', False):
                print("    Simulating entity interactions.")
            load_details["entity_simulation"] = {
                "count": entity_count,
                "type": parameters.get('entity_type', 'generic'),
                "ai_enabled": parameters.get('enable_ai', False),
                "interactions_started": parameters.get('start_interactions', False)
            }

        if load_level == "none":
            print("  No active load generation requested for this baseline scenario.")
            load_details["status"] = "No active load generated (baseline)."
        elif load_level == "high":
            print("  Simulating high resource utilization (e.g., complex calculations, frequent I/O).")
            load_details["status"] = "High load simulation initiated."
        else: # moderate or other
            print("  Simulating moderate resource utilization.")
            load_details["status"] = "Moderate load simulation initiated."

        print("Load generation simulation complete.")
        return {"load_generated": True, "details": load_details}

    def _generate_cpu_load(self, intensity, duration_seconds):
        """Generate CPU load for testing"""
        print(f"Generating CPU load: intensity={intensity}, duration={duration_seconds}s")

        # Simulate CPU-intensive work
        start_time = time.time()
        operations_per_second = intensity * 1000000  # Millions of operations

        while time.time() - start_time < duration_seconds:
            # Perform CPU-intensive calculations
            sum(i * i for i in range(1000))
            # Small delay to control intensity
            if intensity < 0.8:
                time.sleep(0.001 * (1 - intensity))

        return {"cpu_cycles": operations_per_second * duration_seconds, "intensity": intensity}

    def _generate_memory_load(self, size_mb, duration_seconds):
        """Generate memory load for testing"""
        print(f"Generating memory load: size={size_mb}MB, duration={duration_seconds}s")

        # Allocate memory to simulate load
        data_chunks = []
        chunk_size = 1024 * 1024  # 1MB chunks
        num_chunks = int(size_mb)

        try:
            for i in range(num_chunks):
                # Allocate 1MB chunk
                chunk = bytearray(chunk_size)
                # Fill with some data to ensure it's actually allocated
                for j in range(0, chunk_size, 4096):
                    chunk[j] = i % 256
                data_chunks.append(chunk)

            # Hold memory for specified duration
            time.sleep(duration_seconds)

            return {
                "memory_allocated_mb": size_mb,
                "chunks_allocated": len(data_chunks),
                "duration_seconds": duration_seconds
            }

        finally:
            # Clean up memory
            data_chunks.clear()

    def _generate_io_load(self, operations, duration_seconds):
        """Generate I/O load for testing"""
        print(f"Generating I/O load: operations={operations}, duration={duration_seconds}s")

        import tempfile
        import os

        temp_files = []
        start_time = time.time()

        try:
            # Perform file I/O operations
            for i in range(min(operations, 100)):  # Limit to prevent disk filling
                with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                    temp_files.append(tmp_file.name)
                    # Write data
                    data = os.urandom(1024 * 100)  # 100KB of random data
                    tmp_file.write(data)
                    tmp_file.flush()
                    os.fsync(tmp_file.fileno())  # Force write to disk

                    # Read data back
                    tmp_file.seek(0)
                    read_data = tmp_file.read()

                    # Verify data integrity
                    if len(read_data) != len(data):
                        raise IOError("Data integrity check failed")

            # Calculate I/O metrics
            total_data_mb = (operations * 100) / (1024 * 1024)  # Convert to MB
            actual_duration = time.time() - start_time

            return {
                "io_operations": min(operations, 100),
                "data_processed_mb": total_data_mb,
                "duration_seconds": actual_duration,
                "throughput_mb_per_sec": total_data_mb / max(actual_duration, 0.1)
            }

        finally:
            # Clean up temporary files
            for temp_file in temp_files:
                try:
                    os.unlink(temp_file)
                except (OSError, FileNotFoundError):
                    pass

    def _generate_network_load(self, bandwidth_mbps, duration_seconds):
        """Generate network load for testing"""
        print(f"Generating network load: bandwidth={bandwidth_mbps}Mbps, duration={duration_seconds}s")

        # Simulate network operations
        packets_per_second = bandwidth_mbps * 1000  # Approximate packets
        packet_size = 1500  # bytes

        total_packets = int(packets_per_second * duration_seconds)
        simulated_latency = 50  # ms

        # Simulate network operations
        start_time = time.time()
        packets_sent = 0

        while time.time() - start_time < duration_seconds and packets_sent < total_packets:
            # Simulate packet transmission
            os.urandom(packet_size)

            # Simulate network latency
            time.sleep(simulated_latency / 1000)

            packets_sent += 1

        actual_duration = time.time() - start_time
        data_sent_mb = (packets_sent * packet_size) / (1024 * 1024)

        return {
            "packets_sent": packets_sent,
            "data_sent_mb": data_sent_mb,
            "duration_seconds": actual_duration,
            "actual_bandwidth_mbps": (data_sent_mb * 8) / max(actual_duration, 0.1)
        }

    def _generate_entity_load(self, entity_count, complexity_level):
        """Generate entity-based load for Minecraft-like scenarios"""
        print(f"Generating entity load: count={entity_count}, complexity={complexity_level}")

        # Simulate entity processing
        entities = []
        start_time = time.time()

        for i in range(entity_count):
            # Create entity data structure
            entity = {
                'id': i,
                'position': (i % 100, (i // 100) % 100, (i // 10000) % 100),
                'velocity': (0, 0, 0),
                'health': 100,
                'type': f'entity_type_{i % 10}',
                'active': True
            }
            entities.append(entity)

            # Simulate entity AI/processing based on complexity
            if complexity_level == 'high':
                # Complex AI calculations
                for j in range(100):
                    entity['position'] = (
                        entity['position'][0] + 0.1,
                        entity['position'][1],
                        entity['position'][2]
                    )
            elif complexity_level == 'medium':
                # Medium complexity
                for j in range(10):
                    entity['health'] = max(0, entity['health'] - 1)
            else:
                # Simple processing
                entity['active'] = i % 2 == 0

        processing_time = time.time() - start_time

        return {
            'entities_processed': len(entities),
            'processing_time_seconds': processing_time,
            'entities_per_second': len(entities) / max(processing_time, 0.001),
            'complexity_level': complexity_level
        }

    def stop_load(self, load_id):
        """Stop active load generation"""
        if load_id in self.active_loads:
            load_info = self.active_loads[load_id]
            load_info['stopped'] = True
            load_info['stop_time'] = time.time()
            return True
        return False

    def get_active_loads(self):
        """Get information about active loads"""
        return self.active_loads.copy()

class PerformanceAnalyzer:
    def __init__(self):
        print("PerformanceAnalyzer initialized.")
        # Define some basic thresholds (these could be configurable later)
        self.thresholds = {
            "max_cpu_usage_percent": 80.0,
            "max_memory_usage_percent_process": 70.0, # Process memory relative to some limit if known, or just high absolute value
            "max_memory_rss_mb_process": 1024.0, # Example: 1GB RSS limit for the process
            "min_fps_average": 25.0,
            "max_load_time_seconds": 10.0, # For a specific feature
            # Regression thresholds (percentage change from Java to Bedrock)
            "regression_cpu_increase_percent": 30.0, # Bedrock CPU is X% higher
            "regression_memory_increase_percent": 40.0, # Bedrock Memory is X% higher
            "regression_fps_decrease_percent": -25.0, # Bedrock FPS is X% lower (negative indicates decrease)
        }

    def analyze(self, bedrock_metrics_set, comparison_results=None, scenario=None): # Added scenario
        print("\nAnalyzing Bedrock performance metrics...")
        analysis_summary = {
            "identified_issues": [],
            "optimization_suggestions": []
        }

        # --- Direct Metric Analysis for Bedrock ---
        # CPU Analysis
        cpu_metrics = bedrock_metrics_set.get('cpu', {})
        process_cpu_usage = cpu_metrics.get('process_cpu_usage_percent', 0.0)
        # Ensure process_cpu_usage is treated as float for comparison
        if not isinstance(process_cpu_usage, (int,float)):
            process_cpu_usage = 0.0

        if process_cpu_usage > self.thresholds['max_cpu_usage_percent']:
            issue = f"High CPU Usage: Bedrock process CPU at {process_cpu_usage:.2f}% exceeds threshold of {self.thresholds['max_cpu_usage_percent']}%."
            analysis_summary['identified_issues'].append(issue)
            analysis_summary['optimization_suggestions'].append("Investigate CPU-intensive scripts, entity behaviors, or complex block updates.")

        # Memory Analysis
        memory_metrics = bedrock_metrics_set.get('memory', {})
        process_rss_mb = memory_metrics.get('process_rss_mb', 0.0)
        if not isinstance(process_rss_mb, (int,float)):
            process_rss_mb = 0.0

        if process_rss_mb > self.thresholds['max_memory_rss_mb_process']:
            issue = f"High Memory Usage (RSS): Bedrock process RSS at {process_rss_mb:.2f}MB exceeds threshold of {self.thresholds['max_memory_rss_mb_process']}MB."
            analysis_summary['identified_issues'].append(issue)
            analysis_summary['optimization_suggestions'].append("Profile memory allocations. Check for memory leaks, large textures/models, or excessive entity/block data.")

        # Frame Rate Analysis (if available and not 'not_implemented')
        fps_metrics = bedrock_metrics_set.get('frame_rate', {})
        fps_average = fps_metrics.get('fps_average')
        if isinstance(fps_average, (int, float)) and fps_average < self.thresholds['min_fps_average']:
            issue = f"Low Frame Rate: Bedrock average FPS at {fps_average:.2f} is below threshold of {self.thresholds['min_fps_average']} FPS."
            analysis_summary['identified_issues'].append(issue)
            analysis_summary['optimization_suggestions'].append("Optimize rendering: simplify models/textures, reduce particle effects, optimize shaders if applicable. Check for performance spikes tied to specific game events.")

        # Load Time Analysis (if available and not 'not_implemented')
        load_time_metrics = bedrock_metrics_set.get('load_time', {})
        # Construct the key based on target_name from metrics collection if scenario is available
        # Defaulting to a generic key if not.
        target_name_for_load_key = "bedrock" # Assuming analysis is for bedrock
        if scenario and isinstance(scenario.get('parameters', {}).get('target_name_for_load_key'), str): # hypothetical scenario param
             target_name_for_load_key = scenario.get('parameters').get('target_name_for_load_key')

        # The actual key for load time in metrics from collect_all_metrics_for_target is feature_name + "_time_seconds"
        # e.g. "bedrock_load_time_seconds"
        bedrock_metrics_set.get('load_time',{}).get('feature_name_prefix_for_analyzer', target_name_for_load_key + "_load") # a bit meta
        # A more direct approach: assume keys like "bedrock_load_some_feature_time_seconds"
        # For this example, let's assume a general load time metric if one exists, or use a specific one if known.
        # This part is tricky as load_time keys are dynamic.
        # We'll iterate through load_time_metrics to find relevant ones.
        for key, value in load_time_metrics.items():
            if key.endswith("_time_seconds") and isinstance(value, (int, float)):
                if value > self.thresholds['max_load_time_seconds']:
                    issue = f"Long Load Time ({key}): Bedrock load time at {value:.2f}s exceeds threshold of {self.thresholds['max_load_time_seconds']}s."
                    analysis_summary['identified_issues'].append(issue)
                    analysis_summary['optimization_suggestions'].append(f"Optimize loading for '{key}': defer non-critical assets, simplify initial setup.")


        # --- Comparative Analysis (Regressions) using comparison_results ---
        if comparison_results:
            for category, metrics_comp in comparison_results.items(): # renamed metrics to avoid clash
                for metric_name, comparison_data in metrics_comp.items():
                    percentage_change = comparison_data.get('percentage_change')
                    if not isinstance(percentage_change, (int, float)): # Skip if not a number (e.g. "N/A", "inf")
                        continue

                    # Check for CPU regression
                    if category == 'cpu' and 'cpu_usage_percent' in metric_name: # More general check for CPU usage metrics
                        if percentage_change > self.thresholds['regression_cpu_increase_percent']:
                            issue = f"CPU Regression ({metric_name}): Bedrock CPU usage ({comparison_data.get('bedrock_value', 'N/A')}) is {percentage_change:.2f}% higher than Java ({comparison_data.get('java_value', 'N/A')})."
                            analysis_summary['identified_issues'].append(issue)
                            analysis_summary['optimization_suggestions'].append(f"Investigate why Bedrock CPU usage is significantly higher for {metric_name}. Review translated scripts or entity logic for inefficiencies.")

                    # Check for Memory regression (RSS)
                    if category == 'memory' and ('rss_mb' in metric_name or 'memory_percent' in metric_name): # General check for memory
                        if percentage_change > self.thresholds['regression_memory_increase_percent']:
                            issue = f"Memory Regression ({metric_name}): Bedrock Memory ({comparison_data.get('bedrock_value', 'N/A')}) is {percentage_change:.2f}% higher than Java ({comparison_data.get('java_value', 'N/A')})."
                            analysis_summary['identified_issues'].append(issue)
                            analysis_summary['optimization_suggestions'].append(f"Profile Bedrock memory usage for {metric_name}. The increase compared to Java is substantial.")

                    # Check for FPS regression
                    if category == 'frame_rate' and 'fps_average' in metric_name:
                        if percentage_change < self.thresholds['regression_fps_decrease_percent']: # Note: decrease is negative
                            issue = f"Frame Rate Regression ({metric_name}): Bedrock FPS ({comparison_data.get('bedrock_value', 'N/A')}) is {abs(percentage_change):.2f}% lower than Java ({comparison_data.get('java_value', 'N/A')})."
                            analysis_summary['identified_issues'].append(issue)
                            analysis_summary['optimization_suggestions'].append(f"Investigate rendering performance differences for {metric_name}. Compare visual fidelity vs. performance cost.")

        if not analysis_summary['identified_issues']:
            analysis_summary['identified_issues'].append("No major performance issues or regressions detected based on current thresholds.")
            analysis_summary['optimization_suggestions'].append("Performance appears within acceptable limits relative to thresholds and Java version (if compared).")

        # print(f"Analysis summary: {json.dumps(analysis_summary, indent=2)}")
        return analysis_summary

class PerformanceComparator:
    def __init__(self):
        print("PerformanceComparator initialized.")

    def compare(self, java_metrics_set, bedrock_metrics_set):
        # java_metrics_set and bedrock_metrics_set are expected to be structured like:
        # {
        #     "cpu": {"cpu_usage_percent": X, "cpu_time_user_seconds": Y, ...},
        #     "memory": {"process_rss_mb": A, "process_memory_percent": B, ...},
        #     "network": {...},
        #     "frame_rate": {...}, // Placeholder metrics
        #     "load_time": {...},  // Placeholder metrics
        #     "response_time": {...} // Placeholder metrics
        # }
        print("\nComparing Java and Bedrock performance metrics...")
        comparison_results = {}

        # Define categories to iterate through, matching keys from collect_all_metrics_for_target
        metric_categories = ['cpu', 'memory', 'network', 'frame_rate', 'load_time', 'response_time']

        for category in metric_categories:
            comparison_results[category] = {}
            java_category_metrics = java_metrics_set.get(category, {})
            bedrock_category_metrics = bedrock_metrics_set.get(category, {})

            # Get all unique metric names from both Java and Bedrock for this category
            all_metric_keys = set(java_category_metrics.keys()) | set(bedrock_category_metrics.keys())

            for metric_key in all_metric_keys:
                java_value = java_category_metrics.get(metric_key)
                bedrock_value = bedrock_category_metrics.get(metric_key)

                # Initialize comparison entry for this metric
                comparison_results[category][metric_key] = {
                    "java_value": java_value,
                    "bedrock_value": bedrock_value,
                    "difference": "N/A",
                    "percentage_change": "N/A"
                }

                # Attempt numerical comparison if both values are numbers
                if isinstance(java_value, (int, float)) and isinstance(bedrock_value, (int, float)):
                    difference = bedrock_value - java_value
                    comparison_results[category][metric_key]["difference"] = round(difference, 4)
                    if java_value != 0:
                        percentage_change = (difference / java_value) * 100
                        comparison_results[category][metric_key]["percentage_change"] = round(percentage_change, 2)
                    elif bedrock_value != 0: # Java value is 0, Bedrock is not
                        comparison_results[category][metric_key]["percentage_change"] = "inf" # Infinite change
                    else: # Both are 0
                        comparison_results[category][metric_key]["percentage_change"] = 0.0
                elif java_value is None and bedrock_value is not None:
                    comparison_results[category][metric_key]["difference"] = "N/A (Java missing)"
                elif bedrock_value is None and java_value is not None:
                    comparison_results[category][metric_key]["difference"] = "N/A (Bedrock missing)"

                # Handle "not_implemented" strings or other non-numeric data gracefully
                if isinstance(java_value, str) and "not_implemented" in java_value:
                    comparison_results[category][metric_key]["java_value"] = "Not Implemented"
                if isinstance(bedrock_value, str) and "not_implemented" in bedrock_value:
                    comparison_results[category][metric_key]["bedrock_value"] = "Not Implemented"

        # print(f"Comparison results: {json.dumps(comparison_results, indent=2)}") # Requires import json
        return comparison_results

class BenchmarkReporter:
    def __init__(self):
        pass

    def generate_report(self, analysis, comparison_results, scenario):
        scenario_name = scenario.get('scenario_name', scenario.get('scenario_id', 'N/A'))
        report = f"---------- Performance Benchmark Report for Scenario: {scenario_name} ----------\n\n"

        report += "--- Scenario Details ---\n"
        report += f"  ID: {scenario.get('scenario_id', 'N/A')}\n"
        report += f"  Description: {scenario.get('description', 'N/A')}\n"
        report += f"  Type: {scenario.get('type', 'N/A')}\n"
        report += f"  Duration (s): {scenario.get('duration_seconds', 'N/A')}\n"
        report += f"  Parameters: {json.dumps(scenario.get('parameters', {}), indent=2)}\n\n"

        report += "--- Performance Analysis Summary (Bedrock Target) ---\n"
        if analysis and analysis.get('identified_issues'):
            report += "  Identified Issues:\n"
            for issue in analysis['identified_issues']:
                report += f"    - {issue}\n"

            report += "\n  Optimization Suggestions:\n"
            for suggestion in analysis.get('optimization_suggestions', []):
                report += f"    - {suggestion}\n"
        else:
            report += "  No specific analysis points or issues generated by the analyzer.\n"
        report += "\n"

        report += "--- Detailed Java vs. Bedrock Comparison ---\n"
        if comparison_results:
            for category, metrics in comparison_results.items():
                report += f"  Category: {category.upper()}\n"
                if not metrics:
                    report += "    No metrics compared in this category.\n"
                    continue
                for metric_key, values in metrics.items():
                    report += f"    Metric: {metric_key}\n"
                    report += f"      Java Value:         {values.get('java_value', 'N/A')}\n"
                    report += f"      Bedrock Value:      {values.get('bedrock_value', 'N/A')}\n"
                    report += f"      Difference:         {values.get('difference', 'N/A')}\n"
                    report += f"      Percentage Change:  {values.get('percentage_change', 'N/A')}%\n"
        else:
            report += "  No comparison data generated.\n"

        report += "\n-------------------- End of Report --------------------\n"
        # print(f"Generating report: {report}") # Printing is handled by the caller
        return report

class PerformanceBenchmarkingSystem:
    def __init__(self):
        self.benchmark_runner = BenchmarkExecutor()
        # self.metrics_collector = PerformanceMetricsCollector() # This is the old internal one
        self.metrics_collector = ExternalPerformanceMetricsCollector() # Use the advanced one
        self.load_generator = LoadTestGenerator()
        self.analyzer = PerformanceAnalyzer()
        self.comparator = PerformanceComparator()
        self.reporter = BenchmarkReporter()
        print("PerformanceBenchmarkingSystem initialized with ExternalPerformanceMetricsCollector.")

    def run_full_benchmark(self, scenario, java_process_keyword="java", bedrock_process_keyword="bedrock_server"):
        scenario_name = scenario.get('scenario_name', scenario.get('scenario', 'Unknown Scenario'))
        print(f"\nStarting full benchmark for scenario: {scenario_name}")

        # Simulate load generation
        self.load_generator.generate_load(scenario)

        # Collect metrics using the external collector
        print("\nCollecting Java metrics...")
        java_metrics = self.metrics_collector.collect_all_metrics_for_target(
            target_name="java", process_keyword=java_process_keyword
        )
        # print(f"Java metrics collected: {json.dumps(java_metrics, indent=2)}")


        print("\nCollecting Bedrock metrics...")
        bedrock_metrics = self.metrics_collector.collect_all_metrics_for_target(
            target_name="bedrock", process_keyword=bedrock_process_keyword
        )
        # print(f"Bedrock metrics collected: {json.dumps(bedrock_metrics, indent=2)}")

        # Compare metrics
        # The 'compare' method now expects the direct metric sets from collect_all_metrics_for_target
        comparison = self.comparator.compare(java_metrics, bedrock_metrics)

        # Analyze Bedrock metrics (or a combined set as per requirements)
        # The analyzer might need to be adapted based on what metrics it should focus on.
        # For now, let's assume it analyzes Bedrock's 'cpu' and 'memory' sections.
        print("\nAnalyzing Bedrock performance...")
        # Pass bedrock_metrics, comparison results, and scenario to the analyzer
        analysis = self.analyzer.analyze(bedrock_metrics, comparison_results=comparison, scenario=scenario)


        # Generate report
        # The reporter might need scenario details for context.
        print("\nGenerating performance report...")
        report = self.reporter.generate_report(analysis, comparison, scenario) # Added scenario to reporter
        print(report)
        return report

if __name__ == '__main__':
    # Example Usage (for testing purposes)
    # This will use the actual metrics collector, which might look for processes.
    # For local testing, you might want to use common process names like 'python'
    # or a known running application for `java_process_keyword` and `bedrock_process_keyword`
    # if you don't have actual Java/Bedrock servers running.

    # Using a direct dictionary representation of a scenario for simplicity in this example.
    # In a real setup, you'd load this from a JSON file.
    example_scenario_high_entity = {
      "scenario_id": "stress_entity_001_main_test",
      "scenario_name": "High Entity Count Stress Test (Main Example)",
      "description": "Test performance with a high number of custom entities.",
      "type": "stress_test",
      "target_platform": "any",
      "duration_seconds": 10, # Short duration for quick test
      "metrics_to_collect": ["cpu_usage_percent", "memory_used_mb", "frame_rate_average"],
      "parameters": {
        "load_level": "high",
        "entity_count": 100, # Reduced for quick test
        "entity_type": "custom_mob_gamma",
        "enable_ai": True,
        "start_interactions": True
      },
      "thresholds": { # These would be used by a more advanced analyzer or validation step
        "min_fps_average": 20,
        "max_cpu_percent_process": 90,
      }
    }

    print("--- Running PerformanceBenchmarkingSystem with example scenario ---")
    pbs = PerformanceBenchmarkingSystem()

    # For testing, let's assume 'python' is our "Java" process and also for "Bedrock"
    # to ensure psutil finds *something*. In a real test, these would be actual server process keywords.
    # If no such processes are running, the specific metrics will be empty or show errors.
    # The system-wide metrics will still be collected.
    # You can change "python" to a process name that IS running on your system for better test data.
    # For example, if you have a text editor like 'code' (VS Code) running, you could use that.
    # Or simply use None to only get system-wide metrics for those sections.
    java_keyword = "python" # Placeholder, use a running process name if possible
    bedrock_keyword = None # Placeholder, use a running process name or None

    # Check if any python process is running to give more meaningful test output for process-specific metrics
    try:
        import psutil
        found_python = False
        for proc in psutil.process_iter(['name']):
            if 'python' in proc.info['name'].lower():
                found_python = True
                break
        if not found_python:
            print("NOTE: No 'python' process detected. Process-specific metrics for 'java_keyword' might be empty or error out.")
            # java_keyword = None # Optionally set to None if you prefer system-wide for the test
    except ImportError:
        print("psutil not installed, process-specific metrics will likely fail or be empty.")
    except psutil.Error: # More specific psutil errors could be caught if needed
        print("Error accessing process list with psutil.")


    final_report = pbs.run_full_benchmark(
        example_scenario_high_entity,
        java_process_keyword=java_keyword,
        bedrock_process_keyword=bedrock_keyword
    )

    print("\n--- Main test finished. Final Report (also printed above by the system): ---")
    # The report is already printed by run_full_benchmark, but printing it again here
    # just to show it can be captured and used.
    # print(final_report)
    print("--- End of __main__ test run ---")
