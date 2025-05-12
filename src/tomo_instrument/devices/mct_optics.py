"""
MCT Optics Ophyd Device Classes and Usage Documentation

This module defines device classes for managing MCT optics via EPICS.
Each class is designed to interact with specific subsystems,
facilitating ease of use and configurability.

Example Usage:
```
# Initialize the MCTOptics device
optics = MCTOptics("2bm:MCTOptics:", name="optics")

# Access lens information
lens_names = optics.lens_info.name_0.get()
motor_name = optics.lens_info.motor_name.get()
```
"""

from ophyd import Component as Cpt
from ophyd import Device
from ophyd import EpicsSignal
from ophyd import EpicsSignalRO
from ophyd import FormattedComponent as FCpt


class MCTOpticsLensInfo(Device):
    """
    Class for managing lens metadata, motor, and focus-related PVs.

    Attributes:
        name_0 (EpicsSignal): PV for the name of lens 0.
        name_1 (EpicsSignal): PV for the name of lens 1.
        name_2 (EpicsSignal): PV for the name of lens 2.
        motor_name (EpicsSignal): PV for the motor controlling the lens.
        sample_x_name (EpicsSignal): PV for the X-axis sample motor.
        sample_y_name (EpicsSignal): PV for the Y-axis sample motor.
        sample_z_name (EpicsSignal): PV for the Z-axis sample motor.
        focus_name_0 (EpicsSignal): PV for the focus of lens 0.
        focus_name_1 (EpicsSignal): PV for the focus of lens 1.
        focus_name_2 (EpicsSignal): PV for the focus of lens 2.
    """

    name_0 = Cpt(EpicsSignal, "Name0")
    name_1 = Cpt(EpicsSignal, "Name1")
    name_2 = Cpt(EpicsSignal, "Name2")

    # Lens Motor PVs
    motor_name = Cpt(EpicsSignal, "MotorPVName")
    sample_x_name = Cpt(EpicsSignal, "SampleXPVName")
    sample_y_name = Cpt(EpicsSignal, "SampleYPVName")
    sample_z_name = Cpt(EpicsSignal, "SampleZPVName")

    # Lens Focus PVs
    focus_name_0 = Cpt(EpicsSignal, "0FocusPVName")
    focus_name_1 = Cpt(EpicsSignal, "1FocusPVName")
    focus_name_2 = Cpt(EpicsSignal, "2FocusPVName")


class MCTOpticsLensOffset(Device):
    """
    Class for defining lens offsets.

    Attributes:
        x_offset (EpicsSignal): X-axis offset PV.
        y_offset (EpicsSignal): Y-axis offset PV.
        z_offset (EpicsSignal): Z-axis offset PV.
        rotation (EpicsSignal): Rotation offset PV.
        focus (EpicsSignal): Focus offset PV.
    """

    # Lens Offset
    x_offset = Cpt(EpicsSignal, "XOffset")
    y_offset = Cpt(EpicsSignal, "YOffset")
    z_offset = Cpt(EpicsSignal, "ZOffset")
    rotation = Cpt(EpicsSignal, "Rotation")
    focus = Cpt(EpicsSignal, "Focus")


class MCTOpticsLensControl(Device):
    """
    Class for managing lens positions and offsets.

    Attributes:
        pos_0 (EpicsSignal): Position of lens 0.
        pos_1 (EpicsSignal): Position of lens 1.
        pos_2 (EpicsSignal): Position of lens 2.
        lens_1 (MCTOpticsLensOffset): Offset information for lens 1.
        lens_2 (MCTOpticsLensOffset): Offset information for lens 2.
    """

    # Lens Positions
    pos_0 = Cpt(EpicsSignal, "Pos0")
    pos_1 = Cpt(EpicsSignal, "Pos1")
    pos_2 = Cpt(EpicsSignal, "Pos2")
    lens_1 = Cpt(MCTOpticsLensOffset, "1")
    lens_2 = Cpt(MCTOpticsLensOffset, "2")


