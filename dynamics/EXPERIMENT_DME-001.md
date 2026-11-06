# DME-001 — method

Kind: REAL EXPERIMENTAL DATA. Algorithm: dme-flight-1.0.

First30 sorted source GPS files; first12development, next9validation, last9test. File-disjoint, not recording-day-independent. Twenty past samples per origin, stride50; nearest observed targets1/3/5s within120ms; source gaps>2s rejected. WGS84 ECEF→local ENU horizontal, no altitude or Euclidean degrees. Six methods share identical origins and targets. q∈{.01,1,100}, R∈{1,10}, validationADE/NLL tie-break only. Covariance scale=validation equal-flight mean Mahalanobis²/2. Ensemble simplex minimizes validation equal-flight MSE; total covariance includes within-model and between-mean dispersion. ADE/FDE/RMSE/MAE/coverage aggregate equally over nine test files. Nominal95percent Gaussian ellipse (χ²₂), empirical coverage and999 whole-file bootstrap samples. Exact paired sign-flip512patterns, Holm correction over6comparisons. Robustness adds2m context noise or30percent missingness with untouched held-out reference and matched-origin baseline. HMM3 descriptive states fit development only on offline speed/acceleration/turn-rate features; not causal intent inference.

## Limits
- Recorded GNSS is a noisy reference, not known true state. Physical sensor calibration is unavailable.
- Flights share platform and circuit; recording-day groups are unavailable. File-disjoint splits prevent row leakage but do not prove external generalization or independent days.
- Gaussian nominal regions and validation scaling are empirically evaluated, not guaranteed confidence coverage.
- ADE averages sampled1/3/5second horizons, actual timestamp offsets recorded; no interpolation.
- All parameter and ensemble fitting use development/validation only; test outcomes are not tuning inputs.

