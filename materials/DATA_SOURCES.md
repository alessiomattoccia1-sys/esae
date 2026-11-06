# Data sources and terms

## NIST JARVIS-DFT — operational

- Official database documentation: https://pages.nist.gov/jarvis/databases/
- Official JARVIS: https://jarvis.nist.gov/
- Versioned metadata: https://api.figshare.com/v2/articles/6815699/versions/11
- Dataset DOI: https://doi.org/10.6084/m9.figshare.6815699.v11
- Snapshot: `jdft_3d-9-24-2025.json.zip`, file64391379; snapshot date2025-09-24, Figshare publication2026-05-09.
- Download: https://ndownloader.figshare.com/files/64391379
- Compressed48,447,610bytes; officialMD5 `c3179161ef0d029cf1fa70da463aac6e`; wholeSHA256 `f9e0a3309f0000d5de1ec9e49c93963109ea45e63f451103f8f6595d2eabf7f5`.
- Figshare metadata explicitly assigns **Creative Commons Attribution4.0**: https://creativecommons.org/licenses/by/4.0/ . Attribution: NIST JARVIS-DFT / Kamal Choudhary et al. No NIST endorsement.
- Published normalized dataset changes: property whitelisting, unit/formula normalization, missingness handling, crystal descriptors, filtering/statistical analysis. Full raw archive, atom coordinates and source HTML are not redistributed in the release. Those remain locally hash-verified.

The current `jarvis-tools` official download map points to an older2022 dft_3d snapshot. MDE deliberately pins the newer officially published Figshare version/file rather than silently mixing them. Latest dataset version and snapshot filename date are different metadata fields.

## Schema and units actually checked

`mbj_bandgap` TB-mBJ/eV; `optb88vdw_bandgap` optB88vdW/eV; `ehull` energy above hull/eV per atom; `formation_energy_peratom`/eV per atom; `slme` reported theoretical%; `epsx/y/z` and `mepsx/y/z` dimensionless dielectric diagonals; latticeÅ. Source geometry method `func=OptB88vdW` for all93,902records. Optical spectra are not in this bulk file. Per-record SLME thickness/temperature are not encoded.

The source has unquoted NaN constants inside some nested arrays; the bounded decoder follows Python JSON compatibility while converting NaN/Infinity to missing. It never replaces missing data with zero. Original bytes/hashes remain unchanged.

## Separate detail-page check

Three NIST pages acquired under `https://www.ctcms.nist.gov/~knc6/jsmol/JVASP-ID.html`. JID, formula equivalence, MBJgap and SLME were compared. JVASP-12913:bulk33.98% vs page33.08%; JVASP-3951:33.97% vs33.34%; JVASP-8125:33.97% vs33.97%. Gap differences are below0.001eV; the formula `Sb(IF3)2` is compositionally equivalent to `SbI2F6`.

Pages state500nm/300K, but their release version is unspecified; current solar-tool defaults differ. The available metadata cannot establish the reason for SLME disagreement or optical-condition equivalence. Source URLs, response hashes/dates and all discrepancies are preserved. This is a same-provider rendering check, **not an independent second database validation**. Published ranking remains bound to the fixed bulk snapshot.

## Optional / future

Materials Project: https://docs.materialsproject.org/ . NoAPIkey configured; connector not implemented or tested. No request, credential or cross-database claim. Additional database registry entries are future capabilities. Original software Apache2.0 does not relicense scientific data or publications.
