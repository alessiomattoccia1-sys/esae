<!-- SPDX-License-Identifier: Apache-2.0 -->
# FPRE architecture assessment and reuse

Creator: Codex per Alessio / Mattoccia Labs, 6 November 2026. PROJECT/EVIDENCE;
retain until explicit retirement. Existing repository `esae`, commit
`d58ec30f82ec2622b6e3cbe44233664fc271bac9`; no clone or replacement repository.

Actual implemented engines: ESAE0.1.1, GEE0.1.0, MDE0.1.0, FSIE0.1.0.
Their Python/API/UI/shared runtime hashes are frozen before development (68 files).
The existing test suite is executed before adding FPRE; results are recorded in
the assessment evidence rather than assumed. The initial run passed all 209 tests. Separate `.venv-fpre` and fusion
archive preserve all earlier environments and databases.

| Component | Classification | Intervention |
|---|---|---|
| Existing bounded sandbox runner | Direct reuse; one demonstrated exit-race fix | Read only selected HDF; deny network, CPU/time/output limits; emit row chunks below existing per-file limit |
| Shared PublicCache | Direct reuse with injected policy | Official FAIR-MAST/STFC URLs, bounded responses, immutable raw bytes; content-addressed snapshots per study |
| JobStore / OperationLock | Direct reuse | Separate fusion SQLite registry, explicit resume/cancel and per-lab runs |
| Local API boundary | Direct reuse | Loopback Host/Origin/mutation protections and strict CSP |
| Local AI hypothesis helper | Adaptable | Selected measured/derived/statistical findings; no numeric claims or apparatus access |
| Existing CSS/DOM/SVG dashboard | Adaptable | Same original styles, two laboratory entries and eight real-data areas |
| Report/export patterns | Adaptable | Two independent scientific reports, provenance and exact replay; source-specific data licenses |
| FSIE tabular statistics | Domain-specific, not appropriate to share | No financial regimes or lag inference reused as plasma physics |
| Genomics and materials algorithms | Domain-specific | Preserve unchanged; no physics equivalence inferred |
| Fusion registry / units / coordinates | New | Explicit experiments, shots, diagnostics, measurements and findings |
| Magnetic signal algorithms | New specialist module | Quality gates, temporal/spectral processing, candidate events and cross-shot comparison |
| Inertial image characterization | New specialist module | Generic diagnostic array quality, pixel-domain centroids/profiles and preprocessing sensitivity |
| Statistical/physical validation | New shared fusion module | Dimensional checks, uncertainty labels, analytical controls; no parameters invented |
| Website | Existing React/esbuild overlay | Reproduce source84 first; add FUSION/master/latest, preserve all four page bodies |

## Scientific separation

MCF and ICF keep independent algorithms. MAST equilibrium reconstructions are
not labeled direct observations. The specified STFC archive concerns implosion
experiments: the implemented scope is diagnostic inventory and generic image
quality/measurement robustness. No optimization of shock timing, laser drive,
target/implosion geometry, ignition or yield is implemented or inferred. No
operating configurations are joined to performance outcomes. Uncalibrated image
measurements remain in pixels and instrument units, with calibration uncertainty
explicitly unknown. Public datasets are never treated as code to execute.

## Data access and publication

UKAEA describes anonymous S3 Zarr and JSON catalog access, with CC BY-SA4.0
unless exceptions apply; STFC item declares CC BY4.0. Actual per-source metadata
and access must be checked before import and redistribution. Catalog timeouts
will be recorded; only documented official alternatives may be used. No ACL,
authentication or network protections will be bypassed. Full raw archives remain
local; public original software is Apache2.0, scientific derivatives carry the
appropriate separate source license/attribution. No new public backend, persistent
service, firewall, mail, Appunti or ATENA changes.
