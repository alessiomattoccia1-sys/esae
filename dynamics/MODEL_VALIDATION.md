# Model validation

Numerical controls cover exact CV/CA/OU semigroup and noise covariance, OU closed form, scalar Joseph update, partial observations, EKF nonlinear Jacobian, PF ESS/weight degeneracy, HMM probability normalization, independent Monte Carlo increment reconstruction, solve_ivp decay, coordinate conversion and mixture total covariance. Simulation controls verify checkpoint replay, missing-data RNG separation, cadence and50agents. API tests cover loopback/cross-origin/request header/input bounds and persistent reload.

DME-001 splits whole source files12development/9validation/9test. Shared platform/circuit and unknown day group limit independence. Hyperparameters, covariance scaling and ensemble weights use validation only, never test outcomes. Accuracy uses shared origins/horizons; modified-context comparisons include matched-origin baselines. Whole-flight bootstrap999, seed20261106; exact paired signflip and Holm correction are conditional on file-level exchangeability. No universal superiority claim.

DME-002 range/reference residual and geometry reconstruction are separately reported; covariance coverage is empirical, not physical calibration certification. DME-003 resamples independent simulation seeds, not successive temporal samples. Full original-byte offline replay and separate arithmetic/OLS/geometry acceptance audits complement fixture tests. First MC test used a flaky arbitrary±20percent variance tolerance; it failed and was replaced by a stronger exact independent increment reconstruction plus99.9percent chi-square control. Original failure preserved in operations evidence.

Creator: Codex per Alessio, 6 November2026. PROJECT; retain until explicit retirement. Original software SPDX-License-Identifier: Apache-2.0.
