# Verified results — Dynamics Lab0.1.0

Actual33recorded flight files:30IDF plus3MILUV. Distinct observation types:75510GNSS rows,34019UWB ranges and48515source motion-capture rows; do not call all observations independent samples. DME001uses9testflights/439origins/1317forecastpoints per method. DME002usespublished range reference for all34019validUWBrows and an independently computed nearest-mocap geometric check for34012rows;7outside matching tolerance remain explicit.

| Model | ADE m | FDE m | RMSE m | MAEcoordinate m | Coverage95 | ADE bootstrap95 |
|---|---:|---:|---:|---:|---:|---|
| RW | 34.795993 | 57.405282 | 41.426328 | 20.467411 | 0.960960 | 33.394519–36.455400 |
| CV | 12.743919 | 20.827194 | 22.185587 | 8.206763 | 0.906530 | 11.970185–13.572510 |
| CA | 18.129089 | 35.422055 | 29.652082 | 11.491921 | 0.883761 | 17.096728–19.133508 |
| KF | 9.121695 | 17.242098 | 15.832150 | 5.798683 | 0.904366 | 8.588942–9.715700 |
| CRW | 9.271408 | 17.240235 | 15.439684 | 5.926360 | 0.909744 | 8.723924–9.903149 |
| OU | 180.270339 | 237.539602 | 208.814684 | 116.086710 | 0.980210 | 170.895327–190.878435 |
| ENSEMBLE | 9.599610 | 17.400355 | 15.115730 | 6.119857 | 0.926349 | 9.085327–10.193451 |

KF beats CV by3.622223342750516m ADE on this sample. CA is worse than CV; ensemble ADE is worse than KF. All six preregistered paired-vs-CV signflip tests have Holm-adjustedp=.0234375, conditional on independent/exchangeable flight-file groups; unreported shared days limit that assumption. No universal platform generalization. KF nominal95percent coverage=.9043656784733796, not claimed well calibrated.

MILUV observation-weighted calibrated range RMSE=0.30776633109381496m, raw=0.3555526933853096m. MAE=0.17668887672333414m; empirical nominal95coverage=0.8401187571651136. Range, not3Dposition; reference/calibration share upstream processing, systematic uncertainty unknown.

DME003:500main synthetic simulations;15sensitivity runs;1exactsame-seed replay;100Monte Carlo control runs separately. Max tested50agents; five scenarios,200steps. None are recorded flights.

| Experiment | Total cached-run s | Source response bytes | Process lifetime peak RSS bytes |
|---|---:|---:|---:|
| DME-001 | 36.638933 | 2153015 | 227229696 |
| DME-002 | 5.363841 | 18750216 | 309002240 |
| DME-003 | 10.423513 | 0 | 375914496 |

Zero network bytes in these final cached runs; original live acquisitions preceded them and retain acquisition timestamps/HTTP206/source hashes. Timing not claimed for other hardware or with a fresh network.

| Agents | Median/run ms | Median/step ms | Runs |
|---|---:|---:|---:|
| 1 | 11.507542 | 0.057538 | 100 |
| 5 | 12.084396 | 0.060422 | 100 |
| 10 | 12.355688 | 0.061778 | 100 |
| 20 | 13.025771 | 0.065129 | 100 |
| 50 | 15.383479 | 0.076917 | 100 |

284full-suite tests pass, including246previous and38Dynamics. Two preexisting warnings(StarletteHTTPXdeprecation,Zarr3metadata). Independent full-test CV/polyfit, MILUV arithmetic/geometry, counting and negative-outcome checks pass.89originalsource objects rehashed and allthreeexperiments recomputed offline with identical scientific SHA.28dashboard layout cases plus simulation/reload/export interactions pass; native WebKit select rendering emits78known inline-style CSP denials while strict CSP stays enabled.

Initial MC fixture assertion failed under arbitrary±20percent tolerance; stronger exact independent Gaussian-increment reconstruction and statistical chi-square test replace it. First dashboard mobile pass found overflow in longreportSHA, fixed with wrapping. Initial full regression invocation had an import-path error before collection; rerun from repository root passes. These are preserved failures, not omitted scientific outcomes.

Source-runtime commit at execution: af8fd75. Full40-character commit and allworkingPythonfilehashes are in each manifest. Final publication and source-release receipts are separate evidence.

Optional AI qualification: local qwen3:4b was actually called twice on loopback11438 with selected public evidence. Both responses were rejected by the existing numerical/identifier guard and returned unavailable/not_verified; no generated measurements entered reports. Disabled and unavailable paths work. No successful generative explanation is claimed for these two attempts. The isolated model server was stopped after confirming zero resident models; stored model weights were preserved.
