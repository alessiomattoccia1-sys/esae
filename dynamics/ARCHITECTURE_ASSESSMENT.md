# Dynamics Lab — assessment

Creator: Codex per Alessio, 6 November 2026. PROJECT/EVIDENCE; retain until explicit retirement.

Actual baseline: existing repository `esae`, commit `678d340dcf83990f3c3c29deffcf32561e344f6e`. Five implemented Research Engines, published source85. Baseline suite: 246 passed, zero failures/errors/skips, two existing dependency warnings. Before development, 85 runtime/API/UI/shared files were SHA-256 frozen. Existing local histories remain excluded from public distribution.

The site is the established React/esbuild static site, with IT/EN/DE, light/dark and isolated qualified overlays. Current builder is `site-integration/fusion-20261106/build.mjs`; general builds contain unrelated unqualified work. Static deployment uses the installed Mini-to-VPS TCP2223 client and fresh-baseline SHA allowlists. No backend exposure or service restart is needed.

Shared implemented services: bounded official-source PublicCache, separate SQLite JobStore, OperationLock, loopback Host/Origin/CSP boundary, optional local Ollama hypothesis helper and base dashboard CSS. Domain algorithms remain in their current modules. Existing exact Python3.12/macOS arm64 dependency lock already supplies NumPy, SciPy, Pandas, NetworkX, Parquet, FastAPI and plotting. Development reuses that environment read-only; no dependency upgrades are required.

Dynamics Lab is a separate conceptual family, not Research Engine06. Original generic mathematical and simulation cores live under `dynamics`, with the civil-flight application as their first client. It has separate jobs, datasets, reports, numbering, master page and engine page. No clone or replacement repository is created.

Real-data acquisition is being assessed from official Zenodo/Dryad metadata before selecting a bounded subset. IDF_DS declares CC BY4.0, two archives totaling about2.7GB; Dryad declares CC0 and version430761. Actual fields, units and sample sizes will be verified before parser implementation or experimental-result claims. No whole-archive MD5 verification will be claimed for range-selected ZIP members.
