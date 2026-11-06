# DME-002 — method

Kind: REAL EXPERIMENTAL DATA. Algorithm: dme-miluv-1.0.

AERPAW unavailable(403public/401API), replaced with user-authorized MILUV v1(CC BY4.0). Three predefined single-UAV sequences share anchor constellation0. Every selected UWB row analyzed; finite/positive gates, first timestamp+pair duplicate retained, explicit stable time sort. Residual=calibrated(or raw) range−source gt_range, metres. Source gt_range derived from motion capture, not exact truth. Published std assessed with ±1.95996398454σ nominal normal95percent intervals. A second computation uses nearest motion capture(≤20ms), no extrapolation: tag_world=p_world+Rotation(quaternion xyzw)×tag_body; distance=norm(tag_world−anchor_world), pinned published extrinsics. Tolerance5/10/20ms and offset−20/−10/0/10/20ms sensitivity reported. Source spline-derived reference may differ from nearest-time reconstruction. No synchronization fitted to residuals; no3D position error claimed. Pooled metrics observation-weighted; equal-flight MAE separately reported. Source calibration training/validation independence unknown; total systematic uncertainty unavailable.

## Limits
- UWB range residual is not3D position error or UAV intent.
- Source gt_range is motion-capture-derived, not exact physical truth; reconstruction uses same reference system.
- Published std is a calibrated measurement uncertainty model, not known total uncertainty; nominal normal95percent coverage is measured, not guaranteed.
- Source calibrator training/held-out independence not established; before/after comparison is descriptive.
- Three selected flights/one UAV/indoor constellation0 do not establish generalization across36experiments or platforms.
- Nearest-time differences and source spline processing can explain reconstructed-vs-published reference differences; no unrecorded alignment or recalibration.

## Source
{
  "name": "MILUV: A Multi-UAV Indoor Localization dataset with UWB and Vision",
  "doi": "10.25452/figshare.plus.28386041.v1",
  "version": 1,
  "source": "https://api.figshare.com/v2/articles/28386041",
  "license": "CC BY 4.0",
  "authors": [
    "Mohammed Shalaby",
    "Syed Shabbir Ahmed",
    "Nicholas Dahdah",
    "Charles Cossette",
    "Jerome Le Ny",
    "James R. Forbes"
  ],
  "available_experiments_source_description": 36,
  "selected_flights": [
    "default_1_circular2D_0",
    "default_1_circular3D_0",
    "default_1_random3_0"
  ],
  "selected_members": [
    {
      "name": "default_1_circular2D_0/ifo001/uwb_range.csv",
      "archive_url": "https://ndownloader.figshare.com/files/52250714",
      "archive_size": 1862182413,
      "whole_archive_checksum_verified": false,
      "bytes": 5971295,
      "crc32": "4dba162d",
      "sha256": "7fc6a81e554a2ab609fc36b2cbef9aa166a4676a486be8862d4bd9623566e75b"
    },
    {
      "name": "default_1_circular2D_0/ifo001/mocap.csv",
      "archive_url": "https://ndownloader.figshare.com/files/52250714",
      "archive_size": 1862182413,
      "whole_archive_checksum_verified": false,
      "bytes": 2215752,
      "crc32": "72ef8c2b",
      "sha256": "32bf4a2876a3a4902d1dc387feb084a253528f60d35f1b98ce57c75ba4c5a19a"
    },
    {
      "name": "default_1_circular3D_0/ifo001/uwb_range.csv",
      "archive_url": "https://ndownloader.figshare.com/files/52250702",
      "archive_size": 1671977142,
      "whole_archive_checksum_verified": false,
      "bytes": 5704219,
      "crc32": "9048d367",
      "sha256": "8fc39328e537ed0b01f083a2355b78d7f497ba0aec58b257775ae4fcb6033def"
    },
    {
      "name": "default_1_circular3D_0/ifo001/mocap.csv",
      "archive_url": "https://ndownloader.figshare.com/files/52250702",
      "archive_size": 1671977142,
      "whole_archive_checksum_verified": false,
      "bytes": 2048266,
      "crc32": "d0b477ea",
      "sha256": "b508cc1479b697a1eb49ad5e259d1ade8501e1cf3d7821202bfa603e234d43e5"
    },
    {
      "name": "default_1_random3_0/ifo001/uwb_range.csv",
      "archive_url": "https://ndownloader.figshare.com/files/52250735",
      "archive_size": 2551133105,
      "whole_archive_checksum_verified": false,
      "bytes": 8747251,
      "crc32": "5df54254",
      "sha256": "05e4423870f001bbb1e6136c260e80055b694ddae20648e6b51c77cb14e64330"
    },
    {
      "name": "default_1_random3_0/ifo001/mocap.csv",
      "archive_url": "https://ndownloader.figshare.com/files/52250735",
      "archive_size": 2551133105,
      "whole_archive_checksum_verified": false,
      "bytes": 3123830,
      "crc32": "c65aae08",
      "sha256": "08bb608c14050f83a4f40711f09d8c281e4d6560663852ec3b7e0a3b021d5855"
    }
  ],
  "devkit_commit": "399ad46f4e6e88c3c98b40aae33fe8e2c6719cff",
  "configuration_hashes": {
    "config/experiments.csv": "8b66ed2185c7b68dc67ce285a1f481175b21cec7613bff8b732f841d2b79dc3c",
    "config/uwb/anchors.yaml": "4e38cef90d8db1cc0fed2a51aa2b67fee3a637140d4bdb685c1608472b5bb4f3",
    "config/uwb/tags.yaml": "6499c59ebfd498d3077d00c3fbecc3c873112641f25d1f1473b94b1a63be3215",
    "preprocess/cleanup_csv.py": "0798479fc0476a2dbbee644875fc0d04423d0c9c965ebfa42a9ca35aad820dbb",
    "preprocess/process_uwb.py": "e5e32fc672effec2af9ab21b14d3406d534bc27da1d85eba06766936493f4e3b",
    "miluv/utils.py": "dce4a0fa78744b70c183838f6f1bb000aef16775c6c098f929e186ecb8e822a6",
    "examples/ekfutils/imu_one_robot_models.py": "4b4beeaa1f73cf03a97d4f002aabd36de6f176e71d79fdbdd24e6a86c3f984ad"
  }
}
