# Process model and simulator roles

Case agent = generic Dynamics EventAgent. Task = an activity coroutine emitting start/completion events; starts in the empirical model are synthetic instantaneous transitions after an observed elapsed gap, not observed lifecycle starts. Resource agent = SimPy FIFO Resource plus measured synthetic queue/busy state. Workflow controller = calibrated trace/bootstrap or semi-Markov routing. Scheduler/clock = generic EventCore. Histories and bounded events feed actual replay, not decorative movement.

Empirical Process Twin models observed elapsed intervals without claiming to identify service/waiting components. Resource-Constrained Twin explicitly partitions a selected incoming elapsed gap into assumed service and exogenous delay, then adds abstract FIFO capacity. Remaining activities retain empirical elapsed delays. Capacities, service share and disruption calendars are configurable assumptions. The published temporary disruption holds abstract slots nonpreemptively days30–45, recording actual hold acquisition. No employee is modeled psychologically or scored.

Calibration preserves separate process categories and includes zero elapsed intervals. Whole-trace sampling preserves observed route dependence; semi-Markov routing does not. Arrival/positive-interval distribution fits are descriptive and cannot identify service or staffing. Local import does not automatically establish model validity for a new organization.

