"""Bluesky plans replacing tomoscan_cli.py functionality

This module provides Bluesky-compatible plans that replace the command-line
interface functionality from tomoscan_cli.py, using the TomoScan2BMDevice.

IMPORTANT LIMITATIONS:
----------------------
The following plans CANNOT be implemented without additional device components:

1. Vertical scan - Requires sample Y motor as a Component in the device
2. Horizontal scan - Requires sample X motor as a Component in the device
3. Mosaic scan - Requires both sample X and Y motors as Components
4. Energy scan - Requires energy PV and beamline-specific motor Components

The device currently only has sample_x_pv_name and sample_y_pv_name which store
PV names as strings, not actual ophyd motor objects. To implement position-based
scans, the device needs to be extended with:
    sample_x = Cpt(EpicsMotor, dynamic=True)  # Read from sample_x_pv_name
    sample_y = Cpt(EpicsMotor, dynamic=True)  # Read from sample_y_pv_name

See: https://nsls-ii.github.io/ophyd/signals.html#dynamic-signals
"""

import json
import time
from pathlib import Path

import bluesky.plan_stubs as bps
import bluesky.preprocessors as bpp
import numpy as np


def tomo_single_scan(tomoscan_device, *, md=None):
    """Single tomography scan

    Equivalent to: tomoscan single

    Executes a complete tomography scan including dark fields, flat fields,
    and projections using the current device configuration.

    Parameters
    ----------
    tomoscan_device : TomoScan2BMDevice
        The tomoscan ophyd device
    md : dict, optional
        Additional metadata to include in the run

    Yields
    ------
    Msg
        Bluesky messages for the scan

    Examples
    --------
    >>> RE(tomo_single_scan(tomoscan))
    >>> RE(tomo_single_scan(tomoscan, md={'sample': 'test_01'}))
    """
    _md = {
        'plan_name': 'tomo_single_scan',
        'scan_type': 'single',
        'detectors': [tomoscan_device.name],
    }
    _md.update(md or {})

    @bpp.stage_decorator([tomoscan_device])
    @bpp.run_decorator(md=_md)
    def inner():
        # Check that server is running
        server_running = yield from bps.rd(tomoscan_device.server_running)
        if not server_running:
            raise RuntimeError(f"TomoScan server is not running")

        scan_status = yield from bps.rd(tomoscan_device.scan_status)
        if scan_status != 'Scan complete':
            raise RuntimeError(
                f"TomoScan is busy (status: {scan_status}). "
                "Wait for current scan to complete."
            )

        # Trigger the scan
        yield from bps.trigger(tomoscan_device, wait=True)

    yield from inner()


def tomo_time_series_scan(tomoscan_device, num_scans, delay=0, *,
                          in_situ_pv=None, in_situ_start=None,
                          in_situ_step=None, md=None):
    """Time series of tomography scans with optional delay

    Equivalent to: tomoscan single --sleep True --sleep-steps N --sleep-time T

    Executes multiple tomography scans with an optional delay between them.
    Optionally sets an in-situ process variable between scans.

    Parameters
    ----------
    tomoscan_device : TomoScan2BMDevice
        The tomoscan ophyd device
    num_scans : int
        Number of scans to execute
    delay : float, optional
        Delay time between scans in seconds (default: 0)
    in_situ_pv : ophyd.Signal, optional
        Ophyd signal for in-situ parameter control
    in_situ_start : float, optional
        Starting value for in-situ parameter
    in_situ_step : float, optional
        Step size for in-situ parameter
    md : dict, optional
        Additional metadata

    Yields
    ------
    Msg
        Bluesky messages

    Examples
    --------
    >>> # 5 scans with 30 second delay
    >>> RE(tomo_time_series_scan(tomoscan, 5, delay=30))

    >>> # With in-situ temperature ramping
    >>> from ophyd import EpicsSignal
    >>> temp_setpoint = EpicsSignal('2bmb:Temperature:SP', name='temp_sp')
    >>> RE(tomo_time_series_scan(tomoscan, 10, delay=60,
    ...     in_situ_pv=temp_setpoint, in_situ_start=25.0, in_situ_step=5.0))
    """
    _md = {
        'plan_name': 'tomo_time_series_scan',
        'num_scans': num_scans,
        'inter_scan_delay': delay,
        'in_situ_enabled': in_situ_pv is not None,
    }
    _md.update(md or {})

    start_time = time.time()

    for i in range(num_scans):
        scan_md = _md.copy()
        scan_md['time_series_index'] = i

        if in_situ_pv is not None and in_situ_start is not None:
            in_situ_value = in_situ_start + i * (in_situ_step or 0)
            scan_md['in_situ_setpoint'] = in_situ_value
            yield from bps.mv(in_situ_pv, in_situ_value)
            # Could add readback verification here if needed

        # Run the scan
        yield from tomo_single_scan(tomoscan_device, md=scan_md)

        # Delay before next scan (except after the last one)
        if i < num_scans - 1 and delay > 0:
            yield from bps.sleep(delay)

    elapsed = (time.time() - start_time) / 60.0
    print(f"Time series complete. Total time: {elapsed:.1f} minutes")


