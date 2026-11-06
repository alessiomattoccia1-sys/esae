# SPDX-License-Identifier: Apache-2.0
"""Retrospective signal characterization; candidates are not named plasma modes."""

import math, hashlib, json
import numpy as np
from scipy import signal, fft, stats
from .physics import normalize_signal

METHOD_VERSION = "fpre-signals-1.0"


def finite(v):
    return None if v is None or not np.isfinite(v) else float(v)


def clean(x):
    if isinstance(x, dict):
        return {str(k): clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple, np.ndarray)):
        return [clean(v) for v in x]
    if isinstance(x, (bool, np.bool_)):
        return bool(x)
    if isinstance(x, (int, np.integer)):
        return int(x)
    if isinstance(x, (float, np.floating)):
        return finite(x)
    return x


def segments(mask):
    changes = np.diff(np.r_[False, mask, False].astype(int))
    return list(zip(np.where(changes == 1)[0], np.where(changes == -1)[0]))


def quality(t, x):
    t = np.asarray(t, float)
    x = np.asarray(x, float)
    if t.ndim != 1 or x.shape != t.shape or len(t) > 2_000_000 or len(t) < 3:
        raise ValueError("Bounded 1D matching coordinates required")
    dt = np.diff(t)
    valid = np.isfinite(t) & np.isfinite(x)
    positive = dt[np.isfinite(dt) & (dt > 0)]
    median = float(np.median(positive)) if len(positive) else float("nan")
    blocks = segments(valid)
    jump = np.zeros(len(t), bool)
    jump[1:] = ~np.isfinite(dt) | (dt <= 0) | (dt > 1.5 * median)
    runs = []
    for a, b in blocks:
        boundaries = [a] + [i for i in range(a + 1, b) if jump[i]] + [b]
        runs.extend((s, e) for s, e in zip(boundaries[:-1], boundaries[1:]) if e > s)
    lo, hi = max(runs, key=lambda r: r[1] - r[0]) if runs else (0, 0)
    jitter = (
        float(np.max(np.abs(dt - median)) / median)
        if median > 0 and np.isfinite(dt).all()
        else float("inf")
    )
    y = x[valid]
    degenerate = not len(y) or np.ptp(y) == 0
    return clean(
        {
            "samples": len(t),
            "valid_samples": int(valid.sum()),
            "missing_samples": int((~valid).sum()),
            "missing_fraction": 1 - valid.mean(),
            "time_start_s": t[0],
            "time_end_s": t[-1],
            "duration_s": t[-1] - t[0],
            "duplicate_timestamps": int((dt == 0).sum()),
            "nonmonotonic_steps": int((dt < 0).sum()),
            "time_nonfinite": int((~np.isfinite(t)).sum()),
            "median_step_s": median,
            "sample_rate_hz": 1 / median if median > 0 else None,
            "nyquist_hz": 0.5 / median if median > 0 else None,
            "relative_step_jitter_max": jitter,
            "regular_sampling": bool(jitter <= 1e-5),
            "gaps": int((dt > 1.5 * median).sum()),
            "constant_or_degenerate": degenerate,
            "longest_valid_segment": [int(lo), int(hi)],
            "valid_segments": len(runs),
            "apparent_extreme_plateau_fraction": (
                float(max(np.mean(y == y.min()), np.mean(y == y.max())))
                if len(y)
                else None
            ),
            "saturation_status": "Not determined without sensor limits; repeated extrema are only a quality flag",
            "scale_status": "No verified instrument full-scale bounds supplied",
            "preprocessing": "No sorting, interpolation, deduplication, missing-to-zero substitution or source mutation",
        }
    )


def describe(x):
    y = np.asarray(x, float)
    y = y[np.isfinite(y)]
    return (
        clean(
            {
                "n": len(y),
                "mean": np.mean(y),
                "std_sample": np.std(y, ddof=1),
                "rms": np.sqrt(np.mean(y * y)),
                "minimum": np.min(y),
                "maximum": np.max(y),
                "p05": np.quantile(y, 0.05),
                "p95": np.quantile(y, 0.95),
            }
        )
        if len(y)
        else {"n": 0}
    )


