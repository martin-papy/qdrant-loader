# Documentation Progress
Totals by status are computed from `docs/_inventory.csv`.
## Status Totals
```bash
awk -F, 'NR>1{c[$5]++} END{for (s in c) printf "%s,%d\n", s, c[s]}' docs/_inventory.csv | sort
```
## Blockers
- None yet.
## Active PRs
- None yet.
Last Updated: $(date +%F)
Maintainer: Martin Papy
