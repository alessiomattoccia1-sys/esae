<!-- SPDX-License-Identifier: Apache-2.0 -->

# Official sources and actual schema

| Source | Actual channel | Semantics / limitations |
|---|---|---|
| U.S. Treasury | Historical 1990–2024 CSV plus annual Atom/OData XML for 2025 and 2026 | Par yields in percentage points; all 14 encountered tenors retained, including 1.5-month XML. Unknown tenors stop import. `BC_30YEARDISPLAY` is checked against the canonical 30-year value and not counted as an additional maturity. Missing values remain null. |
| Chicago Fed | Current official `api.data.chicagofed.org/NFCI/nfci-data-series-csv.csv` | Friday reference dates, NFCI, ANFCI, Risk, Credit, Leverage, Nonfinancial_Leverage. Risk/Credit/Leverage are standardized subindices, not additive contributions. Full history can revise. |
| New York Fed | Annual bounded SOFR search JSON | SOFR effective date, percentRate and revisionIndicator. Inception 2018-04-02. Source update/acquisition is not assumed original publication. |
| ECB, second phase | SDMX EXR.D.USD.EUR.SP00.A, CSV | USD per EUR, unit multiplier zero, daily source dates. Tested separately on October 2026; not part of FSIE-001. |

Treasury documentation: https://home.treasury.gov/treasury-daily-interest-rate-xml-feed
and https://home.treasury.gov/interest-rates-data-csv-archive/ .
Actual archive: https://home.treasury.gov/system/files/276/yield-curve-rates-1990-2024.csv .

Chicago documentation: https://www.chicagofed.org/research/data/nfci/current-data
and https://www.chicagofed.org/research/data/nfci/about . The old static media
CSV stopped at April 2026 during this acquisition. The current official page's
public data-provider endpoint identified the newer official CSV. No login,
HTML table scraping or access-control bypass was used. The new source reaches
2026-10-30 with Last-Modified 2026-11-04. Preserve the manifest acquisition vintage.
The normal Wednesday release schedule does not prove exact historical release
availability; historical publication timestamps stay null.

New York API: https://markets.newyorkfed.org/static/docs/markets-api.html .
SOFR: https://www.newyorkfed.org/markets/reference-rates/sofr .
ECB: https://data.ecb.europa.eu/help/api/data-examples .

FRED/ALFRED requires an environment API key and remains unimplemented. The
status registry reports only whether a key is configured, never its value.
SEC remains a future connector requiring a declared client/rate policy; it was
not queried and no SEC integration is claimed.

Every actual FSIE-001 response URL, byte hash, size, HTTP status, acquisition time,
source Last-Modified/ETag when supplied, parser version, counts and coverage is
recorded in FSIE-001_MANIFEST.json. Last-Modified is not a guaranteed dataset
release identifier or original historical publication timestamp.
