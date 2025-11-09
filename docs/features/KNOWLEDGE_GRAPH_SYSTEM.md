# Knowledge Graph System Documentation

## Overview

The Knowledge Graph System is a sophisticated component of ModPorter-AI that captures, stores, and analyzes semantic relationships between Java code entities, Minecraft modding concepts, and conversion patterns. It provides the foundation for intelligent code transformation and knowledge management.

## Architecture

### Core Components

1. **Graph Database Layer** (`backend/src/db/graph_db.py`)
   - Neo4j integration for semantic graph storage
   - PostgreSQL fallback with pgvector for graph operations
   - Automatic database selection based on configuration

2. **Knowledge Models** (`backend/src/db/knowledge_graph_crud.py`)
   - Node management (classes, methods, blocks, items)
   - Edge management (relationships, dependencies)
   - Graph traversal and querying capabilities

3. **API Layer** (`backend/src/api/knowledge_graph.py`)
   - RESTful endpoints for graph operations
   - Search and filtering capabilities
   - Visualization data preparation

4. **Frontend Component** (`frontend/src/components/KnowledgeGraphViewer/`)
   - Interactive D3.js-based visualization
   - Real-time graph exploration
   - Node and edge inspection

## Key Features

### 1. Semantic Code Analysis

The system automatically extracts semantic relationships from Java code:

```python
# Example: Extracted relationships
{
  "nodes": [
    {
      "type": "java_class",
      "properties": {
        "name": "BlockRegistry",
        "package": "net.minecraft.block",
        "modifiers": ["public", "final"]
      }
    }
  ],
  "edges": [
    {
      "type": "extends",
      "source": "CustomBlock",
      "target": "Block",
      "properties": {
        "inheritance_depth": 2
      }
    }
  ]
}
```

### 2. Graph Visualization

Interactive D3.js visualization with:
- Force-directed layout algorithms
- Node clustering and grouping
- Real-time filtering and search
- Zoom and pan capabilities
- Custom styling based on node types

### 3. Pattern Recognition

Automatic detection of common patterns:
- Design patterns (Factory, Observer, etc.)
- Minecraft-specific patterns (Block registration, Entity creation)
- Anti-patterns and code smells
- Performance bottlenecks

### 4. Knowledge Inference

The system can infer new knowledge:
- Missing relationships
- Potential refactorings
- Optimization opportunities
- Conversion paths

## API Reference

### Nodes

#### Create Node
```http
POST /api/knowledge-graph/nodes/
Content-Type: application/json

{
  "node_type": "java_class",
  "properties": {
    "name": "CustomBlock",
    "package": "com.example.mod"
  },
  "metadata": {
    "source_file": "CustomBlock.java",
    "lines": [1, 100]
  }
}
```

#### Get Node
```http
GET /api/knowledge-graph/nodes/{node_id}
```

#### Search Nodes
```http
GET /api/knowledge-graph/search/?query=BlockRegistry&node_type=java_class&limit=50
```

#### Get Node Neighbors
```http
GET /api/knowledge-graph/nodes/{node_id}/neighbors?depth=2
```

### Edges

#### Create Edge
```http
POST /api/knowledge-graph/edges/
Content-Type: application/json

{
  "source_id": "node-1",
  "target_id": "node-2",
  "relationship_type": "depends_on",
  "properties": {
    "strength": 0.8
  }
}
```

#### Path Analysis
```http
GET /api/knowledge-graph/path/{source_id}/{target_id}?max_depth=5
```

#### Subgraph Extraction
```http
GET /api/knowledge-graph/subgraph/{center_id}?radius=2&min_connections=3
```

### Advanced Queries

#### Cypher Query Support
```http
POST /api/knowledge-graph/query/
Content-Type: application/json

{
  "query": "MATCH (n:java_class)-[r:extends]->(m:java_class) RETURN n, r, m",
  "parameters": {}
}
```

