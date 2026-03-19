# Context: Phase 08-03 - Custom Model Training

**Phase**: 08-03  
**Milestone**: v3.0: Advanced AI  
**Goal**: Fine-tuned model specifically for Minecraft mod conversion

---

## Locked Decisions

### From PROJECT.md
1. **Translation Model**: CodeT5+ 16B (encoder-decoder optimal for seq2seq) - already selected
2. **RAG Embeddings**: BGE-M3 (64.3 MTEB score, free self-hosted) - already selected
3. **Multi-agent QA**: MetaGPT pattern - implemented in existing codebase
4. **Success Target**: 80%+ conversion accuracy, 60-80% automation acceptable

### From ROADMAP.md
1. **REQ-3.3**: Custom Model Training is a HIGH priority requirement
2. **Dependencies**: REQ-1.4 (AI Code Translation must be complete first)
3. **Timeline**: Part of v3.0 milestone (Months 10-12)

### From MILESTONE-v2.5-PLAN.md
- Milestone v2.5 is complete (2026-03-18)
- Current milestone is v3.0: Advanced AI
- Phase 08-01 and 08-02 may have been completed previously

---

## Technical Context

### What Exists
- AI Engine with CrewAI + LangChain
- FastAPI Backend with 24 routers
- React Frontend with 23 component directories
- PostgreSQL + pgvector for RAG
- Redis for job queue and caching
- Conversion pipeline that processes mods

### What's Needed for Model Training
1. **Training Data**: Minimum 1000 high-quality conversion pairs
2. **GPU Infrastructure**: GPU training environment (Modal or similar)
3. **Fine-tuning Approach**: LoRA/QLoRA for efficient fine-tuning
4. **Base Model**: CodeLlama or similar code generation model
5. **MLflow**: For model registry and tracking
6. **A/B Testing Infrastructure**: For comparing base vs. fine-tuned model

### Constraints
- Training must complete in <24 hours
- Model latency must be <2x of base model
- Need 5%+ accuracy improvement over base model
- A/B test must show statistically significant improvement

---

## Phase Dependencies

### Predecessors
- Phase 08-01: Better Semantic Understanding (likely completed)
- Phase 08-02: Self-Learning System (likely completed)

### This Phase (08-03)
- Task 08-03-01: Training Data Pipeline
- Task 08-03-02: Fine-Tuning Infrastructure  
- Task 08-03-03: Model Deployment & Testing

---

## Technical Decisions Required

1. **Base Model Selection**: CodeLlama vs. DeepSeek-Coder-V2 vs. StarCoder
2. **Fine-tuning Method**: LoRA vs. QLoRA vs. full fine-tuning
3. **Training Infrastructure**: Modal vs. cloud GPU vs. local GPU
4. **Model Registry**: MLflow vs. Weights & Biases vs. custom
5. **A/B Testing Strategy**: Shadow mode vs. canary deployment

---

## Risks

1. **Data Quality**: Need high-quality conversion pairs (not just successful ones)
2. **Training Time**: <24 hours constraint may be challenging
3. **Improvement Measurement**: 5% improvement is measurable but may require careful evaluation
4. **Latency Tradeoff**: Fine-tuned models may be slower than base model

---

*Generated: 2026-03-19*
*For Phase 08-03 Planning*
