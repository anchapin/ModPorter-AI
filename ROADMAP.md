# ModPorter AI — Development Roadmap

**Last Updated:** 2026-04-10
**Status:** Active Development — Week 1-2 Sprint (Conversion Proof + Pipeline Validation)
**Target:** Public launch of modporter.ai by June 22, 2026

---

## Executive Summary

ModPorter converts Minecraft Java mods to Bedrock add-ons. Positioned as a **B2B conversion accelerator** targeting Marketplace creators — handles 60-80% of the conversion work, with creators finishing the rest.

**Current pipeline maturity: ~25-30% weighted content coverage** (up from ~0% on Apr 7).

---

## Conversion Audit Status (Apr 10, 2026)

8 real-world Java mods tested across 3 audit cycles (v1→v2→v3):

| Metric | v1 (Apr 8) | v2 (Apr 9) | v3 (Apr 10) | Target |
|--------|-----------|-----------|------------|--------|
| Pass rate (valid .mcaddon) | 8/8 (100%) | 8/8 (100%) | **8/8 (100%)** | 100% |
| Texture coverage | ~0% | 54.8% | **54.7%** | 80%+ |
| Model coverage | 0% | 0.2% | **0%** | 60%+ |
| Recipe coverage | 0% | 0% | **0%** | 60%+ |
| Entity definitions | 1/mod | 1/mod | **15 total** | All detected |
| B2B readiness (weighted) | ~5% | ~25% | **~25-30%** | 60%+ |

### Per-Mod Highlights
- **Iron Chests**: 100% textures ✅ — ready as demo
- **Farmer's Delight**: 91% textures, but 0/533 recipes and 0/342 models
- **Create**: 49% textures, 9 entities — largest mod (19MB, 2,687 classes)
- **JEI/JourneyMap**: Low coverage — UI/map mods don't map well to Bedrock add-on format

### Test Mods (from Modrinth)
1. Iron Chests, 2. Waystones, 3. Farmer's Delight, 4. Supplementaries, 5. Create
6. Xaero's Minimap, 7. JourneyMap, 8. Just Enough Items (JEI)

---

## 11-Week Launch Roadmap

### ✅ Week 1-2: Conversion Proof + Pipeline Validation (Due: Apr 20)

**Status: ~95% complete**

| Issue | Description | Status |
|-------|-------------|--------|
| #999 | Bulk texture extraction | ✅ Closed — 54.7% texture coverage |
| #982/#983 | Entity converter wired into CLI | ✅ Closed |
| #1027 | Entity detection regression fix | ✅ Closed |
| #1025 | AI engine test configuration | ✅ Closed |
| #1026 | Flaky perf test fix | ✅ Closed |
| #1020 | Security: token logging fix | ✅ Closed |
| #1019 | Production secrets management | ✅ Closed |
| #971 | E2E validation with 20+ real mods | 🟡 Open — 8 mods validated, expanding to 20+ |
| #1010 | AI engine test failures | 🟡 Open — CI blocker |

**Remaining:**
- Expand test library from 8 → 20+ mods
- Resolve #1010 CI test failures

### 🔴 Week 3-4: Conversion Report + 4 P0 Converter Fixes (Due: May 4)

**Status: Not Started — Critical Sprint**

| Issue | Description | Priority | Audit Data |
|-------|-------------|----------|------------|
| #1000 | Model conversion (Java → Bedrock geometry) | **P0** | 0/4,806 models (0%) |
| #998 | Recipe conversion (data pack → Bedrock format) | **P0** | 0/3,852 recipes (0%) |
| #1001 | BlockEntity classification | **P0** | Most entities misclassified as mobs |
| #1004 | Per-mod conversion report | **P0** | Depends on #1000, #998 |
| #1003 | Full entity behaviors/spawn/loot/animation | P1 | 15 entity defs generated |
| #1002 | Sound & localization extraction | P1 | 0/187 sounds, 0/292 lang files |

**Expected impact:** Models + recipes would bring coverage from ~25% to ~55-65%.

### ⏳ Week 5-6: Infrastructure — Billing, Security, Metering (Due: May 18)