def tomo_configure_from_file(tomoscan_device, config_file, *, apply_now=True):
    """Load scan parameters from JSON configuration file

    Equivalent to: tomoscan init / tomoscan file (configuration loading part)

    Loads scan configuration from a JSON file and optionally applies it to the
    device. The JSON file should contain keys matching the device signal names.

    Parameters
    ----------
    tomoscan_device : TomoScan2BMDevice
        The tomoscan ophyd device
    config_file : str or Path
        Path to JSON configuration file
    apply_now : bool, optional
        If True, immediately apply settings to device (default: True)
        If False, just return the configuration dictionary

    Yields
    ------
    Msg
        Bluesky messages (only if apply_now=True)

    Returns
    -------
    dict
        Configuration dictionary loaded from file

    Examples
    --------
    >>> # Load and apply configuration
    >>> RE(tomo_configure_from_file(tomoscan, 'config.json'))

    >>> # Just load without applying
    >>> config = tomo_configure_from_file(tomoscan, 'config.json', apply_now=False)
    """
    config_path = Path(config_file)

    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_file}")

    with open(config_path) as f:
        try:
            config = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {config_file}: {e}")

    # Map of JSON keys to device signal names
    signal_map = {
        'RotationStart': 'rotation_start',
        'RotationStep': 'rotation_step',
        'NumAngles': 'num_angles',
        'ReturnRotation': 'return_rotation',
        'NumDarkFields': 'num_dark_fields',
        'DarkFieldMode': 'dark_field_mode',
        'DarkFieldValue': 'dark_field_value',
        'NumFlatFields': 'num_flat_fields',
        'FlatFieldAxis': 'flat_field_axis',
        'FlatFieldMode': 'flat_field_mode',
        'FlatFieldValue': 'flat_field_value',
        'FlatExposureTime': 'flat_exposure_time',
        'DifferentFlatExposure': 'different_flat_exposure',
        'SampleInX': 'sample_in_x',
        'SampleOutX': 'sample_out_x',
        'SampleInY': 'sample_in_y',
        'SampleOutY': 'sample_out_y',
        'SampleOutAngleEnable': 'sample_out_angle_enable',
        'SampleOutAngle': 'sample_out_angle',
        'ExposureTime': 'exposure_time',
        'SampleName': 'sample_name',
    }

    # Add helical scan parameters if present
    if hasattr(tomoscan_device, 'scan_type'):
        signal_map['ScanType'] = 'scan_type'
    if hasattr(tomoscan_device, 'flip_stitch'):
        signal_map['FlipStitch'] = 'flip_stitch'

    if not apply_now:
        return config

    # Apply configuration to device
    def set_params():
        for json_key, signal_name in signal_map.items():
            if json_key in config and hasattr(tomoscan_device, signal_name):
                signal = getattr(tomoscan_device, signal_name)
                value = config[json_key]
                yield from bps.mv(signal, value)

    yield from set_params()
    return config


