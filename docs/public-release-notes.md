# Public release notes (maintainers)

Use this checklist before pushing the repo to **public** students or GitHub.

## Safe to publish

- **Synthetic data only** — fixtures use fake account `123456789012`, demo tenant UUID, fictional resource names.
- **Demo passwords** — `demo`/`student`/`changeme`/`neo4j` are intentional local-lab credentials (documented, not production secrets).
- **Vendored subset** — `vendor/` contains only trust-graph models + combo engine needed for the lab (no full platform-contracts tree, no AWS onboarding, no infra/terraform).

## Do not commit

- `.env`, real API keys, cloud credentials
- `.venv/`, `node_modules/`, `.pytest_cache/` (listed in `.gitignore`)
- Private customer data or real inventory exports

## Naming & references

- **No competitor product names** in user-facing copy (removed from UI/docs).
- **Netraom** appears as product/education branding and schema ids (`schemas.netraom.io` in vendored JSON) — acceptable if your org approves public schema namespace.
- **Internal repo URLs** and SSM/infra catalog details removed from student docs; see `portal-integration.md` (conceptual only).

## Optional before push

```bash
# Confirm no Wiz/Orca (should be empty):
rg -i 'wiz|orca' --glob '!package-lock.json'

# Confirm no .env tracked:
git status --ignored
```

## License

Ensure root `LICENSE` (or org policy) matches how students may use vendored code. Vendored packages were copied from internal repos — confirm legal/PM approval for public redistribution.
