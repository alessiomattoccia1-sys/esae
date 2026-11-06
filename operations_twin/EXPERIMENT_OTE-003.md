# OTE-003 — Enterprise What-If Simulation

HYPOTHETICAL SCENARIO · completed 2026-11-06T12:21:11.367491+00:00

# OTE-003 Methodology

Category semi-Markov routes calibrated on historical elapsed gaps are combined with a separate hypothetical SimPy FIFO resource layer. Target activity is selected using calibration mean incoming elapsed delay among activities with100transitions. Default5percent of each target incoming gap is assumed to be service;95percent remains exogenous delay. Abstract capacity is designed from specified sample workload and target utilization0.7, not identified real staffing.750SHA-selected heldoutarrivals,50replicas per scenario,seed20261106. Seven scenarios: base,demand+30percent,capacity-25percent,assumed service-20percent,Change/Cancel transition weight-20percent,nonpreemptive temporary capacity reduction days30–45,and combined. Per-case/replicate/component random streams preserve original-agent draws; route interventions alter later correspondence. Nine service-share/utilization sensitivity cells use150cases and5replicas each. All outcomes are HYPOTHETICAL SCENARIOS / NOT VALIDATED. Paired MC95percent confidence intervals represent conditional model differences, not causal organizational improvements. No economic savings are calculated.

- All resource/service parameters are explicitly hypothetical; historical elapsed intervals cannot identify them.
- These are model responses, not demonstrated organizational improvements or causal effects.
- Change/Cancel intervention changes transition weights20percent then renormalizes; it does not guarantee20percent fewer repeats.
- Arrival count grows30percent within the selected cohort; throughput levels cannot be extrapolated to the whole company.
- No money, staff productivity or guaranteed savings are calculated.
- Sensitivity design changes both assumed share and designed slots, rather than identifying a unique real capacity.


Result fingerprint: `6855a0170325dffa811a51831f47be6741f66f879d8619900076fddba8db8742`

Outputs: `reports/operations-twin/OTE-003_REPORT.html`, results JSON, metrics CSV, manifest, methodology and reproducibility files. The same results feed the local dashboard and public page.
