# MDE-001 — reproducible photovoltaic screening

Original software Apache-2.0; JARVIS data CC BY4.0, NIST JARVIS / Kamal Choudhary et al., DOI10.6084/m9.figshare.6815699.v11. Normalization and computed analysis are modifications.

Configuration: 
```json
{
  "gap_min": 0.8,
  "gap_max": 2.2,
  "target_gap": 1.5,
  "hull_max": 0.1,
  "slme_min": 10,
  "exclude_elements": [],
  "require_dielectric": false
}
```

All records of the fixed2025-09-24 official bulk snapshot, not an outcome-selected sample. Validated composition/crystal identity; missing and nonfinite values remain missing, not zero. Zero gap/hull/SLME values are retained. Polymorphs remain separate JIDs.

Primary bandgap is TB-mBJ. optB88vdW gaps are distributed separately, never pooled. Hull and formation energy are separate optB88vdW descriptors; hull threshold is exploratory. StageA: gap/composition/optional dielectric filters, order by distance to configured target1.5eV. The target is the midpoint of the initial interval, not an asserted optimum. StageB: known hull below threshold, order by hull then gap distance. StageC: additionally reported SLME above threshold, order by SLME descending, hull then gap distance. JID breaks ties. No composite probability score.

Sensitivity compares three windows0.8–2.2,1.0–2.0,1.2–1.8eV and four hull thresholds0,0.05,0.1,0.2eV/atom. Coverage and top-ten Jaccard use explicit denominators. Missingness and eligibility changes differ from ranking-order changes. Correlations use paired complete cases; no causal interpretation.

Reported SLME is theoretical, not experimental efficiency. Per-record thickness/temperature are absent; no uniform-condition or independent optical validation claim. The snapshot contains dielectric diagonals, not full absorption spectra. No DFT simulation, synthesis or device experiment was performed.

Reproduce: run `python -m materials.cli run --data .local/materials` with the pinned source. Keep full cached response for `verify`; public normalized replay separately checks the analysis without network. See REPRODUCIBILITY.md.
