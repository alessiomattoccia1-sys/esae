# Real owned-demo validation — ESAE v0.1

Scan `dd545378-9458-4fe4-b8e7-3f25e41188bc` · 2026-11-05T22:04:05.210230+00:00

10 files, 106 physical lines. 11 normalized static diagnostics, 11 separate heuristic indicators. No analyzer errors. Original hashes unchanged.

| Controlled defect | Location | Detected by |
|---|---|---|
| D01 Read one element past a four-element array | src/data.c:5 | cppcheck |
| D02 Dereference a constant null pointer | src/data.c:9 | clang-tidy, cppcheck |
| D03 Read sample on the path ready==0 | src/sensor.c:14 | clang-tidy, cppcheck |
| D04 Allocation leaves the function without free | src/data.c:14 | clang-tidy, cppcheck |

All four intentionally inserted defects matched actual analyzer output. Distinct reports at different locations can remain separate. Report counts are not uniquely proven defect counts.

Tests: 49 passed, 0 failed, 0 skipped. 24 browser checks. Optional local Ollama generated a real explanation for a reported null dereference, labeled hypothesis; wording is not a verified correction.

Safe controls: sensor_average validates pointer/count and caps count; data_store_safe checks pointer and capacity; comm_send checks null; resource_safe uses RAII.
No universal false-positive/sensitivity benchmark. WCET/race freedom/hardware behavior/certification were not verified.

Complete locations, rules, evidence, tool versions and AI label: [JSON](demo-report.json), [HTML](demo-report.html), [validation matrix](validation.json).