#### Graph Statistics
```http
GET /api/knowledge-graph/statistics/
```

## Frontend Component Usage

### Basic Integration

```typescript
import KnowledgeGraphViewer from '../components/KnowledgeGraphViewer';

function ModAnalysis() {
  return (
    <div>
      <h2>Code Relationship Analysis</h2>
      <KnowledgeGraphViewer
        onNodeSelect={(node) => console.log('Selected:', node)}
        filters={{
          nodeTypes: ['java_class', 'minecraft_block'],
          edgeTypes: ['extends', 'creates']
        }}
        layout="force_directed"
      />
    </div>
  );
}
```

### Advanced Configuration

```typescript
<KnowledgeGraphViewer
  // Node and edge styling
  nodeStyle={{
    fill: (d) => d.type === 'java_class' ? '#4CAF50' : '#2196F3',
    radius: 8,
    strokeWidth: 2
  }}
  edgeStyle={{
    stroke: '#999',
    strokeWidth: 2,
    arrowhead: true
  }}
  
  // Layout options
  layout={{
    type: 'force_directed',
    iterations: 1000,
    charge: -300,
    linkDistance: 50
  }}
  
  // Interaction handlers
  onNodeDoubleClick={(node) => openNodeDetails(node)}
  onEdgeClick={(edge) => showEdgeProperties(edge)}
  onGraphUpdate={(stats) => console.log('Graph updated:', stats)}
  
  // Performance optimization
  virtualization={true}
  maxVisibleNodes={1000}
/>
```

## Data Model

### Node Types

| Type | Description | Properties |
|------|-------------|------------|
| `java_class` | Java class or interface | `name`, `package`, `modifiers`, `extends`, `implements` |
| `java_method` | Java method or function | `name`, `parameters`, `return_type`, `visibility` |
| `minecraft_block` | Minecraft block | `name`, `material`, `properties`, `states` |
| `minecraft_item` | Minecraft item | `name`, `type`, `properties`, `creative_tab` |
| `minecraft_entity` | Minecraft entity | `name`, `type`, `behaviors`, `attributes` |

### Edge Types

| Type | Description | Properties |
|------|-------------|------------|
| `extends` | Class inheritance | `depth`, `type` (class/interface) |
| `implements` | Interface implementation | `methods_implemented` |
| `depends_on` | Dependency relationship | `strength`, `type` (compile/runtime) |
| `creates` | Creation relationship | `method`, `frequency` |
| `modifies` | Modification relationship | `fields_modified`, `access_pattern` |
| `calls` | Method invocation | `frequency`, `parameters` |

## Performance Considerations

### Graph Size

- **Small graphs** (< 1,000 nodes): Real-time updates, full interactivity
- **Medium graphs** (1,000-10,000 nodes): Virtualization, optimized rendering
- **Large graphs** (> 10,000 nodes): Clustering, summary views

### Optimization Techniques

1. **Virtualization**: Only render visible nodes
2. **Clustering**: Group related nodes into clusters
3. **Level-of-Detail**: Simplify rendering when zoomed out
4. **Lazy Loading**: Load graph data on-demand
5. **Caching**: Cache frequently accessed subgraphs

### Memory Management

```typescript
// Enable virtualization for large graphs
<KnowledgeGraphViewer
  virtualization={true}
  maxVisibleNodes={500}
  clusterThreshold={1000}
/>
```

## Security Considerations

### Access Control

- Role-based permissions for graph operations
- Read-only access for visualization
- Write access for knowledge extraction
- Admin access for graph management

### Data Privacy

- Sensitive code is obfuscated in the graph
- Access logging for all graph operations
- Optional encryption for sensitive relationships

## Testing

### Unit Tests

```bash
# Run knowledge graph tests
npm run test:knowledge-graph

# With coverage
npm run test:knowledge-graph -- --coverage
```

### Integration Tests

