# Model validation

The preregistered plan was saved after inspecting only three traces for schema, before full aggregate analysis. No test-set tuning or post-hoc acceptance relaxation is allowed.

Core projection removes only SRM-prefixed administrative events for modelling, not full process reconstruction. Eligible cases have observed projected creation and invoice-clearance endpoints entirely within one2018quarter; this creates retrospective selection bias and does not prove business completion. Cross-set purchasing documents are excluded. Q1+Q2calibration, Q3validation, Q4independent test. A deterministic SHA256ranking caps validation/test samples3000cases each without selecting outcomes.

Three alternatives: pooled whole-trace bootstrap, category whole-trace bootstrap, category semi-Markov routing/elapsed gaps. Identical observed heldoutarrival schedules and92day windows;20seeded replicas per model/set. Seven equally weighted errors select the validation winner: relative mean/median/P90elapsed-duration errors, fixed-window completion-count relative error, Wasserstein/observedmean, variant total variation, absolute Change/Cancel-case-rate difference. This is an engineering objective, not scientific confidence.

Per-category test bounds fixed beforehand: mean/median≤20%,P90≤25%,throughput≤20%,Wasserstein/mean≤.2,variantTV≤.3,Change/Cancel rate difference≤.1,min100cases. A category passes only if all apply and simulations finish. The release reports failures; no full validation claim is made when a route-frequency test fails. Rare2-way matching has only2calibration cases and1test case: insufficient evidence.

90% marginal duration intervals use only calibration-generated samples. Coverage on the heldout test is shown. Mean Monte Carlo CIs and whole-document bootstrap intervals describe different uncertainty sources. A mean fit is not individual-case prediction calibration, causal identification, prospective validation or proof of generalization beyond this cohort.