def spectra(t, x, nperseg=None):
    q = quality(t, x)
    if (
        not q["regular_sampling"]
        or q["constant_or_degenerate"]
        or q["missing_samples"]
        or q["nonmonotonic_steps"]
    ):
        return {
            "status": "inconclusive",
            "reason": "FFT/Welch/STFT require a regular, finite, nondegenerate selected segment",
            "quality": q,
        }
    n = len(x)
    fs = q["sample_rate_hz"]
    window = (
        min(4096, 2 ** int(np.floor(np.log2(n / 4))))
        if nperseg is None
        else int(nperseg)
    )
    if n < 256 or not 16 <= window <= min(n, 8192):
        return {
            "status": "inconclusive",
            "reason": "Insufficient spectral samples/window",
        }
    frequency, power = signal.welch(
        x,
        fs=fs,
        window="hann",
        nperseg=window,
        noverlap=window // 2,
        nfft=window,
        detrend="constant",
        scaling="density",
    )
    nonzero = power[1:]
    peak = int(np.argmax(nonzero) + 1)
    hann = signal.windows.hann(n, sym=False)
    amplitude = np.abs(fft.rfft((x - np.mean(x)) * hann)) * 2 / hann.sum()
    amplitude[0] /= 2
    if n % 2 == 0:
        amplitude[-1] /= 2
    f_fft = fft.rfftfreq(n, 1 / fs)
    ff, tt, z = signal.stft(
        x,
        fs=fs,
        window="hann",
        nperseg=window,
        noverlap=window // 2,
        nfft=window,
        detrend="constant",
        boundary=None,
        padded=False,
    )
    f_stride = max(1, math.ceil(len(ff) / 128))
    t_stride = max(1, math.ceil(len(tt) / 96))
    sensitivity = []
    for alt in sorted({max(16, window // 2), window, min(8192, window * 2, n)}):
        f, p = signal.welch(
            x,
            fs=fs,
            window="hann",
            nperseg=alt,
            noverlap=alt // 2,
            detrend="constant",
            scaling="density",
        )
        i = int(np.argmax(p[1:]) + 1)
        sensitivity.append(
            {"nperseg": alt, "peak_hz": f[i], "frequency_bin_hz": fs / alt}
        )
    stride = max(1, math.ceil(len(frequency) / 1024))
    fs_stride = max(1, math.ceil(len(f_fft) / 1024))
    keep_psd = [
        i + int(np.argmax(power[i : i + stride])) for i in range(0, len(power), stride)
    ]
    keep_fft = [
        i + int(np.argmax(amplitude[i : i + fs_stride]))
        for i in range(0, len(amplitude), fs_stride)
    ]
    magnitude = np.abs(z)
    dominant_trace = ff[np.argmax(magnitude[1:], axis=0) + 1]
    freq_bins = []
    pooled = []
    for i in range(0, len(ff), f_stride):
        freq_bins.append(float(np.mean(ff[i : i + f_stride])))
        band = np.max(magnitude[i : i + f_stride], axis=0)
        pooled.append(
            [float(np.max(band[j : j + t_stride])) for j in range(0, len(tt), t_stride)]
        )
    time_bins = [
        float(np.mean(tt[j : j + t_stride])) + t[0] for j in range(0, len(tt), t_stride)
    ]
    return clean(
        {
            "status": "computed",
            "method": "SciPy Welch/FFT/STFT; periodic Hann; constant detrend;50percent overlap; no physical mode identification",
            "fs_hz": fs,
            "nyquist_hz": fs / 2,
            "nperseg": window,
            "nfft": window,
            "frequency_bin_hz": fs / window,
            "dominant_non_dc_hz": frequency[peak],
            "dominant_psd": power[peak],
            "frequency_resolution_half_bin_hz": fs / window / 2,
            "uncertainty_kind": "Frequency-grid resolution only; not total frequency measurement uncertainty",
            "integrated_psd": np.trapezoid(power, frequency),
            "input_variance": np.var(x),
            "psd": {
                "frequency_hz": frequency[keep_psd],
                "density": power[keep_psd],
                "display_stride": stride,
                "display_method": "Peak-preserving bins, actual frequency of each retained maximum; full grid used in metrics",
            },
            "fft": {
                "frequency_hz": f_fft[keep_fft],
                "amplitude": amplitude[keep_fft],
                "display_stride": fs_stride,
                "dominant_frequency_hz_full_grid": f_fft[
                    int(np.argmax(amplitude[1:]) + 1)
                ],
                "dominant_amplitude_full_grid": np.max(amplitude[1:]),
            },
            "stft": {
                "time_s": time_bins,
                "frequency_hz": freq_bins,
                "magnitude": pooled,
                "dominant_frequency_hz_full_grid": dominant_trace,
                "full_grid_times_s": tt + t[0],
                "display_frequency_bin_hz": f_stride * fs / window,
                "display_method": "Maximum magnitude pooling within explicit frequency/time bins; bin centers shown, exact peak trace computed on full grid",
                "frequency_display_stride": f_stride,
                "time_display_stride": t_stride,
                "boundary": None,
                "padded": False,
            },
            "window_sensitivity": sensitivity,
            "limits": "A spectral peak is a signal-processing observation, not a confirmed MHD mode or instability. Window sensitivity and transients can shift peaks.",
        }
    )


def events(t, x, threshold=6, separation_s=0.005):
    derivative = np.gradient(x, t, edge_order=2)
    median = float(np.median(derivative))
    mad = float(np.median(np.abs(derivative - median)))
    scale = 1.4826 * mad
    if scale <= 1e-15:
        return [], {
            "status": "inconclusive",
            "reason": "Zero derivative MAD; no infinite-score events invented",
        }
    score = np.abs(derivative - median) / scale
    fs = 1 / np.median(np.diff(t))
    peaks, _ = signal.find_peaks(
        score, height=threshold, distance=max(1, round(separation_s * fs))
    )
    out = []
    mask = score >= threshold
    for i in peaks:
        a = i
        b = i
        while a > 0 and mask[a - 1]:
            a -= 1
        while b < len(x) - 1 and mask[b + 1]:
            b += 1
        out.append(
            {
                "timestamp_s": t[i],
                "start_s": t[a],
                "end_s": t[b],
                "duration_s": t[b] - t[a],
                "amplitude": np.ptp(x[a : b + 1]),
                "peak_derivative": derivative[i],
                "robust_z": score[i],
                "threshold": threshold,
                "method": "Retrospective derivative median/MAD excursion; local peak separation5ms",
                "verification": "candidate_unclassified",
                "time_discretization_half_step_s": 0.5 / fs,
                "boundary_adjacent": bool(a == 0 or b == len(x) - 1),
            }
        )
    return clean(out), {
        "status": "computed",
        "median_derivative": finite(median),
        "mad_scale": finite(scale),
        "threshold": threshold,
        "minimum_separation_s": separation_s,
        "causal_or_predictive": False,
    }


def block_mean_interval(x, seed=20261106, replicates=499):
    # Finite observed segment; explicitly conditional statistical variability.
    x = np.asarray(x)
    block = max(4, min(len(x) // 8, int(np.sqrt(len(x)))))
    nblocks = math.ceil(len(x) / block)
    rng = np.random.default_rng(seed)
    means = []
    for _ in range(replicates):
        starts = rng.integers(0, len(x) - block + 1, nblocks)
        idx = (starts[:, None] + np.arange(block)).ravel()[: len(x)]
        means.append(np.mean(x[idx]))
    return clean(
        {
            "lower": np.quantile(means, 0.025),
            "upper": np.quantile(means, 0.975),
            "block_samples": block,
            "replicates": replicates,
            "seed": seed,
            "kind": "Conditional moving-block percentile interval for segment mean; assumes locally representative dependence",
            "systematic_calibration_uncertainty": None,
            "not_total_measurement_error": True,
        }
    )


def analyze_signal(time, value, metadata):
    t, x, meta = normalize_signal(time, value, metadata)
    q = quality(t, x)
    lo, hi = q["longest_valid_segment"]
    ts = t[lo:hi]
    xs = x[lo:hi]
    valid = np.isfinite(x) & np.isfinite(t)
    result = {
        "identity": meta,
        "quality": q,
        "statistics": describe(x[valid]),
        "evidence_type": "DERIVED",
        "status": "computed",
        "method_version": METHOD_VERSION,
        "source_samples_unchanged": True,
    }
    if (
        hi - lo < 256
        or q["time_nonfinite"]
        or q["duplicate_timestamps"]
        or q["nonmonotonic_steps"]
    ):
        result.update(
            status="inconclusive",
            reason="No sufficiently long valid segment with sound coordinates",
        )
        return clean(result)
    result["selected_segment"] = {
        "indices": [lo, hi],
        "start_s": ts[0],
        "end_s": ts[-1],
        "samples": len(xs),
        "excluded_samples_from_spectral_analysis": len(x) - len(xs),
    }
    result["spectral"] = spectra(ts, xs)
    result["mean_block_interval"] = block_mean_interval(xs)
    ev, parameters = events(ts, xs)
    result["events"] = ev
    result["event_parameters"] = parameters
    result["event_threshold_sensitivity"] = [
        {"threshold": z, "events": len(events(ts, xs, z)[0])} for z in [4, 6, 8]
    ]
    smooth = []
    for width in [11, 21, 41]:
        y = signal.savgol_filter(xs, width, 3, mode="interp")
        smooth.append(
            {
                "window_samples": width,
                "polynomial": 3,
                "rms_residual": np.sqrt(np.mean((xs - y) ** 2)),
                "filtered_rms": np.sqrt(np.mean(y * y)),
                "event_count_threshold6": len(events(ts, y)[0]),
            }
        )
    result["filter_sensitivity"] = smooth
    display = max(1, math.ceil(len(ts) / 1500))
    smoothed = signal.savgol_filter(xs, 21, 3)
    derivative = np.gradient(xs, ts, edge_order=2)
    rolling = np.convolve(xs, np.ones(21) / 21, mode="valid")
    result["display"] = {
        "time_s": ts[::display],
        "original": xs[::display],
        "savgol21": smoothed[::display],
        "derivative": derivative[::display],
        "rolling_mean21_time_s": ts[10:-10:display],
        "rolling_mean21": rolling[::display],
        "stride": display,
        "kind": "Display decimation only; metrics use all selected samples",
        "unit": meta["unit"],
        "derivative_unit": meta["unit"] + "/s",
    }
    result["limits"] = [
        "Source calibration/systematic uncertainty unavailable; statistical interval does not include it.",
        "Level2 is source-processed diagnostic data; source release known processing corrections may affect coordinates.",
        "Candidate transients are not automatically disruptions, ELMs or named physical instabilities.",
        "Cross-shot timing has no verified physical phase alignment.",
    ]
    return clean(result)


def pair_correlation(t1, x1, t2, x2):
    # No interpolation. Declared boxcar averaging; not an assertion of alias-free decimation.
    if len(t1) < 10 or len(t2) < 10:
        return {"status": "inconclusive"}
    t1 = np.asarray(t1, float)
    x1 = np.asarray(x1, float)
    t2 = np.asarray(t2, float)
    x2 = np.asarray(x2, float)
    if (
        not np.isfinite(t1).all()
        or not np.isfinite(t2).all()
        or np.any(np.diff(t1) <= 0)
        or np.any(np.diff(t2) <= 0)
    ):
        return {
            "status": "inconclusive",
            "reason": "Finite monotonic time references required",
        }
    common = (t1 >= t2[0]) & (t1 <= t2[-1])
    t = t1[common]
    a = x1[common]
    step = np.median(np.diff(t))
    b = []
    for time in t:
        values = x2[(t2 >= time - step / 2) & (t2 < time + step / 2)]
        b.append(
            np.mean(values) if len(values) and np.isfinite(values).all() else np.nan
        )
    b = np.asarray(b)
    valid = np.isfinite(a) & np.isfinite(b)
    all_a = a.copy()
    all_b = b.copy()
    a = a[valid]
    b = b[valid]
    times = t[valid]
    if len(a) < 52 or np.std(a) == 0 or np.std(b) == 0:
        return {"status": "inconclusive", "n": len(a)}
    lags = []
    for k in [-10, -5, -1, 0, 1, 5, 10]:
        xx = all_a[max(0, -k) : min(len(all_a), len(all_a) - k)]
        yy = all_b[max(0, k) : min(len(all_b), len(all_b) + k)]
        good = np.isfinite(xx) & np.isfinite(yy)
        xx = xx[good]
        yy = yy[good]
        lags.append(
            {
                "lag_samples": k,
                "lag_s": k * step,
                "n": len(xx),
                "pearson": (
                    stats.pearsonr(xx, yy).statistic
                    if len(xx) > 2 and np.std(xx) > 0 and np.std(yy) > 0
                    else None
                ),
            }
        )
    return clean(
        {
            "status": "computed",
            "n": len(a),
            "pearson": stats.pearsonr(a, b).statistic,
            "spearman": stats.spearmanr(a, b).statistic,
            "lags": lags,
            "positive_lag": "Coarse signal at t compared with voltage-bin mean at t+k; retrospective, not causal",
            "alignment": "Same shot source relative seconds; no interpolation; fast samples averaged within half coarse-step bins. Exact retained sample dates checked.",
            "limits": "Descriptive dependence, no IID p-values or physical causality. Boxcar averaging can leave aliasing; no modal or causal inference. Both measurements share experimental context.",
        }
    )
