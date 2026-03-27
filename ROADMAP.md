# ModPorter AI - Comprehensive Development Roadmap

**Last Updated:** 2025-02-12
**Status:** Active Development
**Current Phase:** Pre-MVP - Vertical Slice Completion

---

## Executive Summary

This roadmap synthesizes insights from Google Gemini's feasibility assessment, the PRD, AI Expert Strategic Recommendations, and current codebase analysis. The project is **conditionally feasible** using the "Smart Assumption" strategy - shifting from perfect replication to intelligent adaptation.

**Critical Insight:** The JavaAnalyzerAgent already has real AST parsing (not a stub), the BedrockArchitectAgent has a full SmartAssumptionEngine, and the PackagingAgent was recently fixed with proper Bedrock structure. The main blocking issues are the Texture Pipeline and end-to-end integration.

**Target MVP:** Convert a simple Java block mod (e.g., `simple_copper_block.jar`) into a working `.mcaddon` file that installs in Bedrock Edition.

---

## Current State Assessment

### ✅ What's Working (Production-Ready)

| Component | Status | Notes |
|-----------|--------|-------|
| **JavaAnalyzerAgent** | ✅ Fully Implemented | Real AST parsing via `javalang`, JAR extraction, metadata analysis |
| **BedrockArchitectAgent** | ✅ Fully Implemented | SmartAssumptionEngine with conflict resolution, conversion planning |
| **SmartAssumptions System** | ✅ Fully Implemented | Priority-based resolution, comprehensive assumption table |
| **PackagingAgent** | ✅ Recently Fixed | Proper Bedrock folder structure (behavior_packs/, resource_packs/) |
| **Crew Orchestration** | ✅ Fully Implemented | Sequential workflow with enhanced variants, A/B testing support |
| **Docker Infrastructure** | ✅ Complete | Dev/production configurations, health checks, hot reload |
| **Test Fixtures** | ✅ Good Coverage | Test JAR generators, texture creators, sample mods |

### ⚠️ What's Partial (Framework Exists, Needs Implementation)

| Component | Status | Gap |
|-----------|--------|-----|
| **LogicTranslatorAgent** | ⚠️ Partial | Has type/API mapping and basic translation, but needs expansion for complex logic |
| **AssetConverterAgent** | ⚠️ Framework Only | 3,350 lines of structure, but actual image/audio conversion is placeholder |
| **Template System** | ⚠️ Limited | Basic block templates exist, need entity/item/recipe expansion |
| **RAG System** | ⚠️ Infrastructure Only | Vector database setup exists, but embedding generation is TODO |
| **Frontend Components** | ⚠️ Partial | Components exist but lack full backend integration |

### ❌ What's Missing (Blocking MVP)

| Component | Status | Impact |
|-----------|--------|--------|
| **Texture Conversion Pipeline** | ❌ Critical | Visual assets not carried over - blocks appear invisible |
| **End-to-End Testing** | ❌ Critical | Cannot validate if conversion produces working .mcaddon |
| **QA Validation** | ❌ Placeholder | Returns mock data only, no real testing framework |
| **Frontend Integration** | ❌ Incomplete | No real conversion workflow UI with progress tracking |

---

## Probability of Success by Feature Area

Based on Gemini's analysis and current implementation:

| Feature Area | Probability | Rationale |
|--------------|-------------|-----------|
| **Data Conversion (Blocks/Items/Recipes)** | 90% | Template capability is close, SmartAssumptions handle edge cases |
| **Simple Logic (Events/Commands)** | 60% | LogicTranslatorAgent has foundation, needs fine-tuning |
| **Complex Systems (Tech/Magic mods)** | 20% | Will always require human intervention via Post-Conversion Editor |
| **Asset Conversion (Textures/Models)** | 80% | Straightforward with proper libraries (Pillow, audio converters) |
| **Full Modpack Conversion** | 40% | Dependency resolution is inherently complex |

---

## Phase 1: MVP Vertical Slice (Weeks 1-3)

**Goal:** One complete end-to-end conversion of a simple block mod

### 1.1 Texture Pipeline Implementation (Days 1-3)

**Priority:** 🔴 CRITICAL - Blocks MVP completely