def tomo_export_config(tomoscan_device, output_file, *, num_configs=1):
    """Export current device configuration to JSON file

    Equivalent to: tomoscan init

    Reads the current scan parameters from the device and writes them to a
    JSON file. Can create multiple identical configuration entries for batch
    processing.

    Parameters
    ----------
    tomoscan_device : TomoScan2BMDevice
        The tomoscan ophyd device
    output_file : str or Path
        Path to output JSON file
    num_configs : int, optional
        Number of configuration entries to create (default: 1)
        Useful for creating templates for multi-position scans

    Yields
    ------
    Msg
        Bluesky messages for reading device values

    Examples
    --------
    >>> # Export current configuration
    >>> RE(tomo_export_config(tomoscan, 'current_config.json'))

    >>> # Create template with 10 entries for multi-position scan
    >>> RE(tomo_export_config(tomoscan, 'multi_position.json', num_configs=10))
    """
    output_path = Path(output_file)

    if output_path.exists():
        raise FileExistsError(
            f"{output_file} already exists. Delete it or choose a different name."
        )

    # Read current values from device
    def read_config():
        config = {}

        # Read all relevant parameters
        config['RotationStart'] = yield from bps.rd(tomoscan_device.rotation_start)
        config['RotationStep'] = yield from bps.rd(tomoscan_device.rotation_step)
        config['NumAngles'] = yield from bps.rd(tomoscan_device.num_angles)
        config['ReturnRotation'] = yield from bps.rd(tomoscan_device.return_rotation)

        config['NumDarkFields'] = yield from bps.rd(tomoscan_device.num_dark_fields)
        config['DarkFieldMode'] = yield from bps.rd(tomoscan_device.dark_field_mode)
        config['DarkFieldValue'] = yield from bps.rd(tomoscan_device.dark_field_value)

        config['NumFlatFields'] = yield from bps.rd(tomoscan_device.num_flat_fields)
        config['FlatFieldAxis'] = yield from bps.rd(tomoscan_device.flat_field_axis)
        config['FlatFieldMode'] = yield from bps.rd(tomoscan_device.flat_field_mode)
        config['FlatFieldValue'] = yield from bps.rd(tomoscan_device.flat_field_value)
        config['FlatExposureTime'] = yield from bps.rd(tomoscan_device.flat_exposure_time)
        config['DifferentFlatExposure'] = yield from bps.rd(tomoscan_device.different_flat_exposure)

        config['SampleInX'] = yield from bps.rd(tomoscan_device.sample_in_x)
        config['SampleOutX'] = yield from bps.rd(tomoscan_device.sample_out_x)
        config['SampleInY'] = yield from bps.rd(tomoscan_device.sample_in_y)
        config['SampleOutY'] = yield from bps.rd(tomoscan_device.sample_out_y)
        config['SampleOutAngleEnable'] = yield from bps.rd(tomoscan_device.sample_out_angle_enable)
        config['SampleOutAngle'] = yield from bps.rd(tomoscan_device.sample_out_angle)

        config['ExposureTime'] = yield from bps.rd(tomoscan_device.exposure_time)

        # Add helical scan parameters if available
        if hasattr(tomoscan_device, 'scan_type'):
            config['ScanType'] = yield from bps.rd(tomoscan_device.scan_type)

        # Placeholder for sample positions (to be filled manually)
        config['SampleX'] = 0.0
        config['SampleY'] = 0.0

        return config

    # This is a bit tricky - we need to read the values then write the file
    # We'll use a closure to capture the config
    configs_dict = {}
    base_config = {}

    def inner():
        nonlocal base_config
        base_config = yield from read_config()

    yield from inner()

    # Create multiple entries if requested
    for i in range(num_configs):
        key = str(i).zfill(3)
        configs_dict[key] = base_config.copy()

    # Write to file
    with open(output_path, 'w') as f:
        json.dump(configs_dict, f, indent=4, sort_keys=True)

    print(f"Configuration exported to {output_file}")
    if num_configs > 1:
        print(f"Created {num_configs} identical entries.")
        print(f"Customize SampleX and SampleY values for each position in {output_file}")


# =============================================================================
# Plans that CANNOT be implemented without device modifications
# =============================================================================

