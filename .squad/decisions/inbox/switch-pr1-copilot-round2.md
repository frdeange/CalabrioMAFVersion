### 2026-05-19: Switch — PR #1 Copilot Review Round 2 Resolution
**By:** Switch (for Kiko de Ángel)
**What:** Addressed 17 net-new Copilot review comments on PR #1 after the d95fc1d commit. Unified actions/checkout SHA to v6.0.2 across all squad-* workflows, added container-build to required_status_checks, staged .squad/routing.md, applied master→main fixes in non-append-only files, and used "post-write clarification" append pattern for orchestration-log and 6 cross-agent histories (preserving append-only governance per Source of Truth Hierarchy).
**Why:** Maintain factual consistency between code, governance docs, and history while respecting append-only invariants. Supply-chain hygiene: single checkout SHA across the entire repo.
**Status:** Committed to squad/0-devops-foundations, replied to all 17 Copilot threads.