**Tasks:**
- [ ] Install image processing library (Pillow/PIL)
- [ ] Implement PNG optimization and format validation
- [ ] Create asset path mapping system (Java → Bedrock structure)
- [ ] Handle texture atlas extraction for simple mods
- [ ] Add texture validation (dimensions, format)
- [ ] Implement fallback to default texture if conversion fails

**Implementation Location:** `ai-engine/agents/asset_converter.py`

**Code Changes Needed:**
```python
# Replace placeholder texture conversion with actual implementation
from PIL import Image
import io

def convert_texture(java_texture_path: Path, output_dir: Path) -> Path:
    """Convert Java texture to Bedrock-compatible format"""
    # 1. Load and validate PNG
    # 2. Resize if necessary (power of 2)
    # 3. Optimize compression
    # 4. Save to Bedrock path structure
    pass
```

**Acceptance Criteria:**
- Simple block mod with texture converts to visible block in Bedrock
- Texture appears correctly in creative inventory and when placed
- Invalid textures are logged and handled gracefully

**Related Files:**
- `ai-engine/agents/asset_converter.py` (lines 34-56 placeholder)
- `tests/fixtures/create_test_texture.py` (test texture generator)

### 1.2 End-to-End Integration Testing (Days 4-6)

**Priority:** 🔴 CRITICAL - Cannot validate MVP without testing

**Tasks:**
- [ ] Create comprehensive integration test suite
- [ ] Build test fixture: `simple_copper_block.jar` with known properties
- [ ] Implement automated .mcaddon validation (unzip, check structure)
- [ ] Add in-game testing capability (requires manual verification initially)
- [ ] Create test matrix for different block types (solid, transparent, custom model)

**Implementation Location:** `tests/test_mvp_conversion.py` (new)

**Test Cases:**
```python
def test_simple_block_conversion():
    """Test end-to-end conversion of a simple block mod"""
    # 1. Load test JAR
    # 2. Run conversion crew
    # 3. Validate .mcaddon structure
    # 4. Extract and check manifest.json
    # 5. Verify block definition JSON
    # 6. Confirm texture present and valid
    pass

def test_converted_addon_loads_in_bedrock():
    """Manual test: Verify converted addon loads without errors"""
    # This requires manual testing in Minecraft Bedrock
    # Document expected results
    pass
```

**Acceptance Criteria:**
- `pytest tests/test_mvp_conversion.py` passes consistently
- Generated .mcaddon has valid structure per Bedrock spec
- Manual test: Block appears in creative inventory
- Manual test: Block can be placed and destroyed

### 1.3 Packaging Validation & Fixes (Days 7-8)

**Priority:** 🟡 HIGH - Recent fixes need validation

**Tasks:**
- [ ] Verify behavior_packs/ and resource_packs/ folder structure
- [ ] Validate manifest.json generation (UUIDs, versioning)
- [ ] Test .mcaddon installation in real Bedrock client
- [ ] Add pack validation against Minecraft Bedrock schema
- [ ] Implement packaging error handling and rollback

**Implementation Location:** `ai-engine/agents/packaging_agent.py`

**Validation Checklist:**
- [ ] .mcaddon unzips to valid structure
- [ ] manifest.json has all required fields
- [ ] Block definitions match Bedrock JSON schema
- [ ] Textures at correct paths (textures/blocks/)
- [ ] No orphaned temporary files

**Acceptance Criteria:**
- Generated .mcaddon imports without warnings in Bedrock
- All JSON files validate against official schemas
- Clean build process with no leftover temp files

### 1.4 Frontend MVP Integration (Days 9-12)

**Priority:** 🟡 HIGH - Required for user testing

**Tasks:**
- [ ] Implement conversion upload component (drag-drop JAR)
- [ ] Add real-time progress tracking via WebSocket
- [ ] Create conversion results display component
- [ ] Implement .mcaddon download functionality
- [ ] Add error display and user feedback
- [ ] Create conversion summary view (Smart Assumptions applied)

**Implementation Location:**
- `frontend/src/components/ConversionUpload/`
- `frontend/src/components/ConversionProgress/`
- `frontend/src/components/ConversionReport/`

**API Endpoints Needed:**
```
POST /api/v1/conversions          # Start conversion
GET  /api/v1/conversions/{id}     # Get status
WS   /api/v1/conversions/{id}/ws  # Real-time progress
GET  /api/v1/conversions/{id}/download  # Download .mcaddon
```

