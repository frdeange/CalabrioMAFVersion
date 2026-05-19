## Summary

Describe what changed and why.

## Checklist

- [ ] Linked issue (`Closes #N` or `Refs #N`)
- [ ] Conventional Commit title (`feat:`, `fix:`, `chore:`, `docs:`, `test:`, `refactor:`, `ci:`, `perf:`)
- [ ] Tests added or updated (mark N/A only with justification)
- [ ] Coverage ≥80% maintained
- [ ] OTel spans added if touching agent/MCP/middleware code
- [ ] Security review requested (`squad:oracle`) if touching paths owned by Oracle (PII/PromptShields/HMAC/SQL pre-val/APIM policies/KV/MI/RBAC)
- [ ] Documentation updated (README, decisions inbox, history.md, threat model if applicable)
- [ ] No secrets in code or `.env` files (KV refs / OIDC only)
- [ ] GHA actions pinned to SHA (not `@v1`)
- [ ] No clickops — all config in code

> [!IMPORTANT]
> Reviewer Lockout Reminder (Decision #5 in `.squad/decisions.md`): if this PR is rejected, a different agent must revise it.

