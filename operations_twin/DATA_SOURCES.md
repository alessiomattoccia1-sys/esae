# Data sources

BPI Challenge2019, Boudewijn van Dongen, 4TU.ResearchData, version1, CC BY4.0.

- DOI: https://doi.org/10.4121/uuid:d06aff4b-79f0-45e6-8ec8-e19730c248f1
- Official metadata: https://data.4tu.nl/v2/articles/12715853
- Original XES: https://data.4tu.nl/file/35ed7122-966a-484e-a0e1-749b64e3366d/864493d1-3a58-47f6-ad6f-27f95f995828
- Official conference documentation: https://icpmconference.org/2019/icpm-2019/contests-challenges/bpi-challenge-2019/
- Official compressed copy: https://icpmconference.org/2019/wp-content/uploads/sites/6/2019/01/log_IEEE.xes_.gz

The16,901,365byte gzip expands to728,558,522bytes. Original MD5 `4eb909242351193a61e1c15b9c3cc814` matches4TU metadata. Original SHA256 `af63bc687fc4152f2123b05c3af7772b37ef3fce2d3f67f812666c9e356baae7`. This is the full original file, not a sample or alternative dataset. Manifest preserves acquisition response hashes and timestamps. Cache acquisition time is not misrepresented as a fresh download.

Schema is verified from actual XES: trace `concept:name` is the line-item case; `Purchasing Document` is a separate grouping; `Item Category` carries four matching categories; events contain `concept:name,time:timestamp,org:resource,User,Cumulative net worth (EUR)`. No lifecycle transition is present in the1,595,923imported events. The source describes2018but includes out-of-period timestamps: these are retained/flagged and excluded only from explicit sensitivity/model cohorts. Source amounts are anonymized and excluded from all cost claims.

Raw archives are kept locally. Public aggregate statistics and visualizations attribute the source and document transformations. Dataset licence is not changed by Apache2.0 software licensing. This release does not redistribute raw original business logs, resource/case/vendor identifiers or individualized evaluations.