| Issue | Description |
|-------|-------------|
| #970 | Stripe subscription billing (B2B hybrid pricing) |
| #977 | Usage limits and metering per tier |
| #972 | Feature flags for accounts and API keys |
| #973 | File upload security (sandboxing, validation) |
| #976 | Transactional email (verification, notifications) |
| #980 | OAuth login (Discord, GitHub, Google) |

### ⏳ Week 7: Landing Page + Legal + Marketplace Positioning (Due: May 25)

| Issue | Description |
|-------|-------------|
| #978 | Marketing landing page — conversion accelerator positioning |
| #975 | Terms of Service and Privacy Policy |
| — | Marketplace creator outreach materials |
| — | Conversion demo videos (Iron Chests, Farmer's Delight) |

### ⏳ Week 8: Beta Launch — Marketplace Creator Outreach (Due: Jun 1)

- Target: 20-30 Marketplace creators for beta testing
- Channels: r/feedthebeast, Fabric/Forge Discord, direct outreach
- Beta pricing: free tier with premium conversion features

### ⏳ Week 9-11: Beta Feedback + Public Launch (Due: Jun 22)

- Iterate on beta feedback
- Fix top conversion gaps
- Public launch at modporter.ai

---

## Open GitHub Issues (Active)

### P0 — Critical Path
- [#1000](https://github.com/anchapin/ModPorter-AI/issues/1000) Model conversion (4,806 models at 0%)
- [#998](https://github.com/anchapin/ModPorter-AI/issues/998) Recipe conversion (3,852 recipes at 0%)
- [#1001](https://github.com/anchapin/ModPorter-AI/issues/1001) BlockEntity classification
- [#1004](https://github.com/anchapin/ModPorter-AI/issues/1004) Conversion report
- [#971](https://github.com/anchapin/ModPorter-AI/issues/971) E2E validation with 20+ mods

### P1 — Important
- [#1003](https://github.com/anchapin/ModPorter-AI/issues/1003) Full entity conversion
- [#1002](https://github.com/anchapin/ModPorter-AI/issues/1002) Sound & localization
- [#978](https://github.com/anchapin/ModPorter-AI/issues/978) Landing page
- [#970](https://github.com/anchapin/ModPorter-AI/issues/970) Stripe billing

### AI Engine Enhancement (Future)
- [#997](https://github.com/anchapin/ModPorter-AI/issues/997) Fine-tune code LLM
- [#996](https://github.com/anchapin/ModPorter-AI/issues/996) Diffusion LoRA for textures
- [#994](https://github.com/anchapin/ModPorter-AI/issues/994) Upgrade embedding model
- [#993](https://github.com/anchapin/ModPorter-AI/issues/993) Strategy selector
- [#992](https://github.com/anchapin/ModPorter-AI/issues/992) RAG pipeline
- [#991](https://github.com/anchapin/ModPorter-AI/issues/991) LLM-powered agent tools
- [#990](https://github.com/anchapin/ModPorter-AI/issues/990) LLM code translation
- [#989](https://github.com/anchapin/ModPorter-AI/issues/989) Prompt-based RL

---

## Risks

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Model converter complexity | 🟡 MEDIUM | Java models use custom format; may need per-mod-loader handling |
| Recipe format divergence | 🟡 MEDIUM | Forge vs Fabric recipe systems differ; need both parsers |
| Timeline compression (Week 3-4) | 🟡 MEDIUM | 7 issues in 2 weeks; model + recipe can be parallelized |
| Beta recruitment | 🟡 MEDIUM | Community engagement in progress; 8-week ramp |
| Complex mod types (tech/magic) | 🟡 MEDIUM | Out of scope for MVP; focus on content mods first |

---

## Audit Reports

- [v1 — Apr 8, 2026](docs/audit-reports/real-world-scan-20260408.md) — Baseline: 8/8 pass, 1-19% coverage
- [v2 — Apr 9, 2026](docs/audit-reports/real-world-scan-v2-20260409.md) — Texture fix: 54.8% coverage
- [v3 — Apr 10, 2026](docs/audit-reports/real-world-scan-v3-20260410.md) — Entity fix: 15 entity defs, textures stable

---

*Previous roadmap (Feb 2025) archived. This version reflects the B2B pivot and real-world audit data.*