```bash
# Test graph API endpoints
npm run test:integration -- --testNamePattern="KnowledgeGraph"

# Test frontend component
npm run test:component -- KnowledgeGraphViewer
```

### Performance Tests

```bash
# Load testing for graph operations
npm run test:performance -- --graph-size=10000

# Memory usage testing
npm run test:memory -- KnowledgeGraphViewer
```

## Troubleshooting

### Common Issues

#### Graph Not Loading

1. Check Neo4j/PostgreSQL connection
2. Verify database credentials
3. Check API endpoint availability

```python
# Test database connection
from backend.src.db.graph_db import get_graph_db

try:
    db = get_graph_db()
    result = db.test_connection()
    print("Graph database connected:", result)
except Exception as e:
    print("Graph database error:", e)
```

#### Slow Rendering

1. Enable virtualization
2. Reduce visible nodes
3. Optimize query complexity

```typescript
// Enable performance optimizations
<KnowledgeGraphViewer
  virtualization={true}
  maxVisibleNodes={200}
  enableClustering={true}
  simplifyOnZoom={true}
/>
```

#### Memory Issues

1. Monitor memory usage
2. Implement data cleanup
3. Use streaming for large datasets

```python
# Monitor graph memory usage
import psutil

def monitor_graph_memory():
    process = psutil.Process()
    memory_info = process.memory_info()
    return memory_info.rss / 1024 / 1024  # MB
```

### Debug Tools

#### Graph Inspection

```typescript
// Enable debug mode
<KnowledgeGraphViewer
  debug={true}
  onDebugInfo={(info) => console.log('Debug:', info)}
/>
```

#### Query Analysis

```python
# Analyze query performance
from backend.src.db.knowledge_graph_crud import analyze_query

query = "MATCH (n) RETURN n"
analysis = analyze_query(query)
print("Query analysis:", analysis)
```

## Future Enhancements

### Planned Features

1. **Machine Learning Integration**
   - Predictive relationship inference
   - Automatic code refactoring suggestions
   - Anomaly detection in code patterns

2. **Collaborative Knowledge Building**
   - Community contribution system
   - Peer review of graph edits
   - Reputation-based trust scoring

3. **Advanced Visualization**
   - 3D graph visualization
   - Timeline-based graph evolution
   - Interactive storyboarding

4. **Performance Improvements**
   - GPU-accelerated rendering
   - Distributed graph processing
   - Real-time streaming updates

### Roadmap

- **Q1 2024**: ML integration, community features
- **Q2 2024**: Advanced visualization, performance optimization
- **Q3 2024**: Distributed processing, real-time updates
- **Q4 2024**: Full production deployment, enterprise features

## Contributing

### Development Setup

```bash
# Clone the repository
git clone https://github.com/modporter-ai/modporter-ai.git
cd modporter-ai

# Set up development environment
npm install
cd backend && pip install -r requirements.txt

# Start development servers
npm run dev
cd ../backend && python -m uvicorn main:app --reload
```

### Adding New Features

1. Create feature branch: `git checkout -b feature/new-graph-feature`
2. Implement backend changes in `backend/src/db/graph_db.py`
3. Add API endpoints in `backend/src/api/knowledge_graph.py`
4. Update frontend component in `frontend/src/components/KnowledgeGraphViewer/`
5. Add tests in appropriate test directories
6. Submit pull request with comprehensive documentation

### Code Style

- Backend: Follow PEP 8, use type hints
- Frontend: Follow ESLint rules, use TypeScript
- Tests: Aim for 80%+ coverage
- Documentation: Update this file for all changes

## License

This component is part of the ModPorter-AI project and follows the same license terms as the main project.

## Support

For questions, issues, or contributions:

- GitHub Issues: [ModPorter-AI Issues](https://github.com/modporter-ai/modporter-ai/issues)
- Documentation: [Full API Documentation](./API_COMPREHENSIVE.md)
- Community: [Discord Server](https://discord.gg/modporter-ai)
