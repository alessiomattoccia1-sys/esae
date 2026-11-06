# Mathematical Core

State-space form x_next=f(x,u)+w and z=h(x)+v. State order for GaussianMotion: position then velocity(CV/KF/CRW), then acceleration(CA). d∈{1,2,3}; RW/OU contain position only. The application supplies coordinate units. Process intensity q and observation variance r are mathematical hyperparameters; they are not independently calibrated physical sensor errors.

Exact linear Gaussian transitions use F and integrated white acceleration/jerk Q for CV/CA. OU uses exp(-theta*dt), Q=q(1-exp(-2theta*dt))/(2theta). CRW applies discrete velocity persistence rho**dt with a CV noise covariance; it is not claimed an exact continuous OU discretization. Joseph covariance update preserves PSD; asymmetric/nonfinite/negative covariance inputs fail. Partial observation rows update only finite dimensions.

Methods initialize/predict/observe/update/simulate/reset/get_state/get_uncertainty/serialize are available on GaussianMotion. Specialized estimators expose equivalent state operations with distinct HMM/Monte Carlo result types. HMM posterior states are not position estimates. Numerical integration uses scipy.integrate.solve_ivp with recorded tolerances and finite increasing time grids.

Creator: Codex per Alessio, 6 November2026. PROJECT; retain until explicit retirement. Original software SPDX-License-Identifier: Apache-2.0.
