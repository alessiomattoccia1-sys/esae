# Scientific methodology

The configuration was fixed after schema inspection and before numeric analysis in the preserved preregistration. Selection never uses observed waveform or image outcomes.

FPE-001: M9, Conventional divertor, Lower Single Null, source category 700 kA; order by absolute shot-ID distance from documented shot 30421, then ID; first five accessible matches, bounded candidate attempts. Source-relative window 0.05–0.35 s; actual magnetics/ip and OMV voltage channel zero. Source channel label, dimensions and units are checked. Metadata categories do not prove physically identical conditions.

Quality gates precede spectra. No silent interpolation, sorting, deduplication or missing-to-zero replacement. Spectra use the longest regular finite contiguous segment. Welch uses periodic Hann, constant detrend, 50% overlap; power-of-two window at most segment/4 and capped 4096. Half/double windows are all reported. FFT has coherent-gain amplitude normalization; STFT has no artificial boundary extension or padding. Frequency-grid resolution is not total physical uncertainty. Peak-preserving plot bins and max-pooled spectrogram bins are explicit; exact peak metrics use the full grid.

Derivative candidates use whole-selected-segment median/MAD thresholds 4/6/8 and 5 ms minimum peak separation. They are retrospective, not causal detectors. SG polynomial-three windows 11/21/41 are all retained. Mean intervals use 499 moving-block replicates, seed 20261106, block approximately sqrt(N), conditional on representative local dependence. Cross-shot differences remain descriptive. Same-shot IP/voltage comparisons use declared fast-signal cell means, Pearson/Spearman and all listed lags, without IID p-values or causal interpretation.

FPE-002: fixed seven raw HDF filename matches; original uint16 arrays; outer 10% border backgrounds at quantiles 25/50/75, full and central 80% fixed detector ROIs, all six combinations. Positive residuals define generic detector centroids/profiles in pixels. Ranges quantify preprocessing sensitivity, not confidence or total physical uncertainty. No physical scale or radiometric response is invented.

## Clarifications to preregistration

The preliminary phrase “past-compatible median/MAD” was imprecise: the implemented event statistic uses the whole selected segment and is explicitly retrospective. The preliminary “anti-alias” wording does not justify alias-free comparison: boxcar cell averages can leave aliasing. The final analysis reports this limitation and makes no modal, causal or predictive claim. The preregistration is retained unchanged with these deviations disclosed.


Original software © 2026 Mattoccia Labs, Apache License 2.0. Scientific data and derived artifacts retain the separate source licenses.
