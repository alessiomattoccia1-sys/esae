# Scientific methodology — MDE-001

All valid unique JARVIS IDs in the fixed3D snapshot are considered; no cherry-picking by result. A material is a JID/crystal record, not a unique chemical formula. Different polymorphs retain separate identities.

Formula composition is parsed with bracket/stoichiometric support, reduced using JARVIS-tools and checked against atom fractions. Lattice3×3, determinant/volume, finite coordinates and atom counts are validated; cartesian coordinates are converted to fractional. Whitelisted physical fields have explicit units and methods. Missing/nonfinite fields remain null. Negative formation energy is valid and is never substituted for hull energy.

Primary electronic method:TB-mBJ. The complete optB88vdW gap distribution is reported separately, never pooled with TB-mBJ. The exploratory interval0.8–2.2eV is not a proof of photovoltaic suitability. Target1.5eV is the interval midpoint chosen for a baseline ordering, not a universal optimum.

Three nested cohorts and **lexicographic**, nonprobabilistic rankings:

1. A:known TB-mBJgap within inclusive0.8–2.2eV. Optional composition/dielectric constraints can further filter. Order by absolute gap distance from1.5eV, then numericJID.
2. B:A plus known `ehull`≤0.1eV/atom. Order by hull, gap distance, numericJID. Formation energy remains a separate reported quantity.
3. C:B plus reportedSLME≥10%. Order by reportedSLME descending, hull, gap distance, numericJID. SLME is theoretical/source-reported, not measured device efficiency. Per-record conditions are unknown.

Missing required data are explicitly excluded at their stage and counted. Percentages identify numerator and denominator; screen percentages use all valid unique materials. Availability uses all valid unique materials; distributions use the named method's finite values; correlations use complete pairs. CSV includes all eligible records in each tier, so the same JID can appear in multiple tiers; rows across tiers must not be summed as unique materials. Dashboard/report display the first100/20per tier and say so.

Sensitivity:three gap windows[0.8,2.2],[1,2],[1.2,1.8] × four hull maxima0,0.05,0.1,0.2eV/atom. SLME≥10% and any configured composition filters are retained. Report cohort counts, top10Jaccard(overlap/union) and intersection across all12cohorts. Distinguish eligibility from ordering: B and C have identical membership in this particular study although their ordering differs.

Descriptive statistics:NumPy histogram bins[0,.8,1.2,1.6,2.2,3,5,10,∞), lastbininclusive; medians by method/chemical-family with availableN; SciPy Pearson/Spearman on complete finite pairs; constants or fewer than3pairs yield NOT DETERMINABLE. Tukey1.5IQRflags are descriptive, not invalid-material decisions. No causal inference, calibrated probability or population-frequency claim.

Six leading candidates are checked against the original archive and independent JARVIS-library geometry/composition calculations. Three are checked against separately retrieved official HTML. Two SLME disagreements remain unresolved and visible. No outside database or physical measurement validates the ranking. Numeric results never use an LLM.

Evidence labels:OBSERVED DATA from source; COMPUTED RESULT from this reproducible code; AI HYPOTHESIS optional referenced local prose; NOT VERIFIED for optical conditions, experimental efficiency and hypotheses. No synthesis, DFT calculation, new-material discovery or experimental efficiency is claimed.