**Acceptance Criteria:**
- User can upload JAR and see conversion progress
- Progress updates in real-time as agents complete
- Final report shows which Smart Assumptions were applied
- Download button appears when conversion completes

### 1.5 QA Validation Framework (Days 12-15)

**Priority:** 🟢 MEDIUM - Nice to have for MVP

**Tasks:**
- [ ] Implement basic JSON schema validation
- [ ] Add texture existence checks
- [ ] Create manifest.json validator
- [ ] Build block definition validator
- [ ] Generate QA report with pass/fail for each check

**Implementation Location:** `ai-engine/agents/qa_validator.py`

**Validation Rules:**
```python
VALIDATION_RULES = {
    "manifest": {
        "format_version": [1, 2],
        "required_fields": ["uuid", "name", "version"],
    },
    "blocks": {
        "required_fields": ["format_version", "minecraft:block"],
        "textures": "must_exist",
    },
    "textures": {
        "format": "PNG",
        "dimensions": "power_of_2",
    }
}
```

**Acceptance Criteria:**
- QA report generated for each conversion
- Shows pass/fail for each validation category
- Links to detailed error messages
- Overall quality score (0-100%)

---

## Phase 2: Template Expansion (Weeks 4-7)

**Goal:** Support multiple mod types with expanded Smart Assumptions

### 2.1 Template Library (Week 4-5)

**Tasks:**
- [ ] Create entity template system (hostile/passive mobs)
- [ ] Build item template library (tools, armor, consumables)
- [ ] Implement recipe conversion templates (shaped, shapeless, furnace)
- [ ] Add container block template (chests, furnaces)
- [ ] Create interactive block template (buttons, levers)

**Implementation Location:** `ai-engine/templates/bedrock/`

**Template Structure:**
```
templates/bedrock/
├── blocks/
│   ├── basic_block.json.j2
│   ├── container_block.json.j2
│   ├── interactive_block.json.j2
│   └── transparent_block.json.j2
├── entities/
│   ├── passive_mob.json.j2
│   └── hostile_mob.json.j2
├── items/
│   ├── basic_item.json.j2
│   ├── tool.json.j2
│   └── consumable.json.j2
└── recipes/
    ├── shaped.json.j2
    └── shapeless.json.j2
```

**Acceptance Criteria:**
- Each template documented with parameters
- Templates generate valid Bedrock JSON
- Unit tests for each template type
- Template selection based on Java class analysis

### 2.2 Logic Translation Enhancement (Week 5-6)

**Tasks:**
- [ ] Expand Java to JavaScript type mapping
- [ ] Implement event handler generation (block break, entity spawn)
- [ ] Add crafting recipe AST translation
- [ ] Create method translation for common patterns
- [ ] Build glue code generation for complex interactions

**Implementation Location:** `ai-engine/agents/logic_translator.py`

**Translation Patterns:**
```python
TRANSLATION_PATTERNS = {
    "block.onBreak": """
    MinecraftEvents.blockBreak.subscribe((event) => {
        // Converted logic
    });
    """,
    "entity.onHit": """
    MinecraftEvents.entityHit.subscribe((event) => {
        // Converted logic
    });
    """,
}
```

**Acceptance Criteria:**
- Simple event handlers convert successfully
- Recipe data types convert correctly
- Complex logic falls back to comments explaining gap
- Translation report shows what was converted vs. commented out

### 2.3 Smart Assumptions Expansion (Week 6-7)

**Tasks:**
- [ ] Implement assumption logging and reporting
- [ ] Add feature downgrade logic (complex → simple)
- [ ] Create user notification system for assumptions
- [ ] Build assumption conflict resolution UI
- [ ] Add assumption validation (check if workaround viable)

**Implementation Location:** `ai-engine/models/smart_assumptions.py`

**New Assumptions to Add:**
| Java Feature | Smart Assumption |
|--------------|-----------------|
| Custom Biomes | Convert to large structure with terrain |
| Custom Enchantments | Add as item attributes or exclude |
| Redstone Logic | Simplify to basic on/off or exclude |
| Fluid Systems | Replace with lava/water or exclude |

**Acceptance Criteria:**
- Every assumption is logged and reported
- User sees clear explanation of why assumption was made
- Conflicting assumptions resolved deterministically
- Conversion report shows "What Changed" section

