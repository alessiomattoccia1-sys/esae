# Physics and numerical validation

Pint checks explicit input units and compatibility; kA→A and ms→s have analytical controls. Missing or incompatible units fail visibly. No density, temperature, field geometry or response coefficient is presumed to create new plasma quantities.

Controls cover sinusoid FFT amplitude, Welch integrated power, stationary STFT frequency, polynomial derivative/SG filter, known transient candidates, correlation alignment and lag preservation, rectangle detector centroid, NaN handling, independent-uncertainty sum and safe Zarr2/3 reads. Synthetic controls remain separate from actual source acquisition.

Real studies are additionally checked by an independent numerical script and complete raw-source replay. Frequency half-bin width and half-sample time are discretization descriptors. Moving-block intervals describe conditional statistical variability, not unmeasured calibration/systematic error. Detector ROI/background ranges are sensitivity, not measurement confidence intervals. Independent uncertainty propagation assumes independent inputs and is not applied to unknown source calibrations.

No literature reproduction or physical-mode identification is asserted. Numerical agreement is computational verification of the stated measurement-processing procedure.


Original software © 2026 Mattoccia Labs, Apache License 2.0. Scientific data and derived artifacts retain the separate source licenses.
