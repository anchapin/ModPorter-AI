"""
Performance tests for Knowledge Graph System
Tests scalability, memory usage, and response times under various loads
"""
import pytest
import asyncio
import time
import psutil
import tracemalloc
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
from httpx import AsyncClient


class TestKnowledgeGraphPerformance:
    """Performance tests for knowledge graph system"""

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

    @pytest.mark.asyncio
    async def test_large_graph_loading_performance(self, async_client: AsyncClient):
        """Test performance with large graph data sets"""
        
        # Create large graph data
        node_count = 5000
        edge_count = 10000
        
        # Batch create nodes
        node_creation_start = time.time()
        node_ids = []
        
        for batch in range(0, node_count, 100):
            batch_nodes = []
            for i in range(min(100, node_count - batch)):
                node_id = str(uuid4())
                node_ids.append(node_id)
                batch_nodes.append({
                    "id": node_id,
                    "node_type": "java_class",
                    "properties": {
                        "name": f"TestClass{batch + i}",
                        "package": f"com.example.test{batch + i % 10}"
                    }
                })
            
            response = await async_client.post("/api/knowledge-graph/nodes/batch", json={"nodes": batch_nodes})
            assert response.status_code == 201
        
        node_creation_time = time.time() - node_creation_start
        print(f"Created {node_count} nodes in {node_creation_time:.2f}s ({node_count/node_creation_time:.0f} nodes/s)")
        
        # Batch create edges
        edge_creation_start = time.time()
        
        for batch in range(0, edge_count, 200):
            batch_edges = []
            for i in range(min(200, edge_count - batch)):
                source_idx = (batch + i) % node_count
                target_idx = (source_idx + 1) % node_count
                
                batch_edges.append({
                    "source_id": node_ids[source_idx],
                    "target_id": node_ids[target_idx],
                    "relationship_type": "depends_on",
                    "properties": {"strength": 0.5 + (i % 5) * 0.1}
                })
            
            response = await async_client.post("/api/knowledge-graph/edges/batch", json={"edges": batch_edges})
            assert response.status_code == 201
        
        edge_creation_time = time.time() - edge_creation_start
        print(f"Created {edge_count} edges in {edge_creation_time:.2f}s ({edge_count/edge_creation_time:.0f} edges/s)")
        
        # Test graph loading performance
        memory_before = self.get_memory_usage()
        load_start = time.time()
        
        response = await async_client.get("/api/knowledge-graph/visualization/", params={
            "limit": 10000,
            "layout": "force_directed"
        })
        
        load_time = time.time() - load_start
        memory_after = self.get_memory_usage()
        memory_increase = memory_after - memory_before
        
        assert response.status_code == 200
        assert load_time < 5.0  # Should load within 5 seconds
        assert memory_increase < 500  # Should use less than 500MB additional memory
        
        data = response.json()
        assert len(data["nodes"]) >= min(1000, node_count)  # May be limited by pagination
        assert len(data["edges"]) >= min(2000, edge_count)
        
        print(f"Loaded graph in {load_time:.2f}s, memory increase: {memory_increase:.1f}MB")

    @pytest.mark.asyncio
    async def test_concurrent_graph_operations(self, async_client: AsyncClient):
        """Test concurrent graph operations performance"""
        
        # Create initial nodes for concurrent operations
        initial_nodes = []
        for i in range(100):
            response = await async_client.post("/api/knowledge-graph/nodes/", json={
                "node_type": "java_class",
                "properties": {"name": f"InitialNode{i}"}
            })
            assert response.status_code == 201
            initial_nodes.append(response.json()["id"])
        
        # Test concurrent node creation
        concurrent_node_count = 50
        concurrent_start = time.time()
        
        async def create_concurrent_node(node_index):
            response = await async_client.post("/api/knowledge-graph/nodes/", json={
                "node_type": "java_method",
                "properties": {
                    "name": f"ConcurrentMethod{node_index}",
                    "class": f"TestClass{node_index}"
                }
            })
            return response
        
        # Run concurrent operations
        concurrent_tasks = [create_concurrent_node(i) for i in range(concurrent_node_count)]
        concurrent_results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        
        concurrent_time = time.time() - concurrent_start
        successful_operations = sum(1 for r in concurrent_results if hasattr(r, 'status_code') and r.status_code == 201)
        
        print(f"Concurrent node creation: {successful_operations}/{concurrent_node_count} in {concurrent_time:.2f}s")
        assert successful_operations >= concurrent_node_count * 0.9  # At least 90% success
        assert concurrent_time < 3.0  # Should complete within 3 seconds
        
        # Test concurrent graph queries
        concurrent_query_count = 30
        
        async def query_concurrent_graph(query_index):
            response = await async_client.get("/api/knowledge-graph/nodes/", params={
                "node_type": "java_class",
                "limit": 10,
                "offset": query_index * 5
            })
            return response
        
        query_start = time.time()
        query_tasks = [query_concurrent_graph(i) for i in range(concurrent_query_count)]
        query_results = await asyncio.gather(*query_tasks, return_exceptions=True)
        
        query_time = time.time() - query_start
        successful_queries = sum(1 for r in query_results if hasattr(r, 'status_code') and r.status_code == 200)
        
        print(f"Concurrent queries: {successful_queries}/{concurrent_query_count} in {query_time:.2f}s")
        assert successful_queries >= concurrent_query_count * 0.9
        assert query_time < 2.0  # Should complete within 2 seconds

    @pytest.mark.asyncio
    async def test_graph_search_performance(self, async_client: AsyncClient):
        """Test graph search performance with various query complexities"""
        
        # Create diverse graph data for searching
        node_types = ["java_class", "java_method", "minecraft_block", "minecraft_item"]
        relationships = ["extends", "implements", "depends_on", "creates", "modifies"]
        
        # Create nodes
        created_nodes = []
        for i in range(1000):
            node_type = node_types[i % len(node_types)]
            response = await async_client.post("/api/knowledge-graph/nodes/", json={
                "node_type": node_type,
                "properties": {
                    "name": f"SearchTestNode{i}",
                    "category": f"category{i % 20}",
                    "value": i % 100
                }
            })
            created_nodes.append(response.json()["id"])
        
        # Create edges
        for i in range(2000):
            source_idx = i % len(created_nodes)
            target_idx = (source_idx + 1) % len(created_nodes)
            relationship_type = relationships[i % len(relationships)]
            
            await async_client.post("/api/knowledge-graph/edges/", json={
                "source_id": created_nodes[source_idx],
                "target_id": created_nodes[target_idx],
                "relationship_type": relationship_type,
                "properties": {"weight": i % 10}
            })
        
        # Test search performance
        search_queries = [
            # Simple name search
            {"query": "SearchTestNode500", "expected_results": 1},
            # Category search
            {"query": "category15", "expected_results": 50},
            # Node type filter
            {"query": "SearchTestNode", "node_type": "java_class", "expected_results": 250},
            # Complex query
            {"query": "SearchTestNode", "node_type": "java_method", "limit": 20, "expected_results": 20},
            # No results
            {"query": "NonExistentNode", "expected_results": 0}
        ]
        
        for query_data in search_queries:
            search_start = time.time()
            memory_before = self.get_memory_usage()
            
            params = {"query": query_data["query"]}
            if "node_type" in query_data:
                params["node_type"] = query_data["node_type"]
            if "limit" in query_data:
                params["limit"] = query_data["limit"]
            
            response = await async_client.get("/api/knowledge-graph/search/", params=params)
            search_time = time.time() - search_start
            memory_after = self.get_memory_usage()
            
            assert response.status_code == 200
            data = response.json()
            
            # Validate results
            if query_data["expected_results"] > 0:
                assert len(data["results"]) >= min(query_data["expected_results"], 20)  # May be limited
            
            # Performance assertions
            assert search_time < 1.0  # Search should complete within 1 second
            assert (memory_after - memory_before) < 50  # Should use less than 50MB additional memory
            
            print(f"Search '{query_data['query']}': {len(data['results'])} results in {search_time:.3f}s")

    @pytest.mark.asyncio
    async def test_graph_traversal_performance(self, async_client: AsyncClient):
        """Test graph traversal performance with various depths"""
        
        # Create connected graph structure for traversal testing
        root_node_response = await async_client.post("/api/knowledge-graph/nodes/", json={
            "node_type": "java_class",
            "properties": {"name": "RootClass"}
        })
        root_node_id = root_node_response.json()["id"]
        
        # Create tree structure
        created_nodes = [root_node_id]
        levels = 5
        nodes_per_level = [1, 10, 50, 200, 500]
        
        for level in range(1, levels):
            parent_start = sum(nodes_per_level[:level])
            parent_end = sum(nodes_per_level[:level + 1])
            
            for i in range(nodes_per_level[level]):
                node_response = await async_client.post("/api/knowledge-graph/nodes/", json={
                    "node_type": "java_class",
                    "properties": {
                        "name": f"Level{level}Node{i}",
                        "level": level
                    }
                })
                node_id = node_response.json()["id"]
                created_nodes.append(node_id)
                
                # Connect to parent
                parent_idx = parent_start + (i // 10)
                if parent_idx < len(created_nodes):
                    await async_client.post("/api/knowledge-graph/edges/", json={
                        "source_id": created_nodes[parent_idx],
                        "target_id": node_id,
                        "relationship_type": "extends"
                    })
        
        # Test traversal performance at different depths
        traversal_depths = [1, 2, 3, 4, 5]
        
        for depth in traversal_depths:
            traversal_start = time.time()
            memory_before = self.get_memory_usage()
            
            response = await async_client.get(f"/api/knowledge-graph/nodes/{root_node_id}/neighbors", params={
                "depth": depth,
                "max_nodes": 1000
            })
            
            traversal_time = time.time() - traversal_start
            memory_after = self.get_memory_usage()
            
            assert response.status_code == 200
            data = response.json()
            
            expected_nodes = min(sum(nodes_per_level[:depth + 1]), 1000)
            assert len(data["neighbors"]) >= expected_nodes * 0.8  # Allow some variance
            
            # Performance assertions
            assert traversal_time < 2.0  # Traversal should complete within 2 seconds
            assert (memory_after - memory_before) < 100  # Should use less than 100MB
            
            print(f"Traversal depth {depth}: {len(data['neighbors'])} nodes in {traversal_time:.3f}s")

    @pytest.mark.asyncio
    async def test_graph_update_performance(self, async_client: AsyncClient):
        """Test performance of graph updates and modifications"""
        
        # Create initial graph
        initial_node_count = 500
        node_ids = []
        
        for i in range(initial_node_count):
            response = await async_client.post("/api/knowledge-graph/nodes/", json={
                "node_type": "java_class",
                "properties": {"name": f"UpdateTestNode{i}"}
            })
            node_ids.append(response.json()["id"])
        
        # Test batch updates
        batch_updates = []
        for i in range(100):
            node_idx = i % len(node_ids)
            batch_updates.append({
                "id": node_ids[node_idx],
                "properties": {
                    "name": f"UpdatedNode{i}",
                    "version": 2,
                    "last_modified": time.time()
                },
                "metadata": {"update_reason": "performance_test"}
            })
        
        update_start = time.time()
        response = await async_client.post("/api/knowledge-graph/nodes/batch-update", json={
            "updates": batch_updates
        })
        update_time = time.time() - update_start
        
        assert response.status_code == 200
        assert update_time < 2.0  # Batch update should complete within 2 seconds
        
        # Test individual updates
        individual_update_times = []
        for i in range(50):
            update_start = time.time()
            
            response = await async_client.put(f"/api/knowledge-graph/nodes/{node_ids[i]}", json={
                "properties": {
                    "name": f"IndividualUpdate{i}",
                    "version": 3
                }
            })
            
            update_time = time.time() - update_start
            individual_update_times.append(update_time)
            
            assert response.status_code == 200
            assert update_time < 0.5  # Individual update should be fast
        
        avg_individual_update = sum(individual_update_times) / len(individual_update_times)
        print(f"Average individual update time: {avg_individual_update:.3f}s")
        assert avg_individual_update < 0.1  # Average should be under 100ms

    @pytest.mark.asyncio
    async def test_memory_usage_under_load(self, async_client: AsyncClient):
        """Test memory usage under sustained load"""
        
        memory_measurements = []
        operation_count = 0
        max_operations = 1000
        
        while operation_count < max_operations:
            # Perform mixed operations
            memory_before = self.get_memory_usage()
            
            # Create node
            node_response = await async_client.post("/api/knowledge-graph/nodes/", json={
                "node_type": "java_class",
                "properties": {"name": f"MemoryTestNode{operation_count}"}
            })
            
            # Create edge (connect to previous node if exists)
            if operation_count > 0:
                await async_client.post("/api/knowledge-graph/edges/", json={
                    "source_id": node_ids[-1] if 'node_ids' in locals() else node_response.json()["id"],
                    "target_id": node_response.json()["id"],
                    "relationship_type": "depends_on"
                })
            
            # Perform search
            await async_client.get("/api/knowledge-graph/search/", params={
                "query": f"MemoryTestNode{operation_count}",
                "limit": 10
            })
            
            memory_after = self.get_memory_usage()
            memory_increase = memory_after - memory_before
            
            memory_measurements.append(memory_increase)
            node_ids.append(node_response.json()["id"])
            operation_count += 1
            
            # Check for memory leaks every 100 operations
            if operation_count % 100 == 0:
                current_memory = self.get_memory_usage()
                print(f"Operations: {operation_count}, Current Memory: {current_memory:.1f}MB")
                
                # Memory should not grow indefinitely
                if len(memory_measurements) > 100:
                    recent_avg = sum(memory_measurements[-100:]) / 100
                    if current_memory > 1000 and recent_avg > 50:  # 1GB total, 50MB per operation
                        pytest.fail("Potential memory leak detected")
        
        # Analyze memory usage pattern
        avg_memory_per_operation = sum(memory_measurements) / len(memory_measurements)
        max_memory_increase = max(memory_measurements)
        
        print(f"Average memory per operation: {avg_memory_per_operation:.2f}MB")
        print(f"Maximum memory increase: {max_memory_increase:.2f}MB")
        
        # Memory efficiency assertions
        assert avg_memory_per_operation < 5.0  # Should average less than 5MB per operation
        assert max_memory_increase < 50.0  # No single operation should use more than 50MB

    @pytest.mark.asyncio
    async def test_graph_visualization_performance(self, async_client: AsyncClient):
        """Test performance of graph visualization rendering"""
        
        # Create graph data suitable for visualization
        viz_node_count = 2000
        viz_edge_count = 4000
        node_ids = []
        
        # Create nodes with visualization metadata
        for i in range(viz_node_count):
            response = await async_client.post("/api/knowledge-graph/nodes/", json={
                "node_type": ["java_class", "minecraft_block", "minecraft_item"][i % 3],
                "properties": {
                    "name": f"VizNode{i}",
                    "size": 5 + (i % 10),
                    "color": ["#ff0000", "#00ff00", "#0000ff"][i % 3]
                },
                "metadata": {
                    "x": (i % 50) * 20,
                    "y": (i // 50) * 20
                }
            })
            node_ids.append(response.json()["id"])
        
        # Create edges
        for i in range(viz_edge_count):
            source_idx = i % viz_node_count
            target_idx = (source_idx + 1) % viz_node_count
            
            await async_client.post("/api/knowledge-graph/edges/", json={
                "source_id": node_ids[source_idx],
                "target_id": node_ids[target_idx],
                "relationship_type": "depends_on",
                "properties": {
                    "width": 1 + (i % 3),
                    "color": "#999999"
                }
            })
        
        # Test visualization data generation
        viz_configs = [
            {"layout": "force_directed", "limit": 500},
            {"layout": "circular", "limit": 1000},
            {"layout": "hierarchical", "limit": 2000},
            {"layout": "force_directed", "limit": 500, "clustered": True}
        ]
        
        for config in viz_configs:
            viz_start = time.time()
            memory_before = self.get_memory_usage()
            
            response = await async_client.get("/api/knowledge-graph/visualization/", params=config)
            viz_time = time.time() - viz_start
            memory_after = self.get_memory_usage()
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify visualization data structure
            assert "nodes" in data
            assert "edges" in data
            assert "layout" in data
            
            expected_nodes = min(config["limit"], viz_node_count)
            assert len(data["nodes"]) <= expected_nodes
            
            # Performance assertions
            assert viz_time < 3.0  # Visualization should generate within 3 seconds
            assert (memory_after - memory_before) < 200  # Should use less than 200MB
            
            print(f"Visualization {config['layout']} ({config['limit']} nodes): {len(data['nodes'])} nodes, {len(data['edges'])} edges in {viz_time:.3f}s")

    @pytest.mark.asyncio 
    async def test_graph_caching_performance(self, async_client: AsyncClient):
        """Test performance impact of graph caching"""
        
        # Create test data
        node_response = await async_client.post("/api/knowledge-graph/nodes/", json={
            "node_type": "java_class",
            "properties": {"name": "CacheTestNode"}
        })
        node_id = node_response.json()["id"]
        
        # Test cache hit/miss performance
        cache_test_queries = [
            f"/api/knowledge-graph/nodes/{node_id}",
            f"/api/knowledge-graph/nodes/{node_id}/neighbors",
            f"/api/knowledge-graph/search/?query=CacheTestNode"
        ]
        
        for query_url in cache_test_queries:
            # First request (cache miss)
            miss_start = time.time()
            response1 = await async_client.get(query_url)
            miss_time = time.time() - miss_start
            
            # Second request (cache hit)
            hit_start = time.time()
            response2 = await async_client.get(query_url)
            hit_time = time.time() - hit_start
            
            # Both should succeed
            assert response1.status_code == 200
            assert response2.status_code == 200
            
            # Data should be identical
            assert response1.json() == response2.json()
            
            # Cache hit should be faster
            if hit_time > 0:  # Only check if measurable
                cache_speedup = miss_time / hit_time
                print(f"Cache test {query_url}: miss={miss_time:.3f}s, hit={hit_time:.3f}s, speedup={cache_speedup:.1f}x")
                
                # Cache should provide some speedup
                assert cache_speedup > 1.1  # At least 10% faster

    @pytest.mark.asyncio
    async def test_graph_scalability_limits(self, async_client: AsyncClient):
        """Test graph system behavior at scalability limits"""
        
        # Test with increasing graph sizes
        test_sizes = [1000, 5000, 10000]
        
        for size in test_sizes:
            print(f"\nTesting scalability with {size} nodes...")
            
            # Clean graph for this test
            await async_client.delete("/api/knowledge-graph/test-data/clear")
            
            # Create nodes
            node_creation_times = []
            batch_size = 100
            
            for batch_start in range(0, size, batch_size):
                batch_nodes = []
                for i in range(min(batch_size, size - batch_start)):
                    batch_nodes.append({
                        "node_type": "java_class",
                        "properties": {"name": f"ScaleNode{batch_start + i}"}
                    })
                
                creation_start = time.time()
                response = await async_client.post("/api/knowledge-graph/nodes/batch", json={"nodes": batch_nodes})
                creation_time = time.time() - creation_start
                node_creation_times.append(creation_time)
                
                assert response.status_code == 201
                
                # Performance should not degrade significantly
                if len(node_creation_times) > 5:
                    recent_avg = sum(node_creation_times[-5:]) / 5
                    assert recent_avg < 2.0  # Batch should complete within 2 seconds
            
            # Test query performance at scale
            query_start = time.time()
            response = await async_client.get("/api/knowledge-graph/search/", params={
                "query": "ScaleNode",
                "limit": 100
            })
            query_time = time.time() - query_start
            
            assert response.status_code == 200
            assert query_time < 5.0  # Queries should remain fast even at scale
            
            # Memory usage check
            current_memory = self.get_memory_usage()
            print(f"Graph size {size}: Memory {current_memory:.1f}MB, Query time {query_time:.3f}s")
            
            # Memory should scale reasonably
            memory_per_node = current_memory / size
            assert memory_per_node < 0.1  # Less than 100KB per node
            
            # System should remain responsive
            health_response = await async_client.get("/api/knowledge-graph/health/")
            assert health_response.status_code == 200
            health_data = health_response.json()
            assert health_data["status"] == "healthy"
