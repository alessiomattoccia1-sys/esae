# Limitations

- Completion-only timestamps do not identify actual processing, service, waiting times or staffing capacity. Observed durations are elapsed intervals, often containing calendar/non-working time.
- Public data are an anonymized single-company historical release with out-of-period timestamps, possible censored cases, repeated observations and no lifecycle start/complete pairs. Dates are audited, not silently corrected.
- Repeated receipts/invoices may be legitimate installments; Change/Cancel is a descriptive proxy, not proof of waste, individual performance or confirmed regulatory violation.
- Model selection uses an explicit core projection, observed invoice endpoints, complete-quarter and document-disjoint subsets. This retrospective selection narrows generalization and may change duration distributions.
- Three alternatives are compared without test tuning. The current measured release fails the predefined variant-frequency validation bound. No globally validated company twin or forecasting ability is claimed.
-2-way matching has insufficient calibration/test evidence. Consignment has a different endpoint semantics and is kept in full discovery but excluded from invoice-clearance modelling.
- Markov routing loses dependencies between whole paths. Whole-trace bootstrap cannot invent unseen variants. Neither architecture establishes causal interventions.
- Resource/service what-if parameters are assumptions; capacity is designed for a specified sampled workload, not estimated real staffing. Paired Monte Carlo intervals are conditional on those assumptions.
- No prices/cost models, guaranteed savings, employee ranking, ERP/CRM integration or automatic recalibration to new private companies.
- Local API/dashboard and static public replays are implemented. The site does not execute the scientific backend. Private import creates normalized files only; it does not automatically validate another process.
- Optional Ollama output is an unverified hypothesis; no cloud service or model weights are required. No quality claim is made for a local generation unless a real accepted generation is recorded.
- Standalone wheel distribution is qualified only on native macOSAppleSilicon/Python3.12. Windows/Linux not tested. Event generator checkpointing is not implemented; deterministic reruns are.
