# TomoScan Bluesky Plans - Implementation Status

This document describes the Bluesky plans created to replace `tomoscan_cli.py` functionality and lists what cannot be implemented without device modifications.

## Fully Implemented Plans

These plans work with the current `TomoScan2BMDevice` without modifications:

### 1. `tomo_single_scan(tomoscan_device, *, md=None)`
**Replaces:** `tomoscan single`

Executes a complete tomography scan with dark/flat fields using current device configuration.

```python
RE(tomo_single_scan(tomoscan))
RE(tomo_single_scan(tomoscan, md={'sample': 'test_01'}))
```

### 2. `tomo_time_series_scan(tomoscan_device, num_scans, delay=0, *, in_situ_pv=None, ...)`
**Replaces:** `tomoscan single --sleep True --sleep-steps N --sleep-time T`

Executes multiple scans with optional delays and in-situ parameter ramping.

```python
# 5 scans with 30 second delay
RE(tomo_time_series_scan(tomoscan, 5, delay=30))

# With in-situ temperature ramping
from ophyd import EpicsSignal
temp_sp = EpicsSignal('2bmb:Temperature:SP', name='temp_sp')
RE(tomo_time_series_scan(tomoscan, 10, delay=60,
    in_situ_pv=temp_sp, in_situ_start=25.0, in_situ_step=5.0))
```

### 3. `tomo_configure_from_file(tomoscan_device, config_file, *, apply_now=True)`
**Replaces:** `tomoscan file` (configuration loading part)

Loads scan parameters from JSON file and applies to device.

```python
RE(tomo_configure_from_file(tomoscan, 'config.json'))
```

### 4. `tomo_export_config(tomoscan_device, output_file, *, num_configs=1)`
**Replaces:** `tomoscan init`

Exports current device configuration to JSON file.

```python
RE(tomo_export_config(tomoscan, 'current_config.json'))
RE(tomo_export_config(tomoscan, 'multi_position.json', num_configs=10))
```

## Plans Requiring Motor Arguments

These plans are implemented but require sample motors to be passed as arguments because they are not Components of the device:

### 5. `tomo_vertical_scan(tomoscan_device, sample_y_motor, start, step_size, num_steps, *, md=None)`
**Replaces:** `tomoscan vertical`

```python
from ophyd import EpicsMotor

# Create motor from PV name (you need to know the actual PV)
sample_y = EpicsMotor('2bm:m90', name='sample_y')
RE(tomo_vertical_scan(tomoscan, sample_y, 0.0, 0.5, 10))
```

### 6. `tomo_horizontal_scan(tomoscan_device, sample_x_motor, start, step_size, num_steps, *, md=None)`
**Replaces:** `tomoscan horizontal`

```python
sample_x = EpicsMotor('2bm:m89', name='sample_x')
RE(tomo_horizontal_scan(tomoscan, sample_x, 0.0, 1.0, 5))
```

### 7. `tomo_mosaic_scan(tomoscan_device, sample_x_motor, sample_y_motor, x_start, x_step, x_num, y_start, y_step, y_num, *, md=None)`
**Replaces:** `tomoscan mosaic`

```python
sample_x = EpicsMotor('2bm:m89', name='sample_x')
sample_y = EpicsMotor('2bm:m90', name='sample_y')
RE(tomo_mosaic_scan(tomoscan, sample_x, sample_y, 0.0, 1.0, 3, 0.0, 1.0, 3))
```

## Plans That CANNOT Be Implemented

### 8. Energy Scan
**Would replace:** `tomoscan energy`

**Why it cannot be implemented:**
- Requires beamline-specific energy control PVs
- Requires knowledge of which motors to adjust (Camera Z, FZP Z, FZP X, etc.)
- The CLI hardcodes PV names like `32idcTXM:mxv:c1:m6.VAL` which are specific to beamline 32-ID-C
- Each beamline has different optics and motor configurations for energy changes
- Would require a dedicated energy control Device class with beamline-specific configuration

