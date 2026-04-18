# PortKit (ModPorter-AI) — Development Roadmap

**Last Updated:** 2026-04-17 (v8 audit)
**Status:** M2 Complete + M3 Infrastructure underway
**Repo:** [anchapin/ModPorter-AI](https://github.com/anchapin/ModPorter-AI) | Rebrand to PortKit pending ([#1043](https://github.com/anchapin/ModPorter-AI/issues/1043))
**Target:** Public launch at modporter.ai by June 22, 2026

---

## Executive Summary

PortKit converts Minecraft Java mods to Bedrock add-ons. Positioned as a **B2B conversion accelerator** targeting Marketplace creators.

**Current pipeline maturity: ~63% weighted B2B coverage** (v8 audit, Apr 17 — canonical 8 mods, HEAD `35f52cf`).  
**M2 target (60%) exceeded.** Stripe billing shipped. M3 infrastructure underway.  
**Known gap:** Custom recipe type fix (#1079) has a bug — cooking_pot recipes silently discarded. Fix pending.

---

## Conversion Audit History

| Cycle | Date | Mods | Textures | Models | Recipes | Sound | Lang | B2B est. | Key Changes |
|-------|------|------|----------|--------|---------|-------|------|-----------|-------------|
| v1 | Apr 8 | 8 | ~0% | 0% | 0% | 0% | 0% | ~5% | Baseline |
| v2 | Apr 9 | 8 | 54.8% | 0.2% | 0% | 0% | 0% | ~25% | Bulk texture extraction |
| v3 | Apr 10a | 8 | 54.7% | 0% | 0% | 0% | 0% | ~28% | Entity routing fix |
| v4 | Apr 10b | 8 | 54.7% | 0% | 0% | 0% | 0% | ~28% | Agents built, not yet wired |
| v5 | Apr 11 | 8 | 54.7% | 82.3% | 25.8% | 0% | 0% | ~46% | Model+recipe converters wired |
| v6 | Apr 15 | 30 | 68.7% | 68.3% | 40.2% | 0% | 0% | ~49% | NeoForge fix, 30-mod set |
| v7 | Apr 16 | 8 | 54.7% | 82.3% | 25.8% | ~100% | 89.3% | ~63% 🎯 | Sound+lang, loot tables, spawn rules, report enhancements |
| **v8** | **Apr 17** | **8** | **54.7%** | **82.3%** | **25.9%** | **~100%** | **89.3%** | **~63%** | **Stripe (#1081), Error handling (#1080), Custom recipe types (#1079 — bug)** |

**v8 B2B readiness: 63.2%** — unchanged from v7. Stripe and error handling don't affect pipeline metrics. Custom recipe type fix (#1079) was merged but has a bug causing cooking_pot/cutting_board recipes to be silently discarded (ingredient/ingredients field name mismatch). Expected +5-8% B2B not yet realized.

**v8 B2B breakdown:**
| Asset Type | Coverage | Weight | Contribution |
|------------|----------|--------|-------------|
| Texture | 54.7% | 25% | 13.7% |
| Model | 82.3% | 30% | 24.7% |
| Recipe | 25.9% | 20% | 5.2% |
| Sound | ~100% | 10% | 10.0% |
| Localization | 89.3% | 10% | 8.9% |
| Entity | ~15% | 5% | 0.8% |
| **Total** | | | **63.2%** |

---

## 11-Week Launch Roadmap

### ✅ M1 — Weeks 1-2: Conversion Proof + Pipeline (Complete Apr 10)
All M1 converters wired. Models 82.3%, recipes 25.8% (canonical).

### ✅ M2 — Weeks 3-4: Entity Behaviors + Sound/Lang + B2B UX (Complete Apr 16 — 3 weeks early)

| Issue | Status |
|-------|--------|
| #971 E2E validation (20+ mods) | ✅ Closed Apr 15 |
| #1003 Entity behaviors (spawn rules, loot tables) | ✅ Closed by #1074 |
| #1002 Sound + localization | ⚠️ Still open (PR #1075 merged but not auto-closed) |
| #1067 Conversion Report handoff (B2B UX) | ✅ Closed by #1076 |
| #1066 Production secrets hardening | ✅ Closed by #1072 |
| #1068 Error handling & user-visible feedback | ✅ Closed by #1080 |
| #1078 Custom Forge recipe types | ✅ Closed by #1079 (PR merged, **but buggy** — cooking_pot recipes silently discarded) |

### 🔄 M3 — Weeks 5-6: Infrastructure (Due: May 18)

| Issue | Status | Priority |
|-------|--------|----------|
| [#970](https://github.com/anchapin/ModPorter-AI/issues/970) Stripe subscription billing | ⚠️ Still open (PR #1081 merged, not auto-closed) | ✅ Done |
| **Custom recipe types bugfix** (see #1079 regression) | 🆕 **File new issue — P0** | P0 |
| [#973](https://github.com/anchapin/ModPorter-AI/issues/973) File upload security | Open | P1 — beta blocker |
| [#972](https://github.com/anchapin/ModPorter-AI/issues/972) Feature flags | Open | P1 — needed for Stripe tiers |
| [#977](https://github.com/anchapin/ModPorter-AI/issues/977) Usage limits + metering | Open | P1 |
| [#976](https://github.com/anchapin/ModPorter-AI/issues/976) Transactional email | Open | P2 |
| [#980](https://github.com/anchapin/ModPorter-AI/issues/980) OAuth login | Open | P2 |

### ⏳ M4 — Week 7: Landing Page + Legal + Rebrand (Due: May 25)

| Issue | Description |
|-------|-------------|
| [#978](https://github.com/anchapin/ModPorter-AI/issues/978) | Marketing landing page |
| [#975](https://github.com/anchapin/ModPorter-AI/issues/975) | Terms of Service and Privacy Policy |
| [#979](https://github.com/anchapin/ModPorter-AI/issues/979) | Conversion history dashboard |
| [#1043](https://github.com/anchapin/ModPorter-AI/issues/1043) | Rebrand to PortKit |

### ⏳ M5 — Week 8: Beta Launch (Due: Jun 1)
Target: 20–30 Marketplace creators. Demo mods: Waystones (98% model/88% recipe), Farmer's Delight (88% model/98% lang), Supplementaries (95% model/101% sounds).

### ⏳ M6-M7 — Weeks 9-11: Beta Feedback + Public Launch (Due: Jun 22)

---

## Top 3 Priority Issues (Apr 17 — post-v8)

### 🥇 #1: Custom Recipe Types Bugfix — File New Issue (P0)

**#1079 was merged but the fix is broken.** Root cause: In `_parse_java_recipe`, the `farmersdelight:cooking` branch reads `recipe_data.get("ingredient")` (singular), but actual Farmer's Delight cooking recipes use `"ingredients"` (plural array). Result: `normalized["ingredients"]` stays empty → `_convert_cooking_pot_to_bedrock` returns a `manual_review_result` dict (no `"minecraft:recipe_"` key, no top-level `"identifier"`) → silently discarded in `block_item_generator.py`. 183 Farmer's Delight cooking recipes and many more converted to 0 output.

**Fix:** In `_parse_java_recipe` for `farmersdelight:cooking`: add fallback `recipe_data.get("ingredients", [])`. Similarly verify `farmersdelight:cutting` ingredients extraction. Expected impact once fixed: **Recipe 25.9% → 50%+, B2B ~63% → ~68%**.

### 🥈 #2: [#973](https://github.com/anchapin/ModPorter-AI/issues/973) — File Upload Security (P1 — beta blocker)

Executing arbitrary JAR files from untrusted uploads without sandboxing is a critical security risk for a public SaaS. Needed before any beta invites. Covers: sandboxing (Docker/gVisor), size/type validation, virus scanning (ClamAV), path traversal prevention.

### 🥉 #3: [#972](https://github.com/anchapin/ModPorter-AI/issues/972) — Feature Flags (P1)

Stripe integration (#1081) is merged, but without feature flags the tiers can't be enforced. Feature flags are also needed for safe rollout of any future pipeline changes (e.g., once recipe bugfix ships, it can be gated). Prerequisite for: usage limits (#977), OAuth rollout (#980), and any A/B testing during beta.

---

## Open Issues (15 total)

### Immediate (M3)
- 🆕 **Custom recipe types bugfix** — no issue yet, file one **← #1 PRIORITY**
- [#973](https://github.com/anchapin/ModPorter-AI/issues/973) File upload security **← #2 PRIORITY**
- [#972](https://github.com/anchapin/ModPorter-AI/issues/972) Feature flags **← #3 PRIORITY**
- [#977](https://github.com/anchapin/ModPorter-AI/issues/977) Usage limits | [#976](https://github.com/anchapin/ModPorter-AI/issues/976) Transactional email | [#980](https://github.com/anchapin/ModPorter-AI/issues/980) OAuth

### Auto-close needed (PRs merged, issues still open)
- [#970](https://github.com/anchapin/ModPorter-AI/issues/970) — closed by #1081 (Stripe)
- [#1002](https://github.com/anchapin/ModPorter-AI/issues/1002) — closed by #1075 (sound/lang)

### M4 Marketing/Legal
- [#978](https://github.com/anchapin/ModPorter-AI/issues/978) Landing page | [#975](https://github.com/anchapin/ModPorter-AI/issues/975) ToS/Privacy | [#979](https://github.com/anchapin/ModPorter-AI/issues/979) History dashboard | [#1043](https://github.com/anchapin/ModPorter-AI/issues/1043) Rebrand

### Post-Launch / AI
- [#1048](https://github.com/anchapin/ModPorter-AI/issues/1048) IDE plugins | [#994](https://github.com/anchapin/ModPorter-AI/issues/994) Embedding upgrade | [#996](https://github.com/anchapin/ModPorter-AI/issues/996) Diffusion LoRA | [#997](https://github.com/anchapin/ModPorter-AI/issues/997) LLM fine-tune

---

## Audit Reports

- v1–v5: [docs/audit-reports/](docs/audit-reports/)
- [v6 — Apr 15](docs/audit-reports/real-world-scan-v6-20260415.md) — 30 mods, B2B ~49%
- [v7 — Apr 16](docs/audit-reports/real-world-scan-v7-20260416.md) — Sound ~100%, Lang 89.3%, B2B 63.2% ✅
- [**v8 — Apr 17**](docs/audit-reports/real-world-scan-v8-20260417.md) — B2B **63.2%** (flat), Stripe+Error handling shipped, custom recipe types buggy
