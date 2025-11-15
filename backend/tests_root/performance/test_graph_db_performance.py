"""
Direct Graph Database Performance Tests

Tests the Neo4j graph database performance without API layer
to identify bottlenecks and optimization opportunities.
"""

import pytest
import time
import psutil
import tracemalloc
import os
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
import asyncio

# Import graph database manager
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent / "backend" / "src"))
from db.graph_db import GraphDatabaseManager


class TestGraphDatabasePerformance:
    """Performance tests for Neo4j graph database"""

    @pytest.fixture(autouse=True)
    def setup_memory_tracking(self):
        """Setup memory tracking for performance tests"""
        tracemalloc.start()
        yield
        tracemalloc.stop()

    def get_memory_usage(self):
        """Get current memory usage in MB"""
        process = psutil.Process()
        memory_info = process.memory_info()
        return memory_info.rss / 1024 / 1024  # MB

    @pytest.fixture
    def graph_manager(self):
        """Create a graph database manager for testing"""
        manager = GraphDatabaseManager()
        # Use test credentials
        manager.uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        manager.user = os.getenv("NEO4J_USER", "neo4j")
        manager.password = os.getenv("NEO4J_PASSWORD", "password")
        yield manager
        manager.close()

    def test_connection_performance(self, graph_manager):
        """Test connection establishment performance"""
        connection_times = []
        
        # Test multiple connection attempts
        for i in range(10):
            start_time = time.time()
            connected = graph_manager.connect()
            connection_time = time.time() - start_time
            connection_times.append(connection_time)
            
            if connected:
                graph_manager.close()
        
        avg_connection_time = sum(connection_times) / len(connection_times)
        print(f"Average connection time: {avg_connection_time:.3f}s")
        
        # Connection should be reasonably fast
        assert avg_connection_time < 1.0  # Should connect within 1 second

    def test_node_creation_performance(self, graph_manager):
        """Test node creation performance"""
        if not graph_manager.connect():
            pytest.skip("Neo4j not available")
        
        try:
            # Test individual node creation
            individual_times = []
            for i in range(100):
                start_time = time.time()
                node_id = graph_manager.create_node(
                    node_type="java_class",
                    name=f"TestClass{i}",
                    properties={"package": f"com.example.test{i % 10}"}
                )
                creation_time = time.time() - start_time
                individual_times.append(creation_time)
                assert node_id is not None
            
            avg_individual_time = sum(individual_times) / len(individual_times)
            print(f"Average individual node creation time: {avg_individual_time:.3f}s")
            
            # Individual operations should be fast
            assert avg_individual_time < 0.1  # Should be under 100ms
            
            # Test batch-like performance (simulated)
            batch_start = time.time()
            batch_node_ids = []
            for i in range(500):
                node_id = graph_manager.create_node(
                    node_type="java_method",
                    name=f"TestMethod{i}",
                    properties={"class": f"TestClass{i % 50}", "visibility": "public"}
                )
                batch_node_ids.append(node_id)
            
            batch_time = time.time() - batch_start
            batch_rate = 500 / batch_time
            print(f"Created 500 nodes in {batch_time:.2f}s ({batch_rate:.0f} nodes/s)")
            
            # Should maintain reasonable throughput
            assert batch_rate > 50  # At least 50 nodes per second
            
        finally:
            # Clean up test data
            self._cleanup_test_data(graph_manager)

    def test_relationship_creation_performance(self, graph_manager):
        """Test relationship creation performance"""
        if not graph_manager.connect():
            pytest.skip("Neo4j not available")
        
        try:
            # Create nodes for relationships
            node_ids = []
            for i in range(100):
                node_id = graph_manager.create_node(
                    node_type="java_class",
                    name=f"RelTestClass{i}",
                    properties={"package": f"com.example.rel"}
                )
                node_ids.append(node_id)
            
            # Test relationship creation
            relationship_times = []
            for i in range(200):
                source_idx = i % len(node_ids)
                target_idx = (source_idx + 1) % len(node_ids)
                
                start_time = time.time()
                rel_id = graph_manager.create_relationship(
                    source_node_id=node_ids[source_idx],
                    target_node_id=node_ids[target_idx],
                    relationship_type="depends_on",
                    properties={"strength": 0.5 + (i % 5) * 0.1},
                    confidence_score=0.8
                )
                relationship_time = time.time() - start_time
                relationship_times.append(relationship_time)
                assert rel_id is not None
            
            avg_relationship_time = sum(relationship_times) / len(relationship_times)
            print(f"Average relationship creation time: {avg_relationship_time:.3f}s")
            
            # Relationship creation should be fast
            assert avg_relationship_time < 0.15  # Should be under 150ms
            
        finally:
            self._cleanup_test_data(graph_manager)

    def test_search_performance(self, graph_manager):
        """Test search performance with various query complexities"""
        if not graph_manager.connect():
            pytest.skip("Neo4j not available")
        
        try:
            # Create test data for searching
            node_types = ["java_class", "java_method", "minecraft_block", "minecraft_item"]
            created_nodes = []
            
            for i in range(1000):
                node_type = node_types[i % len(node_types)]
                node_id = graph_manager.create_node(
                    node_type=node_type,
                    name=f"SearchTestNode{i}",
                    properties={
                        "category": f"category{i % 20}",
                        "value": i % 100,
                        "package": f"com.example.search{i % 50}"
                    }
                )
                created_nodes.append(node_id)
            
            # Test search performance
            search_queries = [
                ("SearchTestNode500", 1),  # Exact match
                ("category15", 50),        # Category search
                ("SearchTestNode", 100),   # Partial match
            ]
            
            for query, expected_min_results in search_queries:
                memory_before = self.get_memory_usage()
                search_start = time.time()
                
                results = graph_manager.search_nodes(query, limit=100)
                
                search_time = time.time() - search_start
                memory_after = self.get_memory_usage()
                memory_increase = memory_after - memory_before
                
                print(f"Search '{query}': {len(results)} results in {search_time:.3f}s, memory: +{memory_increase:.1f}MB")
                
                # Performance assertions
                assert search_time < 0.5  # Search should complete within 500ms
                assert memory_increase < 20  # Should use less than 20MB additional memory
                assert len(results) >= min(expected_min_results, 20)  # May be limited
                
        finally:
            self._cleanup_test_data(graph_manager)

    def test_traversal_performance(self, graph_manager):
        """Test graph traversal performance"""
        if not graph_manager.connect():
            pytest.skip("Neo4j not available")
        
        try:
            # Create a tree structure for traversal testing
            root_id = graph_manager.create_node(
                node_type="java_class",
                name="TraversalRoot"
            )
            
            # Create tree with 5 levels
            level_nodes = [[root_id]]
            for level in range(1, 6):
                level_nodes.append([])
                parent_nodes = level_nodes[level - 1]
                
                for parent in parent_nodes:
                    for i in range(3):  # 3 children per parent
                        child_id = graph_manager.create_node(
                            node_type="java_class",
                            properties={
                                "name": f"Level{level}Node{len(level_nodes[level])}",
                                "level": level
                            }
                        )
                        level_nodes[level].append(child_id)
                        
                        # Create relationship
                        graph_manager.create_relationship(
                            source_node_id=parent,
                            target_node_id=child_id,
                            relationship_type="extends"
                        )
            
            # Test traversal performance at different depths
            for depth in range(1, 6):
                memory_before = self.get_memory_usage()
                traversal_start = time.time()
                
                # Get all relationships (simulating traversal)
                relationships = graph_manager.get_node_relationships(root_id)
                
                traversal_time = time.time() - traversal_start
                memory_after = self.get_memory_usage()
                
                total_relationships = len(relationships["incoming"]) + len(relationships["outgoing"])
                
                print(f"Traversal at depth {depth}: {total_relationships} relationships in {traversal_time:.3f}s, memory: +{memory_after - memory_before:.1f}MB")
                
                # Performance should remain reasonable
                assert traversal_time < 1.0  # Traversal should complete within 1 second
                assert (memory_after - memory_before) < 50  # Should use less than 50MB
                
        finally:
            self._cleanup_test_data(graph_manager)

    def test_concurrent_operations(self, graph_manager):
        """Test performance under concurrent operations"""
        if not graph_manager.connect():
            pytest.skip("Neo4j not available")
        
        try:
            # Test concurrent node creation
            concurrent_start = time.time()
            
            def create_node_batch(node_index):
                """Create a single node"""
                node_id = graph_manager.create_node(
                    node_type="java_class",
                    name=f"ConcurrentNode{node_index}",
                    properties={"thread": "concurrent_test"}
                )
                return node_id
            
            # Use ThreadPoolExecutor for concurrent operations
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(create_node_batch, i) for i in range(50)]
                node_ids = [future.result() for future in futures]
            
            concurrent_time = time.time() - concurrent_start
            successful_nodes = sum(1 for node_id in node_ids if node_id is not None)
            
            print(f"Concurrent node creation: {successful_nodes}/50 in {concurrent_time:.2f}s")
            
            # Most operations should succeed
            assert successful_nodes >= 45  # At least 90% success rate
            assert concurrent_time < 5.0  # Should complete within 5 seconds
            
            # Test concurrent searches
            def search_nodes(search_index):
                """Search nodes"""
                return graph_manager.search_nodes(f"ConcurrentNode{search_index}")
            
            search_start = time.time()
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(search_nodes, i) for i in range(30)]
                search_results = [future.result() for future in futures]
            
            search_time = time.time() - search_start
            successful_searches = sum(1 for result in search_results if result is not None)
            
            print(f"Concurrent searches: {successful_searches}/30 in {search_time:.2f}s")
            
            # Searches should be reliable
            assert successful_searches >= 27  # At least 90% success rate
            assert search_time < 2.0  # Should complete within 2 seconds
            
        finally:
            self._cleanup_test_data(graph_manager)

    def test_memory_efficiency(self, graph_manager):
        """Test memory usage efficiency"""
        if not graph_manager.connect():
            pytest.skip("Neo4j not available")
        
        try:
            memory_measurements = []
            
            # Create nodes and measure memory
            for i in range(200):
                memory_before = self.get_memory_usage()
                
                # Create node
                node_id = graph_manager.create_node(
                    node_type="java_class",
                    name=f"MemoryTestNode{i}",
                    properties={
                        "field1": f"value{i % 10}",
                        "field2": i,
                        "field3": f"desc{i % 5}",
                        "large_data": "x" * 100  # Some larger data
                    }
                )
                
                # Create relationships
                if i > 0:
                    graph_manager.create_relationship(
                        source_node_id=f"previous_node_{i-1}",
                        target_node_id=node_id,
                        relationship_type="depends_on"
                    )
                
                memory_after = self.get_memory_usage()
                memory_increase = memory_after - memory_before
                memory_measurements.append(memory_increase)
                
                # Check for memory leaks every 50 operations
                if i % 50 == 0:
                    current_memory = self.get_memory_usage()
                    print(f"Created {i+1} nodes, current memory: {current_memory:.1f}MB")
            
            # Analyze memory usage
            avg_memory_per_operation = sum(memory_measurements) / len(memory_measurements)
            max_memory_increase = max(memory_measurements)
            
            print(f"Average memory per operation: {avg_memory_per_operation:.2f}MB")
            print(f"Maximum memory increase: {max_memory_increase:.2f}MB")
            
            # Memory efficiency assertions
            assert avg_memory_per_operation < 2.0  # Should average less than 2MB per operation
            assert max_memory_increase < 20.0  # No single operation should use more than 20MB
            
        finally:
            self._cleanup_test_data(graph_manager)

    def _cleanup_test_data(self, graph_manager):
        """Helper method to clean up test data"""
        try:
            # Delete all test nodes
            session = graph_manager.get_session()
            if session:
                session.run("MATCH (n) WHERE n.name STARTS WITH 'Test' OR n.name STARTS WITH 'SearchTest' OR n.name STARTS WITH 'RelTest' OR n.name STARTS WITH 'Traversal' OR n.name STARTS WITH 'Concurrent' OR n.name STARTS WITH 'MemoryTest' DETACH DELETE n")
                session.close()
        except Exception as e:
            print(f"Warning: Failed to clean up test data: {e}")
