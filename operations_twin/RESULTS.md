# Verified results and acceptance scope

Status: **functional prototype with validation limits; not a fully validated company twin**. Historical findings, measured model errors and hypothetical scenarios remain separate.

## Historical findings

Full original source: 1,595,923events; 251,734line-item cases; 76,349purchase documents; 42activities; 11,973distinct activity sequences across categories; 498distinct activity-pair transitions across categories.

| Category | Cases | Mean elapsed d | Median d | P90 d | P95 d |
|---|---:|---:|---:|---:|---:|
| 3-way match, invoice before GR | 221010 | 74.465828 | 66.347917 | 127.041667 | 142.240764 |
| 3-way match, invoice after GR | 15182 | 74.959061 | 63.422222 | 133.967431 | 189.511111 |
| Consignment | 14498 | 24.103579 | 19.926042 | 48.678681 | 62.126562 |
| 2-way match | 1044 | 57.453668 | 23.686111 | 196.864306 | 250.134028 |

Excluded required-field events: 0 / 1595923 (0.0%). All 132,748exact full-attribute duplicate candidates remain; absent event IDs prevent proving they are errors. 45,455events are outside2018, which is the source's purchase-order cohort year, not a validity bound on all event timestamps. Missing resource fields: 399,090. Missing lifecycle: 1,595,923 / 1,595,923.

Repeated-activity cases: 22,438 / 251,734 (8.9134%). Extra repeated occurrences: 290,532. Change/Cancel-proxy cases: 37,923; neither proxy is confirmed waste.

## Independently tested model results

Calibration 23,886cases; validation 3,000; test 1,757cases / 654documents. Model selected on validation only: **pooled_bootstrap**. All alternatives remain in the independent test table.

| Model | Mean error % | Median error % | P90 error % | Throughput error % | Variant TV |
|---|---:|---:|---:|---:|---:|
| pooled_bootstrap | 12.161292 | 10.242712 | 22.519112 | 15.278884 | 0.372339 |
| category_bootstrap | 11.723859 | 9.973428 | 21.675632 | 15.065452 | 0.368867 |
| semi_markov | 11.565598 | 1.964926 | 30.809076 | 18.201480 | 0.780933 |

The predefined variant-TV bound0.30fails for the selected model. No category is claimed fully validated by all tests. Two-way matching has only2calibration and1test case, insufficient for acceptance. Better test mean error of another model does not override validation-only selection. The semi-Markov model is not automatically superior.

| Test category | Cases | Selected-model90%interval coverage |
|---|---:|---:|
| 2-way match | 1 | 100.000000% |
| 3-way match, invoice after GR | 104 | 93.269231% |
| 3-way match, invoice before GR | 1652 | 92.554479% |

## Hypothetical improvements — not observed business gains

750base cases, 50replicas × 7scenarios = 350main runs. Nine sensitivity cells ×5replicas =45additional runs. Maximum975agents in demand-growth scenarios. Target **Clear Invoice** selected by calibration incoming elapsed gaps. Assumed service fraction0.05; designed utilization0.7. Base abstract capacity18slots, not real staff.

| Scenario | Mean simulated d |95%MC mean CI d | Paired delta d |95%delta CI d |
|---|---:|---|---:|---|
| base | 49.143844 | [48.9235027784976, 49.364184645576465] | 0.000000 | [0.0, 0.0] |
| demand_growth | 49.984755 | [49.771183130380265, 50.19832723001859] | 0.840911 | [0.6874909652094421, 0.9943319711153462] |
| capacity_reduction | 49.949698 | [49.66740591527875, 50.23199082546199] | 0.805855 | [0.683259486781606, 0.9284498298850612] |
| automation | 48.807802 | [48.58967738660618, 49.025927298579006] | -0.336041 | [-0.34553646969535, -0.32654626919353835] |
| rework_reduction | 49.094687 | [48.87877281753966, 49.310601000978856] | -0.049157 | [-0.1323526452499168, 0.03403903969436005] |
| disruption | 49.184846 | [48.966023871737974, 49.403668433817586] | 0.041002 | [0.03247234736491192, 0.049532534116570326] |
| combined | 48.797157 | [48.61690166537723, 48.97741230157435] | -0.346687 | [-0.4899988415925756, -0.20337461552992947] |

All resource/service scenarios are **HYPOTHETICAL / NOT VALIDATED**. Paired differences describe model responses, not causal company improvements, economic savings or personal productivity. No unfinished case is hidden; all published main runs report zero unfinished cases.

## Acceptance not reached

The functional software, real ingestion/reconstruction, independent numerical validation, reports and scenarios are implemented. The stronger criterion of a fully validated digital twin is **not reached** because predefined distributional thresholds fail. This negative result is preserved; source data, cohorts and thresholds were not changed to manufacture acceptance.