---

## Phase 3: Production Readiness (Weeks 8-11)

**Goal:** Scalable, user-ready conversion system

### 3.1 Frontend Completion (Week 8-9)

**Tasks:**
- [ ] Complete conversion workflow UI
- [ ] Add advanced options panel (assumption preferences)
- [ ] Implement conversion history and management
- [ ] Build batch conversion interface (modpacks)
- [ ] Create settings and configuration page

**Components to Complete:**
```
frontend/src/components/
├── BehaviorEditor/          # Post-conversion code editor
├── ComparisonView/          # Java vs Bedrock side-by-side
├── ConversionHistory/       # Past conversions
├── BatchConversion/         # Modpack upload
└── Settings/                # User preferences
```

**Acceptance Criteria:**
- Complete upload-to-download workflow
- Conversion history with re-download capability
- Batch upload for multiple mods
- Settings page for API keys, preferences

### 3.2 Performance Optimization (Week 9-10)

**Tasks:**
- [ ] Implement async conversion processing with queue
- [ ] Add file upload optimization (chunking, validation)
- [ ] Create conversion result caching
- [ ] Build rate limiting for API endpoints
- [ ] Optimize LLM token usage (context trimming)

**Performance Targets:**
| Metric | Target |
|--------|--------|
| Simple block conversion | <30 seconds |
| Small modpack (5 mods) | <5 minutes |
| Large modpack (20+ mods) | <20 minutes |
| Concurrent conversions | 10 simultaneous |
| API response time | <200ms (p95) |

**Implementation Locations:**
- `backend/src/api/` - Add rate limiting middleware
- `backend/src/services/queue.py` - Task queue (Celery or similar)
- `ai-engine/crew/` - Context window optimization

**Acceptance Criteria:**
- All performance targets met
- No memory leaks during long conversions
- Graceful handling of concurrent requests
- Efficient token usage (cost control)

### 3.3 Error Handling & Monitoring (Week 10-11)

**Tasks:**
- [ ] Implement comprehensive error handling
- [ ] Add structured logging with correlation IDs
- [ ] Create conversion failure analysis
- [ ] Build retry logic with exponential backoff
- [ ] Set up monitoring dashboards (Grafana/Prometheus)

**Error Categories:**
```python
ERROR_TYPES = {
    "parse_error": "Failed to analyze Java code",
    "asset_error": "Texture/model conversion failed",
    "logic_error": "Logic translation too complex",
    "package_error": "Failed to create .mcaddon",
    "validation_error": "Generated addon failed validation",
}
```

**Monitoring Metrics:**
- Conversion success rate (target: 80%+)
- Average conversion time by mod type
- LLM API call counts and costs
- Error rates by category
- User drop-off points in funnel

**Acceptance Criteria:**
- All errors caught and logged with context
- User sees helpful error messages
- Monitoring dashboard operational
- Alert system for critical failures

---

## Phase 4: Advanced Features (Weeks 12+)

**Goal:** Differentiation and power user features

### 4.1 Post-Conversion Editor (Week 12-14)

**Tasks:**
- [ ] Build dual-pane code editor (Java vs JavaScript)
- [ ] Implement syntax highlighting and error checking
- [ ] Add integrated Bedrock API documentation
- [ ] Create live preview of changes
- [ ] Implement one-click re-package of edited files