class MCTOpticsCameraControl(Device):
    """
    Class for managing camera control parameters.

    Attributes:
        pos (EpicsSignal): Position of the camera.
        pv_name (EpicsSignal): PV name of the camera.
        rotation_name (EpicsSignal): PV for camera rotation.
        lens_ctrl (MCTOpticsLensControl): Lens control associated with the camera.
    """

    def __init__(
        self,
        prefix: str,
        *args,
        **kwargs,
    ):
        """
        Initializes the camera control device. It extracts the base prefix
        and a trailing number from the provided prefix.

        Args:
            prefix (str): The EPICS prefix for the device.
            *args: Additional arguments for the Device initializer.
            **kwargs: Additional keyword arguments for the Device initializer.
        """

        # Identify the position where the trailing number starts
        split_index = len(prefix.rstrip("0123456789"))

        # Separate the base prefix and the trailing number
        self.base_prefix = prefix[:split_index]
        self.last_number = prefix[split_index:]

        super().__init__(prefix, *args, **kwargs)

    # Name
    pos = FCpt(EpicsSignal, "{base_prefix}Pos{last_number}")
    pv_name = FCpt(EpicsSignal, "{base_prefix}Name{last_number}")

    # Camera Rotation PV Name
    rotation_name = Cpt(EpicsSignal, "RotationPVName")

    # Lens Control
    lens_ctrl = Cpt(MCTOpticsLensControl, "Lens")


class MCTOptics(Device):
    """
    Ophyd Device Class for controlling MCT optics via EPICS.

    Attributes:
        lens_select (EpicsSignal): Select the lens (0-2).
        camera_select (EpicsSignal): Select the camera (0-1).
        camera_selected (EpicsSignalRO): Currently selected camera.
        cross_select (EpicsSignal): Crosshair selection.
        sync (EpicsSignal): Synchronization status.
        server_running (EpicsSignal): Server status.
        mct_status (EpicsSignal): MCT status indicator.
        scintillator_type (EpicsSignal): Scintillator material type.
        scintillator_thickness (EpicsSignal): Thickness of the scintillator.
        image_pixel_size (EpicsSignal): Size of image pixels.
        detector_pixel_size (EpicsSignal): Size of detector pixels.
        camera_objective (EpicsSignal): Camera objective configuration.
        camera_tube_length (EpicsSignal): Camera tube length.
        lens_info (MCTOpticsLensInfo): Information about the lenses.
        camera_0 (MCTOpticsCameraControl): Camera 0 control.
        camera_1 (MCTOpticsCameraControl): Camera 1 control.
    """

    # Configurable PVs
    lens_select = Cpt(EpicsSignal, "LensSelect")  # Use numbers 0-2

    camera_select = Cpt(EpicsSignal, "CameraSelect")  # Use number 0-1
    camera_selected = Cpt(EpicsSignalRO, "CameraSelected", string="true")

    cross_select = Cpt(EpicsSignal, "CrossSelect")
    sync = Cpt(EpicsSignal, "Sync", string="true")
    server_running = Cpt(EpicsSignal, "ServerRunning", string="true")
    mct_status = Cpt(EpicsSignal, "MCTStatus", string="true")

    # Scintillator Information
    scintillator_type = Cpt(EpicsSignal, "ScintillatorType")
    scintillator_thickness = Cpt(EpicsSignal, "ScintillatorThickness")

    # Image and Detector Pixel Size
    image_pixel_size = Cpt(EpicsSignal, "ImagePixelSize")
    detector_pixel_size = Cpt(EpicsSignal, "DetectorPixelSize")

    # Camera Objectives
    camera_objective = Cpt(EpicsSignal, "CameraObjective")
    camera_tube_length = Cpt(EpicsSignal, "CameraTubeLength")

    # # Lens Names
    lens_info = Cpt(MCTOpticsLensInfo, "Lens")

    # Camera Lens Positions, Offsets, & Movement
    camera_0 = Cpt(MCTOpticsCameraControl, "Camera0")
    camera_1 = Cpt(MCTOpticsCameraControl, "Camera1")