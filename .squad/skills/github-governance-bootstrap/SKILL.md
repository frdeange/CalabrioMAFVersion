# GitHub Governance Bootstrap Pattern

## When to use

Use this pattern when initializing repository governance before feature delivery starts.

## Steps

1. Resolve repo owner/default branch with `gh repo view --json owner,defaultBranchRef`.
2. Ensure GitFlow integration branch exists (`develop`), create from default branch if missing.
3. Materialize issue/PR templates + CODEOWNERS in `.github/`.
4. Sync labels idempotently using a script and `gh label create --force`.
5. Commit branch-protection payload JSON to repo, then apply with `gh api -X PUT`.
6. Apply required signatures using `gh api -X POST .../required_signatures`.
7. Wire CI job names first (can be placeholders), then lock branch checks to those job names.
8. Enable secret scanning and push protection via `gh api -X PATCH`.
9. Record outcomes and limitations in `.squad/decisions/inbox/` and agent history.

## Why this works

- Reproducible: all policy state is in code + scripts.
- Idempotent: reruns converge to desired state.
- Safe: branch protections and scanning are enforced before broad PR activity.

## Default Branch Rename

Use GitHub's atomic branch-rename API so redirects, default-branch change, PR retargeting, and protection migration are handled server-side in one operation:

```bash
gh api -X POST /repos/{owner}/{repo}/branches/{old}/rename -f new_name={new}
```

Then verify with:

1. `gh repo view {owner}/{repo} --json defaultBranchRef`
2. `gh pr list --state open --json number,baseRefName,headRefName`
3. `gh api /repos/{owner}/{repo}/branches/{new}/protection`

## Gotchas after rename

- Workflow branch filters in `.github/workflows/*.yml` (`on.push.branches` / `on.pull_request.branches`)
- `.github/dependabot.yml` `target-branch` values
- Branch-protection config filenames (for example `branch-protection.master.json` → `branch-protection.main.json`)
- CODEOWNERS comments/docs that describe the default branch by name
- Governance scripts/docs that mention `master`

## Confidence

- medium
