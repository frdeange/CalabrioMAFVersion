# 2026-05-19T13:38:00Z — Rename default branch `master` → `main`

**By:** Switch (for Kiko de Ángel)

## What changed
- Default branch renamed atomically from `master` to `main` via GitHub API.
- Open PRs were auto-retargeted by GitHub where applicable (notably PR #10 to `main`).
- PR #1 (`squad/0-devops-foundations`) was updated and force-pushed to remove hardcoded `master` references in governance artifacts.

## Why
- Modernization and alignment with GitHub's post-2020 default branch convention (`main`).
- Reduce future friction across tools and templates that assume `main`.

## Impact
- PR #1 now carries `main` references in workflow filters and branch-protection JSON filename.
- PR #10 base now points to `main` after GitHub auto-retargeting.
- Branch protection transferred to `main` during rename, including signed-commit enforcement.
- GitHub redirect behavior for legacy `master` refs remains active per platform policy (~6 months), but should not be relied on.

## Future
- All new branches should be created from `main` (or `develop` per GitFlow policy when applicable).
- All new workflow branch filters should reference `main` explicitly (and `develop` where policy requires).
