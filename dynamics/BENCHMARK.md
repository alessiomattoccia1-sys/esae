# Performance benchmark

Native Mini M1 / external SviluppoApp. Each experiment manifest reports source-response sizes, actual network bytes for that invocation, acquisition/analysis/total wall seconds, and whole-process lifetime peak RSS. Reusing cached sources legitimately reports zero new network bytes, not zero source size. Runtime measurements are not synthetic flight science. DME-003 separately records500run times and per-N median total/per-step times, including state recording/assembly; maximum tested count50agents.15sensitivity runs and one exact replay are separately counted. Additional Monte Carlo100run control is not called real data.

No throughput claim for untested200agent configurations or other hardware. The backend bounds input bytes/entries/steps, checks safe cancellation between stages and avoids downloading multi-GB image archives. It is not a DFT/aerodynamic simulator or operational controller. See generated RESULTS.md and experiment manifests for actual measured values, rather than theoretical performance.

Creator: Codex per Alessio, 6 November2026. PROJECT; retain until explicit retirement. Original software SPDX-License-Identifier: Apache-2.0.