def tomo_vertical_scan(tomoscan_device, sample_y_motor, start, step_size,
                      num_steps, *, md=None):
    """Vertical tomography scan - REQUIRES sample_y_motor

    Equivalent to: tomoscan vertical

    NOTE: This plan requires the sample Y motor to be passed as an argument
    because it is not included as a Component in the TomoScan2BMDevice.

    To make this work, you need to:
    1. Create an EpicsMotor for the sample Y axis, OR
    2. Extend the device class to include sample_y as a Component

    Parameters
    ----------
    tomoscan_device : TomoScan2BMDevice
        The tomoscan ophyd device
    sample_y_motor : EpicsMotor
        The sample Y positioning motor
    start : float
        Starting Y position (mm)
    step_size : float
        Step size in Y (mm)
    num_steps : int
        Number of Y positions to scan
    md : dict, optional
        Additional metadata

    Yields
    ------
    Msg
        Bluesky messages

    Examples
    --------
    >>> from ophyd import EpicsMotor
    >>> sample_y = EpicsMotor('2bm:m1', name='sample_y')
    >>> RE(tomo_vertical_scan(tomoscan, sample_y, 0.0, 0.5, 10))
    """
    _md = {
        'plan_name': 'tomo_vertical_scan',
        'scan_type': 'vertical',
        'y_start': start,
        'y_step': step_size,
        'y_num': num_steps,
    }
    _md.update(md or {})

    # Determine which PV to move based on flat field axis
    flat_field_axis = yield from bps.rd(tomoscan_device.flat_field_axis)
    flat_field_mode = yield from bps.rd(tomoscan_device.flat_field_mode)

    # If flat field uses X axis or is disabled, move the main Y motor
    # Otherwise, we'd need to set SampleInY (which is a setpoint, not a motor)
    if flat_field_axis == 'X' or flat_field_mode == 'None':
        motor_to_move = sample_y_motor
    else:
        # In this case, the scan should set sample_in_y and the IOC handles movement
        # This requires a different approach
        print("Warning: FlatFieldAxis is Y, using sample_in_y setpoint")
        motor_to_move = None

    start_time = time.time()

    positions = np.linspace(start, start + step_size * num_steps, num_steps, endpoint=False)
    print(f"Vertical positions (mm): {positions}")

    for i, y_pos in enumerate(positions):
        scan_md = _md.copy()
        scan_md['y_position'] = y_pos
        scan_md['position_index'] = i

        if motor_to_move is not None:
            yield from bps.mv(motor_to_move, y_pos)
        else:
            yield from bps.mv(tomoscan_device.sample_in_y, y_pos)

        yield from tomo_single_scan(tomoscan_device, md=scan_md)

    elapsed = (time.time() - start_time) / 60.0
    print(f"Vertical scan complete. Total time: {elapsed:.1f} minutes")


def tomo_horizontal_scan(tomoscan_device, sample_x_motor, start, step_size,
                         num_steps, *, md=None):
    """Horizontal tomography scan - REQUIRES sample_x_motor

    Equivalent to: tomoscan horizontal

    NOTE: This plan requires the sample X motor to be passed as an argument
    because it is not included as a Component in the TomoScan2BMDevice.

    Parameters
    ----------
    tomoscan_device : TomoScan2BMDevice
        The tomoscan ophyd device
    sample_x_motor : EpicsMotor
        The sample X positioning motor
    start : float
        Starting X position (mm)
    step_size : float
        Step size in X (mm)
    num_steps : int
        Number of X positions to scan
    md : dict, optional
        Additional metadata

    Yields
    ------
    Msg
        Bluesky messages

    Examples
    --------
    >>> from ophyd import EpicsMotor
    >>> sample_x = EpicsMotor('2bm:m2', name='sample_x')
    >>> RE(tomo_horizontal_scan(tomoscan, sample_x, 0.0, 1.0, 5))
    """
    _md = {
        'plan_name': 'tomo_horizontal_scan',
        'scan_type': 'horizontal',
        'x_start': start,
        'x_step': step_size,
        'x_num': num_steps,
    }
    _md.update(md or {})

    flat_field_axis = yield from bps.rd(tomoscan_device.flat_field_axis)
    flat_field_mode = yield from bps.rd(tomoscan_device.flat_field_mode)

    if flat_field_axis == 'Y' or flat_field_mode == 'None':
        motor_to_move = sample_x_motor
    else:
        print("Warning: FlatFieldAxis is X, using sample_in_x setpoint")
        motor_to_move = None

    start_time = time.time()

    positions = np.linspace(start, start + step_size * num_steps, num_steps, endpoint=False)
    print(f"Horizontal positions (mm): {positions}")

    for i, x_pos in enumerate(positions):
        scan_md = _md.copy()
        scan_md['x_position'] = x_pos
        scan_md['position_index'] = i

        if motor_to_move is not None:
            yield from bps.mv(motor_to_move, x_pos)
        else:
            yield from bps.mv(tomoscan_device.sample_in_x, x_pos)

        yield from tomo_single_scan(tomoscan_device, md=scan_md)

    elapsed = (time.time() - start_time) / 60.0
    print(f"Horizontal scan complete. Total time: {elapsed:.1f} minutes")


