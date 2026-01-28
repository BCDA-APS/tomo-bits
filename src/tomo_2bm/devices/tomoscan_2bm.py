"""2BM-specific ophyd Device class for tomoscan Bluesky integration

This module provides the TomoScan2BMDevice class that implements beamline-specific
functionality for APS beamline 2-BM, including dual camera support, shutters,
and data transfer capabilities.
"""


from ophyd import Component as Cpt
from ophyd import EpicsSignal
from ophyd import EpicsSignalRO

from tomo_instrument.devices.tomoscan_helical import TomoScanHelicalDevice


class TomoScan2BMDevice(TomoScanHelicalDevice):
    """ophyd Device for tomography scanning at APS beamline 2-BM

    This class extends TomoScanHelicalDevice with 2-BM-specific features:
    - Dual camera support via mctOptics
    - Front-end and fast shutter control
    - Camera-specific trigger modes (Oryx, Grasshopper, Adimec)
    - HDF5 theta array postprocessing
    - Data transfer to analysis computer
    - Webcam frame capture

    """

    testing = Cpt(EpicsSignal, 'Testing', kind='config')

    # Front-end shutter (different from fast shutter)
    # shutter_status = Cpt(EpicsSignalRO, 'ShutterStatus', kind='normal')

    # Data transfer settings
    copy_to_analysis_dir = Cpt(EpicsSignal, 'CopyToAnalysisDir', kind='config')
    remote_analysis_dir = Cpt(EpicsSignal, 'RemoteAnalysisDir', string=True, kind='config')

    # File path configuration
    detector_top_dir = Cpt(EpicsSignal, 'DetectorTopDir', string=True, kind='config')
    experiment_year_month = Cpt(EpicsSignal, 'ExperimentYearMonth', string=True, kind='config')
    user_last_name = Cpt(EpicsSignal, 'UserLastName', string=True, kind='config')

    # File writer settings
    overwrite_warning = Cpt(EpicsSignal, 'OverwriteWarning', string=True, kind='config')
