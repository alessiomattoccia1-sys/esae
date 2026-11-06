# Multi-agent simulation

Generic state(position,velocity), independent of drone aerodynamics. Common deterministic tick; dt=.01–1s; bounded N≤200, steps≤2000 and total state budget≤400000position values. Public validation covers N1/5/10/20/50,2D;3D numerical controls, no3D UI. A independent, B noisy, C local velocity consensus, D partial observations, E heterogeneous CV/CRW.

C rule: v_next += dt*kappa*(mean(old neighbor velocities)-old velocity), neighbors within radius12, no self loops, unchanged isolated agents. All agents update from the same old state. Reflecting box±100 abstract units. Separate process/measurement/visibility RNG streams ensure missing observations do not change latent dynamics. Observation cadence is configurable. Checkpoints preserve clock, states, three RNGs, records, boundary events and neighbor-degree history. Pause stops clock; replay pause affects visualization only after batch computation.

No pursuit, interception, encirclement, real geography, actuator commands or live UAV connections. Kalman estimates on exploratory simulations are derived only from noisy observations and explicitly remain unvalidated for arbitrary interacting scenarios.

Creator: Codex per Alessio, 6 November2026. PROJECT; retain until explicit retirement. Original software SPDX-License-Identifier: Apache-2.0.
