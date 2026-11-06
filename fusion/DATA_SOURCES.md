# Data sources and rights

## UKAEA FAIR-MAST

Official overview: https://www.ukaea.org/service/fair-mast/ . Current official documentation: https://github.com/ukaea/fair-mast and https://ukaea.github.io/fair-mast/ . Original documentation and source metadata were inspected as data, not executed.

The legacy mastapp.site JSON/documentation endpoint timed out during assessment. The current official quickstart documents anonymous S3 Parquet catalogs and Zarr diagnostic stores. The connector uses https://s3.echo.stfc.ac.uk/mast/fairmast-meta/l2_shots.parquet and selected level2/shots/SHOT.zarr/ objects. Level 1 is consolidated Zarr2; Level 2 is consolidated Zarr3, not a failed Zarr2 store. Source metadata includes ingestion timestamp and commit where present. Catalog entries are not measurements.

UKAEA states CC BY-SA 4.0 unless a specific exception applies: https://creativecommons.org/licenses/by-sa/4.0/ . Per-group license metadata is checked. Attribution: UKAEA FAIR-MAST and source contributors. Associated source documentation cites Jackson et al., SoftwareX 27 (2024), 101869, DOI https://doi.org/10.1016/j.softx.2024.101869 ; this project does not claim to reproduce that paper.

Changes by Mattoccia Labs: selected shot/time/channel chunks, explicit unit normalization, diagnostic statistics, signal transformations and visualizations. Data-derived FPE-001 artifacts remain CC BY-SA 4.0. No UKAEA endorsement is implied.

## STFC eData

Official item: https://edata.stfc.ac.uk/items/e7a22beb-f55a-45a0-a0c7-bca8eb94d849 . DOI https://doi.org/10.5286/edata/944 . Issued 2025-06-17. Archive DataRepo.zip: 64,965,109 bytes; SHA-256 89928d857b29304d0be65ca0805b398444dfbea9802a37c6473e2f1089dd0966.

The item explicitly declares CC BY 4.0: https://creativecommons.org/licenses/by/4.0/ . Complete source authors are retained from the official item metadata in the result dataset. Attribution is to those authors and STFC eData, not solely to this engine.

The archive includes heterogeneous diagnostics and operating/performance material. Only the seven raw SLOS-TRXI HDF4 gel_raw detector frames are numerically analyzed. Other members are cataloged without executing scripts or analyzing target/laser/performance fields. Changes: fixed detector ROI/background operations, statistics, profiles and explicitly scaled display images. FPE-002 derived scientific artifacts remain CC BY 4.0. Source originals are unchanged; no source endorsement is implied.

No LLNL data is acquired in v0.1. Synthetic algorithm fixtures are identified separately and never counted as experimental evidence. No complete third-party raw archive is redistributed in the source package.


Original software © 2026 Mattoccia Labs, Apache License 2.0. Scientific data and derived artifacts retain the separate source licenses.
