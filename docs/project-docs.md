# Contributing Guidelines

Thank you for your interest in contributing to ModPorter AI! This document provides guidelines for contributing to the project.

## Development Setup

### Prerequisites
- Node.js 18+ and pnpm 7+
- Python 3.9+ and pip
- Docker and Docker Compose (optional but recommended)
- Git

### Quick Start
```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/ModPorter-AI.git
cd ModPorter-AI

# Install all dependencies
pnpm run install-all

# Start development environment
docker compose up -d

# Or start services individually
pnpm run dev
```

## Project Structure

```
ModPorter-AI/
├── frontend/          # React TypeScript frontend
├── backend/           # Python FastAPI backend  
├── ai-engine/         # CrewAI conversion engine
├── local-agent/       # Node.js local validation agent
├── docs/              # Documentation
└── tests/             # Integration tests
```

## Development Workflow

### 1. Test-Driven Development (TDD)
We follow TDD principles as specified in the PRD:

```bash
# Write tests first
pnpm run test:watch

# Implement feature
# Run tests to verify
pnpm run test
```

### 2. Code Quality Standards
- **Frontend**: ESLint + Prettier for TypeScript/React
- **Backend**: Flake8 + Black for Python
- **Testing**: Jest (frontend), pytest (backend)
- **Coverage**: Minimum 80% test coverage required

### 3. Commit Convention
We use Conventional Commits:
```
feat: add smart assumption for custom dimensions
fix: resolve file upload validation issue
docs: update API documentation
test: add conversion crew unit tests
```

### 4. Pull Request Process
1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Write tests following TDD approach
4. Implement feature according to PRD specifications
5. Ensure all tests pass: `pnpm run test`
6. Submit pull request with clear description

## PRD Compliance

All contributions must align with the Product Requirements Document:

### Core Features (Must Implement)
- **Feature 1**: One-Click Modpack Ingestion
- **Feature 2**: AI Conversion Engine (CrewAI multi-agent)
- **Feature 3**: Interactive Conversion Report
- **Feature 4**: AI-Powered Validation & Comparison
- **Feature 5**: Post-Conversion Editor (future)

### Smart Assumptions Implementation
Refer to PRD Section 1.0.2 for the complete Smart Assumptions table. Any new assumptions must:
1. Have clear PRD justification
2. Include user impact assessment
3. Provide fallback mechanisms
4. Generate transparent reports

## Testing Requirements

### Frontend Tests
```bash
cd frontend
pnpm test -- --coverage
```
- Component testing with React Testing Library
- User interaction testing
- Visual regression testing for UI components
- API integration testing

### Backend Tests
```bash
cd backend
pytest --cov=src tests/
```
- API endpoint testing
- Business logic unit tests
- Database integration tests
- Error handling verification

### AI Engine Tests
```bash
cd ai-engine
pytest --cov=src tests/
```
- CrewAI agent testing
- Smart assumption logic verification
- Conversion workflow testing
- Mock LLM response testing

#### RAG Testing Suite
```bash
cd ai-engine
# Run RAG-specific tests
pytest tests/test_rag_crew.py tests/unit/test_embedding_generator.py tests/integration/test_rag_workflow.py -v

# Run RAG evaluation suite
python src/testing/rag_evaluator.py

# Check RAG code quality
python check_code_quality.py
```
- RAG crew functionality testing
- Embedding generation and vector database testing
- End-to-end RAG workflow validation
- Knowledge retrieval accuracy assessment
- Performance metrics and evaluation

## Code Style

### TypeScript/React (Frontend)
```typescript
// Use functional components with hooks
const ConversionUpload: React.FC<Props> = ({ onConversionStart }) => {
  const [isConverting, setIsConverting] = useState(false);
  
  // Clear, descriptive function names
  const handleFileUpload = useCallback((file: File) => {
    // Implementation
  }, []);
  
  return (
    <div className="conversion-upload">
      {/* JSX */}
    </div>
  );
};
```

### Python (Backend/AI Engine)
```python
# Type hints for all functions
def convert_mod(mod_path: Path, output_path: Path) -> ConversionResult:
    """
    Convert Java mod to Bedrock add-on.
    
    Args:
        mod_path: Path to Java mod file
        output_path: Output directory for converted files
        
    Returns:
        ConversionResult with success/failure details
    """
    # Implementation
```

## Visual Learning Resources

Since the project targets visual learners, contributions should include:

### Documentation
- Mermaid diagrams for workflows
- Screenshots for UI components
- Video demos for complex features
- Interactive examples where possible

### UI/UX Guidelines
- Clear visual feedback for all user actions
- Progress indicators for long-running operations
- Intuitive icons and labels
- Responsive design for all screen sizes

## API Design

### RESTful Endpoints
Follow PRD API specifications:
```
POST /api/v1/convert              # Start conversion
GET  /api/v1/convert/{id}/status  # Check progress
GET  /api/v1/convert/{id}/download # Download result
```

### Error Handling
```json
{
  "error": "clear_user_message",
  "code": "CONVERSION_FAILED", 
  "details": {
    "stage": "analysis",
    "reason": "unsupported_mod_format"
  }
}
```

## Security Guidelines

### File Upload Security
- Validate file types and sizes
- Scan uploads for malicious content  
- Isolate processing in containers
- Clean up temporary files

### API Security
- Rate limiting on conversion endpoints
- Input validation and sanitization
- Secure handling of user uploads
- No storage of personal data

## Performance Requirements

### Response Times
- File upload: < 5 seconds
- Conversion start: < 10 seconds  
- Status updates: < 1 second
- Report generation: < 30 seconds

### Resource Usage
- Frontend bundle: < 2MB gzipped
- Memory usage: < 1GB per conversion
- Concurrent conversions: 10+ supported

## Documentation Standards

### Code Comments
```python
class SmartAssumptionEngine:
    """
    Implements PRD Section 1.0.2: Smart Assumptions for bridging Java/Bedrock gaps.
    
    This engine applies intelligent compromises when Java features cannot be 
    directly converted to Bedrock equivalents.
    """
    
    def apply_assumption(self, feature_type: str) -> ConversionResult:
        """
        Apply smart assumption for incompatible feature.
        
        Follows PRD Table of Smart Assumptions for consistent behavior.
        """
```

### API Documentation
Use OpenAPI/Swagger with clear examples:
```yaml
/convert:
  post:
    summary: Convert Java mod to Bedrock add-on
    description: |
      Implements PRD Feature 1: One-Click Modpack Ingestion
      
      Accepts .jar files, .zip modpack archives, or repository URLs
```

## Release Process

### Version Numbering
- Major: Breaking changes or new core features
- Minor: New features, backward compatible
- Patch: Bug fixes, small improvements

### Release Checklist
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Performance benchmarks met
- [ ] Security review completed
- [ ] PRD compliance verified

## Getting Help

### Communication Channels
- GitHub Issues: Bug reports and feature requests
- GitHub Discussions: General questions and ideas
- Pull Request Reviews: Code-specific feedback

### Resources
- [Product Requirements Document](docs/PRD.md)
- [API Documentation](docs/API.md)
- [Architecture Overview](docs/ARCHITECTURE.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
