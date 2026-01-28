"""Base ophyd Device class for tomoscan Bluesky integration

This module provides the base TomoScanDevice class that implements core
tomography scanning functionality using the ophyd/Bluesky framework.
"""


from ophyd import Component as Cpt
from ophyd import Device
from ophyd import EpicsSignal
from ophyd import EpicsSignalRO


class TomoScanDevice(Device):
    """Base ophyd Device for tomography scanning with EPICS

    This class provides the core functionality for tomography data collection
    at APS beamlines using the Bluesky framework.

    Parameters
    ----------
    prefix : str
        The EPICS PV prefix for the TomoScan IOC (e.g., '13BMDPG1:TS:')
    **kwargs
        Additional keyword arguments passed to Device.__init__

    Attributes
    ----------
    scan_is_running : bool
        Flag indicating if a scan is currently running
    theta : ndarray or None
        Array of rotation angles for the current/last scan
    """

    # Configuration PVs - values saved with scan configuration
    rotation_start = Cpt(EpicsSignal, 'RotationStart', kind='config')
    rotation_step = Cpt(EpicsSignal, 'RotationStep', kind='config')
    rotation_stop = Cpt(EpicsSignal, 'RotationStop', kind='config')
    num_angles = Cpt(EpicsSignal, 'NumAngles', kind='config')
    return_rotation = Cpt(EpicsSignal, 'ReturnRotation', string=True, kind='config')

    exposure_time = Cpt(EpicsSignal, 'ExposureTime', kind='config')

    # Dark field configuration
    num_dark_fields = Cpt(EpicsSignal, 'NumDarkFields', kind='config')
    dark_field_mode = Cpt(EpicsSignal, 'DarkFieldMode', string=True, kind='config')
    dark_field_value = Cpt(EpicsSignal, 'DarkFieldValue', kind='config')

    # Flat field configuration
    num_flat_fields = Cpt(EpicsSignal, 'NumFlatFields', kind='config')
    flat_field_mode = Cpt(EpicsSignal, 'FlatFieldMode', string=True, kind='config')
    flat_field_value = Cpt(EpicsSignal, 'FlatFieldValue', kind='config')
    flat_field_axis = Cpt(EpicsSignal, 'FlatFieldAxis', string=True, kind='config')
    sample_in_x = Cpt(EpicsSignal, 'SampleInX', kind='config')
    sample_out_x = Cpt(EpicsSignal, 'SampleOutX', kind='config')
    sample_in_y = Cpt(EpicsSignal, 'SampleInY', kind='config')
    sample_out_y = Cpt(EpicsSignal, 'SampleOutY', kind='config')
    sample_out_angle_enable = Cpt(EpicsSignal, 'SampleOutAngleEnable', string=True, kind='config')
    sample_out_angle = Cpt(EpicsSignal, 'SampleOutAngle', kind='config')

    different_flat_exposure = Cpt(EpicsSignal, 'DifferentFlatExposure', string=True, kind='config')
    flat_exposure_time = Cpt(EpicsSignal, 'FlatExposureTime', kind='config')

    # File configuration
    file_path = Cpt(EpicsSignal, 'FilePath', string=True, kind='config')
    file_name = Cpt(EpicsSignal, 'FileName', string=True, kind='config')
    file_path_exists = Cpt(EpicsSignal, 'FilePathExists', kind='config')

    # Control signals
    start_scan = Cpt(EpicsSignal, 'StartScan', kind='omitted')
    abort_scan_pv = Cpt(EpicsSignal, 'AbortScan', kind='omitted')
    scan_status = Cpt(EpicsSignal, 'ScanStatus', string=True, kind='normal')
    server_running = Cpt(EpicsSignalRO, 'ServerRunning', kind='omitted')

    move_sample_in_pv = Cpt(EpicsSignal, 'MoveSampleIn', kind='omitted')
    move_sample_out_pv = Cpt(EpicsSignal, 'MoveSampleOut', kind='omitted')

    # Sample information
    sample_name = Cpt(EpicsSignal, 'SampleName', string=True, kind='config')

    # Shutter PVs (may be None for some beamlines)
    # close_shutter_pv = Cpt(EpicsSignal, 'CloseShutter', kind='config')
    # close_shutter_value = Cpt(EpicsSignal, 'CloseShutterValue', kind='config')
    # open_shutter_pv = Cpt(EpicsSignal, 'OpenShutter', kind='config')
    # open_shutter_value = Cpt(EpicsSignal, 'OpenShutterValue', kind='config')

    # PV prefixes - these store the prefixes for other IOCs
    camera_pv_prefix = Cpt(EpicsSignal, 'CameraPVPrefix', string=True, kind='config')
    file_plugin_pv_prefix = Cpt(EpicsSignal, 'FilePluginPVPrefix', string=True, kind='config')

    # Rotation PV name
    rotation_pv_name = Cpt(EpicsSignal, 'RotationPVName', string=True, kind='config')

    # Sample motor PV names
    sample_x_pv_name = Cpt(EpicsSignal, 'SampleXPVName', string=True, kind='config')
    sample_y_pv_name = Cpt(EpicsSignal, 'SampleYPVName', string=True, kind='config')

    # Watchdog
    watchdog = Cpt(EpicsSignal, 'Watchdog', kind='omitted')


