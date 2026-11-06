# FPE-001 — scientific methodology

Real experimental retrospective data. Configuration:

```json
{
  "shot_count": 5,
  "window_seconds": [
    0.05,
    0.35
  ]
}
```

Catalog categories M9/Conventional/Lower Single Null/700kA are matched before viewing signal values; nearest shot IDs to documented30421 define order. All candidate exclusions are retained. Level2 magnetics source ingested_at and commit_url are retained. Time coordinates must be monotonic and finite; no interpolation or sorting repairs. Pint converts explicitly stated units. Quality checks report finite samples, gaps, duplicates, jitter, constant values and apparent extreme plateaus without asserting saturation.

Temporal statistics use finite selected samples. Spectra use the longest contiguous regular valid segment. Welch uses periodic Hann, constant detrend,50percent overlap, window largest power of2 not exceeding segment/4, capped4096. Half/double windows are reported. FFT amplitudes use Hann coherent-gain normalization; STFT has no padding or boundary extension. Frequency-bin half width is grid resolution, not total uncertainty.

Derivative events use retrospective median/MAD thresholds4/6/8 and5ms peak separation; no physical event names are assigned. Savitzky-Golay degree3 windows11/21/41 are all retained, not selected to maximize an outcome. Moving-block percentile intervals for the mean use499replicates,seed20261106,block approximatelysqrt(N), conditional on representative dependence/stability; unknown calibration error is not included. Same-shot coarse/fast comparisons use declared cell means and descriptive correlation; boxcar attenuation does not prove alias freedom and no IID p-values are used. Cross-shot dispersion is observational, not causal or phase-aligned.

Observed data, derived quantities, statistical descriptions and unverified hypotheses remain distinct. Source licenses and modifications are documented separately from original-code Apache2.0.
