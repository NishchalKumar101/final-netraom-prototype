# Vendored dependencies

The demo API uses a **minimal vendored copy** of shared trust-graph libraries so students need only this repo + Docker.

| Package | What we copied |
|---------|----------------|
| `netraom-contracts` | Graph + finding Pydantic models and JSON schemas |
| `netraom-graph-writer` | NetworkX graph loader + T1–T9 pattern engine |

Maintainers: refresh vendored files from your upstream platform repos when patterns change (see copies under `vendor/`).

Students: do not need any other repository.