**What would be needed:**
```python
# Example structure (beamline-specific)
class TomoScanEnergyControl(Device):
    energy_pv = Cpt(EpicsSignal, 'Energy')
    start_energy_change = Cpt(EpicsSignal, 'StartEnergyChange')
    camera_z = Cpt(EpicsMotor, '...')  # Beamline specific
    fzp_z = Cpt(EpicsMotor, '...')      # Beamline specific
    fzp_x = Cpt(EpicsMotor, '...')      # Beamline specific
    # ... other energy-dependent motors
```

## Recommended Device Improvements

To make the position-based scans cleaner and more Bluesky-native, consider adding dynamic Components to `TomoScanDevice`:

```python
from ophyd import Component as Cpt, EpicsMotor, Device

class TomoScanDevice(Device):
    # ... existing components ...

    # Sample motor PV names (existing)
    sample_x_pv_name = Cpt(EpicsSignal, 'SampleXPVName', string=True, kind='config')
    sample_y_pv_name = Cpt(EpicsSignal, 'SampleYPVName', string=True, kind='config')

    # Add actual motor components (NEW)
    # These would be dynamically connected based on the PV names above
    # Requires custom __init__ to read PV names and create motors
    # OR use ophyd's DynamicDeviceComponent
```

Alternatively, create wrapper functions that automatically create motors:

```python
def get_tomoscan_motors(tomoscan_device):
    """Create sample X/Y motors from TomoScan PV names

    Returns
    -------
    sample_x, sample_y : EpicsMotor
        The sample positioning motors
    """
    from ophyd import EpicsMotor

    x_pv = tomoscan_device.sample_x_pv_name.get()
    y_pv = tomoscan_device.sample_y_pv_name.get()

    sample_x = EpicsMotor(x_pv, name='sample_x')
    sample_y = EpicsMotor(y_pv, name='sample_y')

    return sample_x, sample_y
```

## Usage Examples

### Complete workflow using the new plans:

```python
from tomo_2bm.startup import *
from tomo_2bm.plans.tomoscan_bluesky_plans import *
from ophyd import EpicsMotor

# 1. Export current configuration as template
RE(tomo_export_config(tomoscan, 'scan_config.json'))

# 2. Run a single scan
RE(tomo_single_scan(tomoscan, md={'sample': 'calibration'}))

# 3. Run time series
RE(tomo_time_series_scan(tomoscan, 3, delay=10))

# 4. For position-based scans, create motors first
sample_x = EpicsMotor('2bm:m89', name='sample_x')  # Use actual PV
sample_y = EpicsMotor('2bm:m90', name='sample_y')  # Use actual PV

# 5. Run vertical scan
RE(tomo_vertical_scan(tomoscan, sample_y, 0.0, 0.5, 5))

# 6. Run mosaic scan
RE(tomo_mosaic_scan(tomoscan, sample_x, sample_y,
                    0.0, 1.0, 3,  # X: start, step, num
                    0.0, 0.5, 3)) # Y: start, step, num
```

## Migration from CLI to Bluesky

| CLI Command | Bluesky Plan | Notes |
|-------------|--------------|-------|
| `tomoscan single` | `tomo_single_scan()` | Direct replacement |
| `tomoscan single --sleep ...` | `tomo_time_series_scan()` | Includes in-situ parameter support |
| `tomoscan init` | `tomo_export_config()` | Creates JSON config file |
| `tomoscan vertical` | `tomo_vertical_scan()` | Requires sample_y motor argument |
| `tomoscan horizontal` | `tomo_horizontal_scan()` | Requires sample_x motor argument |
| `tomoscan mosaic` | `tomo_mosaic_scan()` | Requires both motors as arguments |
| `tomoscan file` | `tomo_configure_from_file()` + loops | Load config then run scans |
| `tomoscan energy` | NOT IMPLEMENTED | Requires beamline-specific energy control |
| `tomoscan status` | `tomoscan.summary()` | Use ophyd's built-in summary |

## Advantages of Bluesky Plans

1. **Better metadata**: All scans automatically include comprehensive metadata
2. **Data management**: Automatic integration with databroker/tiled
3. **Composability**: Plans can be combined with other Bluesky plans
4. **Interruption handling**: Proper pause/resume/abort support
5. **Live visualization**: BestEffortCallback provides real-time plots
6. **Queue integration**: Works with bluesky-queueserver out of the box
