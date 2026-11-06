# Third-party components and data

Original FPRE modules use Apache 2.0. They import existing original Research Core/ESAE components without changing their licenses. DEPENDENCY-LICENSE-AUDIT.json records exact installed distributions, declared licenses and hashes of their shipped license files.

NumPy/SciPy/Pandas/Xarray/Dask/Zarr/Pint/Matplotlib/PyArrow/FastAPI and associated dependencies retain their upstream licenses. Native HDF readers use pyhdf (MIT) and its upstream HDF dependencies; HDF5 is available through h5py but the selected experimental arrays are HDF4. Wheel-distributed native codecs/math libraries can have additional notices. No third-party wheel, binary, notebook code or library source is redistributed in this project archive. Hash-locked setup downloads the official distributions with their own notices; Apache 2.0 does not relicense them.

FAIR-MAST scientific derivatives are CC BY-SA 4.0; STFC derivatives are CC BY 4.0 with complete author attribution in the experiment result. See DATA_SOURCES.md, NOTICE and the per-report data notice. Dataset scientific claims and source-specific restrictions remain separate from original software licensing. No complete external paper is reproduced.


Original software © 2026 Mattoccia Labs, Apache License 2.0. Scientific data and derived artifacts retain the separate source licenses.