**Technology Options:**
- Monaco Editor (VS Code's editor)
- CodeMirror 6
- Ace Editor

**Acceptance Criteria:**
- Side-by-side view of original and converted code
- Edit Bedrock files with real-time validation
- Documentation panel for Bedrock APIs
- Export updated .mcaddon

### 4.2 AI-Powered Validation (Week 15-17)

**Tasks:**
- [ ] Implement Mode 1: Direct gameplay comparison
- [ ] Build local agent for Minecraft integration
- [ ] Create automated gameplay testing scripts
- [ ] Implement multimodal screenshot comparison
- [ ] Add Mode 2: Online research analysis

**Mode 1 Requirements:**
- Launch Java and Bedrock Minecraft locally
- Run automated test scripts (craft items, place blocks)
- Capture screenshots and gameplay footage
- Compare visual and functional differences

**Mode 2 Requirements:**
- Accept URLs to CurseForge/Modrinth/YouTube
- Multimodal analysis of original mod content
- Generate feature checklist from research
- Validate converted addon against checklist

**Acceptance Criteria:**
- Validation report scores conversion (0-100%)
- Side-by-side comparison of features
- Visual diff of screenshots
- List of missing or broken features

### 4.3 RAG & Learning System (Week 18-20)

**Tasks:**
- [ ] Implement actual embedding generation (OpenAI or local)
- [ ] Build knowledge base from Bedrock documentation
- [ ] Create successful conversion corpus
- [ ] Implement semantic search for conversion patterns
- [ ] Add feedback loop for model improvement

**RAG Implementation:**
```python
# Replace placeholder embeddings
from openai import OpenAI
client = OpenAI()

def generate_embedding(text: str) -> List[float]:
    response = client.embeddings.create(
        model="text-embedding-ada-002",
        input=text
    )
    return response.data[0].embedding
```

**Acceptance Criteria:**
- Real embeddings stored in PostgreSQL pgvector
- Semantic search returns relevant conversion examples
- System learns from successful manual conversions
- Conversion quality improves over time

### 4.4 RL Training Pipeline (Month 6+)

**Note:** Per expert recommendation, postpone until after production deployment

**Tasks:**
- [ ] Collect 1000+ labeled conversion examples
- [ ] Define reward function (conversion success, user feedback)
- [ ] Implement simulation environment for training
- [ ] Train RL model on conversion policy
- [ ] A/B test RL vs rule-based conversion

**Prerequisites:**
- 6 months of production data
- 1000+ successful conversions
- Clear metrics for optimization
- User feedback on quality

**Acceptance Criteria:**
- RL model outperforms rule-based baseline
- Conversion success rate improves by 10%+
- User satisfaction scores increase
- System can handle novel mod types better

---

## Phase 5: Modpack & Complexity (Months 7-9)

**Goal:** Handle real-world modpack complexity

### 5.1 Modpack Support

**Tasks:**
- [ ] Parse CurseForge modpack manifests
- [ ] Implement Modrinth pack format support
- [ ] Add dependency analysis and resolution
- [ ] Create mod load order calculation
- [ ] Implement conflict detection between mods

**Challenges:**
- Circular dependencies
- API conflicts (Forge + Fabric mods)
- Shared asset namespace collisions
- Load order dependencies

### 5.2 Advanced Smart Assumptions

**Tasks:**
- [ ] Custom dimension → structure conversion
- [ ] Complex machinery → simplified block chains
- [ ] Custom GUI → in-game text replacement
- [ ] Energy systems → Bedrock alternatives

---

## Success Metrics & Validation

### Technical Metrics

| Metric | MVP Target | Phase 2 Target | Phase 3 Target |
|--------|-----------|----------------|----------------|
| Conversion Success Rate | 80% (simple blocks) | 70% (multi-feature) | 60% (complex mods) |
| Processing Time | <30s (block) | <2m (small mod) | <5m (modpack) |
| Package Validity | 100% | 100% | 100% |
| Asset Preservation | 95% | 90% | 85% |
| Test Coverage | 60% | 75% | 85% |

### User Experience Metrics

| Metric | Target |
|--------|--------|
| Upload to Download | <2 minutes end-to-end |
| Error Clarity | All failures have explanations |
| Smart Assumption Transparency | 100% of assumptions reported |
| Feature Coverage | Blocks, items, basic recipes by Phase 2 |

### Quality Gates

**MVP Gate (Week 3):**
- [ ] Simple block mod converts to working .mcaddon
- [ ] Texture appears correctly in Bedrock
- [ ] Block can be placed and destroyed
- [ ] Frontend upload-to-download flow works

**Phase 2 Gate (Week 7):**
- [ ] Items, entities, recipes convert successfully
- [ ] Smart Assumptions reported clearly
- [ ] Conversion success rate >70% for test suite

**Phase 3 Gate (Week 11):**
- [ ] Production-ready performance
- [ ] Error handling comprehensive
- [ ] Monitoring and alerting operational

---

## Risk Mitigation

### High-Risk Dependencies

| Risk | Mitigation | Contingency |
|------|-----------|-------------|
| Java AST parsing failures | Pre-validate javalang performance | Fall back to regex-based analysis |
| Bedrock API changes | Monitor Minecraft release cycle | Version-locked templates |
| LLM reliability issues | Implement fallback rule-based conversion | Local LLM deployment |
| File size limits | Test large modpacks early | Queue-based processing |
| Texture conversion failures | Robust error handling | Fallback to default textures |

### Contingency Plans

**Parser Failure:**
- Primary: javalang AST parsing
- Fallback: Regex pattern matching
- Last Resort: Manual annotation via user input

**Template Gaps:**
- Primary: Comprehensive template library
- Fallback: Generic placeholder template
- Long-term: AI-generated templates

**Performance Issues:**
- Primary: Async queue processing
- Fallback: Batch processing with notifications
- Scale: Horizontal scaling of worker nodes

**API Cost Overruns:**
- Primary: Token optimization
- Fallback: Local LLM (Ollama)
- Cache: Aggressive result caching

---

## Dependencies & Prerequisites

### External Dependencies

**Required:**
- Python 3.9+
- Node.js 22+ (Vite 7.2.2+)
- Docker & Docker Compose
- PostgreSQL 15 with pgvector
- Redis 7

**Python Packages:**
```
javalang          # Java AST parsing
Pillow            # Image processing
crewai            # Agent orchestration
langchain         # LLM framework
fastapi           # API framework
asyncpg           # Async PostgreSQL
```

**Node Packages:**
```
react@19          # Frontend framework
vite@7.2.2+       # Build tool
typescript        # Type safety
```

### API Keys Required

**Development:**
- `OPENAI_API_KEY` - For embeddings and advanced LLM calls
- `ANTHROPIC_API_KEY` - For Claude models (optional, recommended)

**Production:**
- All development keys
- Monitoring service (DataDog, New Relic, or similar)
- Error tracking (Sentry)

### Infrastructure

**Development:**
- Local Docker with 8GB RAM minimum
- 4 CPU cores recommended

**Production:**
- Cloud hosting (AWS, GCP, Azure)
- Managed PostgreSQL (RDS, Cloud SQL)
- Managed Redis (ElastiCache, Redis Cloud)
- Object storage (S3, Cloud Storage)
- CDN for frontend assets

---

## Resource Allocation

### Team Structure (Ideal)

**Phase 1-3 (MVP to Production):**
- 1 Senior Backend Engineer (AI/Python focus)
- 1 Full Stack Engineer (Frontend + Backend API)
- 1 DevOps Engineer (Infrastructure, 50% time)
- 1 QA Engineer (Testing, 50% time)

**Phase 4+ (Advanced Features):**
- Add 1 ML Engineer (RAG, RL)
- Add 1 Frontend Specialist (Editor, UI polish)

### Time Allocation by Phase

| Phase | Duration | Backend | Frontend | DevOps | Testing |
|-------|----------|---------|----------|--------|---------|
| Phase 1 | 3 weeks | 60% | 30% | 5% | 5% |
| Phase 2 | 4 weeks | 50% | 30% | 10% | 10% |
| Phase 3 | 4 weeks | 40% | 40% | 10% | 10% |
| Phase 4 | 8 weeks | 50% | 40% | 5% | 5% |
| Phase 5 | 12 weeks | 60% | 20% | 10% | 10% |

---

## Related Documents

- [Product Requirements Document](PRD.md)
- [AI Expert Strategic Recommendations](AI_EXPERT_STRATEGIC_RECOMMENDATIONS.md)
- [API Documentation](API.md)
- [Contributing Guidelines](../CONTRIBUTING.md)

---

## Change Log

| Date | Version | Changes | Author |
|------|---------|---------|--------|
| 2025-02-12 | 1.0 | Initial roadmap creation based on codebase analysis and Gemini guidance | Claude Code |

---

**Next Steps:**

1. **Immediate (This Week):** Start Texture Pipeline implementation (Phase 1.1)
2. **Parallel:** Set up end-to-end test infrastructure (Phase 1.2)
3. **Week 2:** Validate PackagingAgent fixes with real Bedrock testing
4. **Week 3:** Complete frontend MVP integration

**Remember:** The goal is a working vertical slice, not a perfect system. Get a simple block converting end-to-end, then expand. The "Smart Assumption" strategy means accepting 80% quality with transparency about the remaining 20%.