## Source
{
  "source": "Zenodo IDF_DS",
  "doi": "10.5281/zenodo.16992976",
  "version": "v1.0",
  "archive_url": "https://zenodo.org/api/records/16992976/files/Speedybee%20DataSet.zip/content",
  "archive_total_bytes": 580834225,
  "archive_declared_md5_not_whole_verified": "md5:fa6210078d8f615118027a5310dfc99c",
  "whole_archive_downloaded": false,
  "license": "CC-BY-4.0",
  "authors": [
    "García Gascón, César"
  ],
  "concept_dataset_flights_claimed": 240,
  "readme_speedybee_flights_claimed": 120,
  "actual_gps_members": 111,
  "selected_by_rule": "First30lexicographically sorted GPS files before values; no outcome selection",
  "members": [
    {
      "name": "Speedybee DataSet/processed/GPS/Lap001_gps.csv",
      "bytes": 228258,
      "crc32": "2edff5e8",
      "sha256": "611f2d9417f94eaf6399d77bb971cd0dd2eba6c7dac9a8fce8e34bc87474a22e"
    },
    {
      "name": "Speedybee DataSet/processed/GPS/Lap002_gps.csv",
      "bytes": 231394,
      "crc32": "8f27f9c9",
      "sha256": "94c2761e3838f2b4c8ae479702bf5a68eca9d18a6ba5661dd76ca1748bbabb8f"
    },
    {
      "name": "Speedybee DataSet/processed/GPS/Lap003_gps.csv",
      "bytes": 243612,
      "crc32": "31c44155",
      "sha256": "3a7dcdbe64709d26c02df25b834694486bd2377c4e657b7eb0ce1c3a84eb42cc"
    },
    {
      "name": "Speedybee DataSet/processed/GPS/Lap004_gps.csv",
      "bytes": 235920,
      "crc32": "97f0d386",
      "sha256": "c004d14f072c859f0a931b340cb99019de239aa63d1db399333643f82ae1d6e9"
    },
    {
      "name": "Speedybee DataSet/processed/GPS/Lap005_gps.csv",
      "bytes": 249131,
      "crc32": "9f9dce17",
      "sha256": "87dc6dd1059970adefe57e8a4c2e3f4a111db4caec5a6feaefbd745bf8486dd7"
    },
    {
      "name": "Speedybee DataSet/processed/GPS/Lap006_gps.csv",
      "bytes": 254222,
      "crc32": "b3edca47",
      "sha256": "ce3972d05e2c3284350b89664c753952578a755fce7fef83414bdcb48dc4b970"
    },
    {
      "name": "Speedybee DataSet/processed/GPS/Lap007_gps.csv",
      "bytes": 264302,
      "crc32": "a739ff38",
      "sha256": "361af6176e811cb73ddbaa28a1ffa6d2e4d65f9dbbe15d34aa7ced043bb56422"
    },
    {
      "name": "Speedybee DataSet/processed/GPS/Lap008_gps.csv",
      "bytes": 272936,
      "crc32": "5e530db3",
      "sha256": "e67480ccd1920dcc8459df6843215a528fb4a71a2576799727825e09db7bc2f5"
    },
    {
      "name": "Speedybee DataSet/processed/GPS/Lap009_gps.csv",
      "bytes": 259655,
      "crc32": "e3939169",
      "sha256": "a47b6049a3af75537d28bca255f1fa2945f744110dda39d9da0dbf10672876a2"
    },
    {
      "name": "Speedybee DataSet/processed/GPS/Lap010_gps.csv",
      "bytes": 256720,
      "crc32": "27bbcdfb",
      "sha256": "d8aba94ed6fbddacb840efe1ac77c599b017343e4528054cb7457d744932a869"
    },
    {
      "name": "Speedybee DataSet/processed/GPS/Lap011_gps.csv",
      "bytes": 243010,
      "crc32": "ab2d62aa",
      "sha256": "4ea98abfdc71fef2696c5e9728192672688371f54955a01a99f34b752c198ec2"
    },
    {
      "name": "Speedybee DataSet/processed/GPS/Lap012_gps.csv",
      "bytes": 254490,
      "crc32": "1eb01a4a",
      "sha256": "198a1f288f9730b6bd2719f1c1d52dee83fdc32e1f0fe582749a43905fdc26cc"
    },
    {
      "name": "Speedybee DataSet/processed/GPS/Lap013_gps.csv",
      "bytes": 257315,
      "crc32": "cdd63c5b",
      "sha256": "ea87f3abe32840c99fdae07029c757d1486fc2f29a1d176e7b4b236c9885c66e"
    },
    {
      "name": "Speedybee DataSet/processed/GPS/Lap014_gps.csv",
      "bytes": 259710,
      "crc32": "3088c5a7",
      "sha256": "d8509493c63c55533eb026ea2175b1fdde38ce45ddfc7baf02411f45da5eb240"
    },
    {
      "name": "Speedybee DataSet/processed/GPS/Lap015_gps.csv",
      "bytes": 249987,
      "crc32": "3c6c451e",
      "sha256": "982a2b955c66b4ed4179ed8d7031192fdfd5fd33fc9ec6e501b16ce5b684d776"
    },
    {
      "name": "Speedybee DataSet/processed/GPS/Lap016_gps.csv",
      "bytes": 235317,
      "crc32": "f6b83870",
      "sha256": "4693a6abbb4117e430606a1d01eaa3a0df30d842e54742f9c15813a2ed8b8e7a"
    },
    {
      "name": "Speedybee DataSet/processed/GPS/Lap017_gps.csv",
      "bytes": 242644,
      "crc32": "826fb4da",
      "sha256": "0947fa4d061280d37cbb5c98787b5920e16cefdf6528af5880b2a4816781cc98"
    },
    {
      "name": "Speedybee DataSet/processed/GPS/Lap018_gps.csv",
      "bytes": 239197,
      "crc32": "857334f6",
      "sha256": "2b7e46d01b1a5d21dc5576f55a18bb214be4fed090f172a023b1dd882351d342"
    },
    {
      "name": "Speedybee DataSet/processed/GPS/Lap019_gps.csv",
      "bytes": 247048,
      "crc32": "f7c9f9c6",
      "sha256": "6edd511e690f9039e85d6015fbb5bec2f003f0ece97c51e094678a7fcd89085c"
    },
    {
      "name": "Speedybee DataSet/processed/GPS/Lap020_gps.csv",
      "bytes": 271949,
      "crc32": "93a157d2",
      "sha256": "83c97cf139f08d8fbacf392c3f640615b1aa8b83377e2d2862f6e5e5cd3f9023"
    },
    {
      "name": "Speedybee DataSet/processed/GPS/Lap021_gps.csv",
      "bytes": 240419,
      "crc32": "7177459f",
      "sha256": "825b5bc248217407b806fe5be760cfb1f3aadd8ceba86818227add8324c08186"
    },
    {
      "name": "Speedybee DataSet/processed/GPS/Lap022_gps.csv",
      "bytes": 229517,
      "crc32": "71808aff",
      "sha256": "e472a0659b1857b4d864e2c58e436a3d4a995e042fbba0343327087fc56db02e"
    },
    {
      "name": "Speedybee DataSet/processed/GPS/Lap023_gps.csv",
      "bytes": 210653,
      "crc32": "1891ef8a",
      "sha256": "148a50a720b34209859adb68670719270a094ab60df2c80029deafb9bf4bf19f"
    },
    {
      "name": "Speedybee DataSet/processed/GPS/Lap024_gps.csv",
      "bytes": 228523,
      "crc32": "96c03271",
      "sha256": "97277b993ddc84aa5eebdd594f26f5155da95af6244c423c0750aa0d6d252fa1"
    },
    {
      "name": "Speedybee DataSet/processed/GPS/Lap025_gps.csv",
      "bytes": 244486,
      "crc32": "b6d81cc7",
      "sha256": "deeb39735f004592716edf4b3338a4fcf39f881551e7a0aff39a2b1910957c80"
    },
    {
      "name": "Speedybee DataSet/processed/GPS/Lap026_gps.csv",
      "bytes": 241516,
      "crc32": "4e1c1b25",
      "sha256": "28aaf568bad86b7a34cd7b16e76f58cee81744f816e4ab756f53502e33f8cccd"
    },
    {
      "name": "Speedybee DataSet/processed/GPS/Lap027_gps.csv",
      "bytes": 254430,
      "crc32": "5c515dba",
      "sha256": "4f68df4fe56b302a935b6d604da67d975c7ab34d1a625e9cf7fdda215ca3925e"
    },
    {
      "name": "Speedybee DataSet/processed/GPS/Lap028_gps.csv",
      "bytes": 243290,
      "crc32": "556551a6",
      "sha256": "01a05bad69f90394cdcf84c76b7174abd339eb7a6a6c4ef894609ebb6ac60e4c"
    },
    {
      "name": "Speedybee DataSet/processed/GPS/Lap029_gps.csv",
      "bytes": 252361,
      "crc32": "38380c39",
      "sha256": "ed402784cf03d2d504f8f99261d4501cc3bb603dd0891ba74d4d22d926296837"
    },
    {
      "name": "Speedybee DataSet/processed/GPS/Lap030_gps.csv",
      "bytes": 274137,
      "crc32": "07cb2e80",
      "sha256": "74b0259266b6674238aa6664c62ec3d833d80948cafe01c901852d55d81f8219"
    }
  ],
  "excluded": [],
  "source_metadata_sha256": "61f648b3f9e0cebd3b40da4aa0f937fdaf376bb65b9d6c46239a69aa6c0a5a01",
  "imported_flights": 30,
  "raw_source_bytes": 7416149,
  "documentation_caveat": "Speedybee README describes120flights; actual archive has111GPS files. Do not conflate archive layouts or claim all240flights analyzed."
}

## Actual result

{
  "flights_imported": 30,
  "valid_source_observations": 75510,
  "excluded_source_rows": 0,
  "development_flights": 12,
  "validation_flights": 9,
  "test_flights": 9,
  "validation_origins": 450,
  "test_origins": 439,
  "test_forecast_points_per_model": 1317,
  "individual_models": 6,
  "ensemble_models": 1
}

Scientific SHA256: 1f0238e055f9f9a1d601982e68e3e6406f6148a4e768ca17fd0cdfed30427280
See reports/dynamics/DME-001_REPORT.html and RESULTS.md.
