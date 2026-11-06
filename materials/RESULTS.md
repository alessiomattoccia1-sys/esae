# MDE-001 — verified results

Completed:2026-11-06T04:33:42.775493+00:00 · duration31.639s (cached source; first live acquisition was separately recorded).93,902records acquired,93,902valid unique materials,0invalid,0duplicates.65,395normalized formulas, not a material count.

TB-mBJgaps21,559/93,902; optB88vdWgaps93,902/93,902; hull and formation values93,902/93,902 each; SLME10,022/93,902; full TB-mBJdielectric diagonals19,834/93,902.

A gap[0.8,2.2]eV:2,561/93,902. B adds hull≤0.1eV/atom:415/93,902. C adds reportedSLME≥10%:415/93,902.72,343lackTB-mBJgap;18,998are outsidegap;2,146A-candidates exceedhull. Here B/Cmembership is identical; ordering changes. No stage exclusion from missinghull/SLME in this particular B-cohort. All12criteria intersection95materials.

## Source-reported optical ranking examples

| JID | Formula | TB-mBJ / eV | Hull / eV atom⁻¹ | ReportedSLME / % | Source |
|---|---|---:|---:|---:|---|
| JVASP-12913 | SbI2F6 | 1.34 | 0.0 | 33.98 | [NIST](https://www.ctcms.nist.gov/~knc6/jsmol/JVASP-12913.html) |
| JVASP-3951 | Rb2PdBr6 | 1.343 | 0.0 | 33.97 | [NIST](https://www.ctcms.nist.gov/~knc6/jsmol/JVASP-3951.html) |
| JVASP-8125 | NaCuSe | 1.342 | 0.0 | 33.97 | [NIST](https://www.ctcms.nist.gov/~knc6/jsmol/JVASP-8125.html) |
| JVASP-7827 | Rb3Sb | 1.349 | 0.0001 | 33.94 | [NIST](https://www.ctcms.nist.gov/~knc6/jsmol/JVASP-7827.html) |
| JVASP-19759 | TbSe | 1.348 | 0.0204 | 33.94 | [NIST](https://www.ctcms.nist.gov/~knc6/jsmol/JVASP-19759.html) |
| JVASP-102790 | Cd2TeSe | 1.362 | 0.0 | 33.93 | [NIST](https://www.ctcms.nist.gov/~knc6/jsmol/JVASP-102790.html) |
| JVASP-35067 | KMgBi | 1.36 | 0.0 | 33.93 | [NIST](https://www.ctcms.nist.gov/~knc6/jsmol/JVASP-35067.html) |
| JVASP-99962 | MgCdS2 | 1.36 | 0.0 | 33.93 | [NIST](https://www.ctcms.nist.gov/~knc6/jsmol/JVASP-99962.html) |
| JVASP-109475 | Rb2TlAgF6 | 1.354 | 0.0 | 33.93 | [NIST](https://www.ctcms.nist.gov/~knc6/jsmol/JVASP-109475.html) |
| JVASP-65769 | Ba2SbBr | 1.353 | 0.0 | 33.93 | [NIST](https://www.ctcms.nist.gov/~knc6/jsmol/JVASP-65769.html) |

Two of3official-page comparisons disagree onSLME:JVASP-12913(33.98snapshot vs33.08page),JVASP-3951(33.97vs33.34);JVASP-8125agrees(33.97). Do not interpret ranking values as optical validation. Six raw-record/JARVISgeometrychecks pass.

## Sensitivity

| Gap / eV | Hull max / eV atom⁻¹ | Gap cohort | Optical cohort |
|---|---:|---:|---:|
| 0.8–2.2 | 0.0 | 2561 | 216 |
| 0.8–2.2 | 0.05 | 2561 | 347 |
| 0.8–2.2 | 0.1 | 2561 | 415 |
| 0.8–2.2 | 0.2 | 2561 | 521 |
| 1.0–2.0 | 0.0 | 1802 | 155 |
| 1.0–2.0 | 0.05 | 1802 | 243 |
| 1.0–2.0 | 0.1 | 1802 | 297 |
| 1.0–2.0 | 0.2 | 1802 | 367 |
| 1.2–1.8 | 0.0 | 1091 | 95 |
| 1.2–1.8 | 0.05 | 1091 | 152 |
| 1.2–1.8 | 0.1 | 1091 | 189 |
| 1.2–1.8 | 0.2 | 1091 | 228 |

Correlations are descriptive complete pairs. TB-mBJgap↔SLME:N9,377,Pearson−0.623170093866,Spearman−0.821802481387. They do not establish causality or a new physical law.

AnalysisSHA256:`1ae88ce32871d91d0ba984a557d92c84be508584ca015bf9716f0817d261eec7`. Complete distributions, allcandidate tiers, metadata and denominators are in MDE-001_RESULTS.json; CSVcontains allcandidates per tier. Raw and normalized offline replays must match before publication. NoLLMgenerated these values.