def tomo_mosaic_scan(tomoscan_device, sample_x_motor, sample_y_motor,
                    x_start, x_step, x_num, y_start, y_step, y_num, *, md=None):
    """Mosaic tomography scan - REQUIRES sample_x_motor and sample_y_motor

    Equivalent to: tomoscan mosaic

    NOTE: This plan requires both sample X and Y motors to be passed as arguments.

    Parameters
    ----------
    tomoscan_device : TomoScan2BMDevice
        The tomoscan ophyd device
    sample_x_motor : EpicsMotor
        The sample X positioning motor
    sample_y_motor : EpicsMotor
        The sample Y positioning motor
    x_start : float
        Starting X position (mm)
    x_step : float
        Step size in X (mm)
    x_num : int
        Number of X positions
    y_start : float
        Starting Y position (mm)
    y_step : float
        Step size in Y (mm)
    y_num : int
        Number of Y positions
    md : dict, optional
        Additional metadata

    Yields
    ------
    Msg
        Bluesky messages

    Examples
    --------
    >>> from ophyd import EpicsMotor
    >>> sample_x = EpicsMotor('2bm:m2', name='sample_x')
    >>> sample_y = EpicsMotor('2bm:m1', name='sample_y')
    >>> # 3x3 grid scan
    >>> RE(tomo_mosaic_scan(tomoscan, sample_x, sample_y,
    ...                     0.0, 1.0, 3, 0.0, 1.0, 3))
    """
    _md = {
        'plan_name': 'tomo_mosaic_scan',
        'scan_type': 'mosaic',
        'grid_shape': (y_num, x_num),
        'x_range': (x_start, x_start + x_step * x_num),
        'y_range': (y_start, y_start + y_step * y_num),
    }
    _md.update(md or {})

    flat_field_axis = yield from bps.rd(tomoscan_device.flat_field_axis)
    flat_field_mode = yield from bps.rd(tomoscan_device.flat_field_mode)

    start_time = time.time()

    y_positions = np.linspace(y_start, y_start + y_step * y_num, y_num, endpoint=False)
    x_positions = np.linspace(x_start, x_start + x_step * x_num, x_num, endpoint=False)

    print(f"Vertical positions (mm): {y_positions}")
    print(f"Horizontal positions (mm): {x_positions}")

    position_index = 0
    for i, y_pos in enumerate(y_positions):
        # Move Y
        if flat_field_axis == 'X' or flat_field_mode == 'None':
            yield from bps.mv(sample_y_motor, y_pos)
        else:
            yield from bps.mv(tomoscan_device.sample_in_y, y_pos)

        for j, x_pos in enumerate(x_positions):
            scan_md = _md.copy()
            scan_md['grid_position'] = (i, j)
            scan_md['x_position'] = x_pos
            scan_md['y_position'] = y_pos
            scan_md['position_index'] = position_index

            # Move X
            if flat_field_axis == 'Y' or flat_field_mode == 'None':
                yield from bps.mv(sample_x_motor, x_pos)
            else:
                yield from bps.mv(tomoscan_device.sample_in_x, x_pos)

            yield from tomo_single_scan(tomoscan_device, md=scan_md)
            position_index += 1

    elapsed = (time.time() - start_time) / 60.0
    print(f"Mosaic scan complete. Total time: {elapsed:.1f} minutes")


# Energy scan cannot be implemented without knowing the specific energy control
# PVs and beamline motor configuration. The CLI hardcodes specific PV names
# like '32idcTXM:mxv:c1:m6.VAL' which are beamline-specific.
