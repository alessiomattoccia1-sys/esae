# Copyright 2026 Alessio Mattoccia
# SPDX-License-Identifier: Apache-2.0
"""Explicit dimensions and uncertainty types, never assumed plasma parameters."""

import numpy as np, pint

ureg = pint.UnitRegistry()


def convert(values, source, target):
    if (
        not isinstance(source, str)
        or not source
        or len(source) > 50
        or not isinstance(target, str)
    ):
        raise ValueError("Explicit bounded source and target units required")
    try:
        return np.asarray(
            ureg.Quantity(np.asarray(values, dtype=float), source).to(target).magnitude,
            dtype=float,
        )
    except (pint.PintError, ValueError, TypeError) as e:
        raise ValueError("Incompatible or unknown physical units") from e


def uncertainty_sum_independent(values, standard_uncertainties, weights=None):
    values = np.asarray(values, float)
    u = np.asarray(standard_uncertainties, float)
    w = np.ones_like(values) if weights is None else np.asarray(weights, float)
    if (
        values.shape != u.shape
        or w.shape != values.shape
        or not np.isfinite(values).all()
        or not np.isfinite(u).all()
        or (u < 0).any()
    ):
        raise ValueError("Compatible finite independent inputs required")
    return {
        "value": float(w @ values),
        "standard_uncertainty": float(np.sqrt(np.sum((w * u) ** 2))),
        "assumptions": "Independent stated standard uncertainties; covariance/systematic effects not included",
    }


def normalize_signal(time, value, metadata):
    expected = "V" if "voltage" in metadata["diagnostic"] else "A"
    t = convert(time, metadata["time_unit"], "s")
    x = convert(value, metadata["unit"], expected)
    if t.shape != x.shape or t.ndim != 1:
        raise ValueError("Signal/time shapes differ")
    return (
        t,
        x,
        dict(
            metadata,
            original_unit=metadata["unit"],
            original_time_unit=metadata["time_unit"],
            unit=expected,
            time_unit="s",
            normalization="Explicit Pint dimensional conversion; original source arrays remain unchanged",
        ),
    )
