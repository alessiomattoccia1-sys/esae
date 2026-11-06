# DME-003 — method

Kind: SIMULATED DATA. Algorithm: dme-simulation-1.0.

Five synthetic scenarios Aindependent/Bstochastic/Clocal velocity consensus/Dpartial observations/Eheterogeneous CV+CRW; N1/5/10/20/50×20seeds=500main runs. dt=.1s,200steps, q=noise²=.09, radius12abstract units, coupling.8, observationσ1, Dmissing.3. Synchronous consensus dv_i=κ(mean_neighbor(v)−v_i)dt; reflecting box±100, no targets or geography. Three separate RNG streams for process/measurement/missingness. Bootstrap resamples independent seeds. Sensitivity dt .05/.1/.2 at equal20s, noise .1/.3/.8, coupling0/.8/1.6, missing0/.3/.6. Observation cadence1/2/5 supplemental after first pilot. Same-seed replay byte checks strict scientific JSON. Timing excludes no work silently; run timing includes state recording/result assembly. Abstract results are not validated drone aerodynamics.

## Limits
- All values are synthetic abstract-system results, not real flights.
- Local velocity consensus and a reflecting box are defined mathematical rules, not validated aerodynamics.
- Different timesteps use equal physical duration but different stochastic discretizations; sensitivity is not a common-Brownian-path strong-convergence proof.
- Bootstrap intervals here resample independent simulation seeds, unlike temporal observations within real flights.

## Source
{
  "source": "Dynamics mathematical/simulation core",
  "license": "Apache-2.0 original generated synthetic data; no measured flights",
  "actual_flight_data": false
}

## Actual result

{
  "main_simulations": 500,
  "robustness_simulations": 15,
  "reproducibility_recalculations": 1,
  "maximum_agents": 50,
  "steps_per_main_run": 200,
  "seed_replicates_per_configuration": 20
}

Scientific SHA256: f154ddcdb4aebdec0a278e478fae39a500f3ee9383c4bfdcd1c20b63a9441a67
See reports/dynamics/DME-003_REPORT.html and RESULTS.md.
