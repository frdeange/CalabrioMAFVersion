### 2026-05-19: Switch — PR #1 Copilot Review Round 3 Resolution
**By:** Switch (for Kiko de Ángel)
**When:** 2026-05-19T20:04:40Z–20:04:41Z review window; resolved same day
**What:** Addressed 2 net-new Copilot review comments on PR #1:
- Comment `#3269274901` on `.github/scripts/sync-labels.ps1:60`
- Comment `#3269274936` on `.github/workflows/squad-issue-assign.yml:122`
**Why:** Remove competing label sources of truth and harden squad:copilot assignment behavior when `COPILOT_ASSIGN_TOKEN` is missing.
**Resolution Summary:**
- **Fix A (label ownership split):** Removed `squad` + `squad:*` entries from `.github/scripts/sync-labels.ps1`. PS1 now owns only static project taxonomy (`kind:*`, `area:*`, `phase:*`). Added an explicit NOTE block documenting that `.github/workflows/sync-squad-labels.yml` is authoritative for squad governance labels (`squad`, `squad:*`, `squad:copilot`, `go:*`, `release:*`, `type:*`, `bug`, `feedback`, `priority:*`) sourced dynamically from `.squad/team.md`.
- **Fix B (copilot token guard):** In `.github/workflows/squad-issue-assign.yml`, promoted `COPILOT_ASSIGN_TOKEN` to job-level env; gated the acknowledgment step to skip `squad:copilot` when PAT is missing; guarded `Assign @copilot coding agent` with `env.COPILOT_ASSIGN_TOKEN != ''`, switched token input to env value, and added `continue-on-error: true`; added a dedicated warning step that posts a user-facing remediation comment when PAT is not configured.
**Bootstrap note:** After PR #1 merge, run `Sync Squad Labels` workflow once via `workflow_dispatch` to ensure squad:* labels exist before applying them to issues.
**Status:** Committed on `squad/0-devops-foundations`, pushed, and both Copilot threads replied.
