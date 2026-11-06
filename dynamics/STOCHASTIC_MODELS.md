# Stochastic models

RW: Gaussian independent increments, baseline. CRW: temporally persistent velocity, rho∈(0,1). CV: integrated white acceleration; CA: integrated white jerk. OU: mean reversion toward an explicit reference, not presumed flight realism. Linear Kalman: Joseph update, finite observation subsets. EKF: supplied nonlinear functions and explicit Jacobians; tested against known scalar nonlinear and linear controls, not all real UAV flight dynamics. Particle filter: bounded particles, log-likelihood weights, normalized ESS and systematic seeded resampling; nonfinite likelihoods return insufficient evidence rather than fabricated evidence. Gaussian HMM: diagonal emissions, log forward/backward/Baum-Welch, ordered sequence boundaries, descriptive latent labels. Monte Carlo: SeedSequence-spawned independent runs, initial covariance sampling, quantiles and aggregate terminal covariance.

DME-001 benchmarks RW/CV/CA/KF/CRW/OU only. EKF and PF numerical controls are not described as real-flight benchmark wins. MC and HMM are not substituted for trajectory forecasts. Complex methods and the ensemble are not automatically superior.

Creator: Codex per Alessio, 6 November2026. PROJECT; retain until explicit retirement. Original software SPDX-License-Identifier: Apache-2.0.
