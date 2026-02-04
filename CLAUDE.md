# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository (`tomo-bits`) contains a Bluesky-based data acquisition instrument for tomography scanning at APS (Advanced Photon Source) beamlines. It provides both a generic tomography framework (`tomo_instrument`) and a beamline-specific implementation for 2-BM (`tomo_2bm`).

## Development Setup

### Initial Installation

```bash
export ENV_NAME=tomo_bits
conda create -y -n $ENV_NAME python=3.11 pyepics
conda activate $ENV_NAME
pip install -e ".[all]"
```

### Testing

```bash
# Run all tests
pytest -vvv --lf ./src

# Run tests for a specific module
pytest -vvv ./src/tomo_2bm/
```

### Code Quality

```bash
# Format code (line length: 88 for ruff, 115 for black)
ruff format .

# Lint code
ruff check .

# Type checking
mypy src/
```

### Documentation

```bash
# Build documentation (requires pandoc: conda install conda-forge::pandoc)
make -C docs clean html

# View documentation
BROWSER ./docs/build/html/index.html &
```

## Architecture

### Package Structure

The codebase is organized into two main packages:

1. **`tomo_instrument`** - Generic tomography framework providing base classes and plans
2. **`tomo_2bm`** - Beamline-specific implementation for APS sector 2-BM

### Device Inheritance Hierarchy

The tomoscan devices follow a clear inheritance chain that adds capabilities at each level:

```
TomoScanDevice (base)
  └── TomoScanPSODevice (adds Aerotech PSO fly-scan triggering)
      └── TomoScanHelicalDevice (adds helical vertical motion)
          └── TomoScan2BMDevice (adds 2-BM beamline specifics)
```

- **TomoScanDevice** (`tomo_instrument/devices/tomoscan_base.py`): Core tomography scanning with EPICS PVs for rotation, dark/flat fields, file I/O, and shutter control
- **TomoScanPSODevice** (`tomo_instrument/devices/tomoscan_pso.py`): Adds Position Synchronized Output (PSO) for continuous fly-scan acquisition
- **TomoScanHelicalDevice** (`tomo_instrument/devices/tomoscan_helical.py`): Adds helical scanning where sample moves vertically during rotation
- **TomoScan2BMDevice** (`tomo_2bm/devices/tomoscan_2bm.py`): Adds dual camera support (mctOptics), front-end shutters, and data transfer features

### Startup Sequence

The instrument initialization follows a specific order (see `tomo_2bm/startup.py`):

1. Load configuration from `configs/iconfig.yml`
2. Initialize instrument registry using apsbits (`init_instrument`)
3. Register Bluesky magics for IPython
4. Initialize Bluesky components: BEC (best-effort callback), catalog, RunEngine
5. Optional: Initialize NeXus/SPEC file writers if enabled
6. Import Bluesky plans (different imports for queueserver vs console)
7. Create devices from `configs/devices.yml` using apsbits device manager
8. Setup baseline stream for devices with "baseline" label
9. Import beamline-specific plans

### Configuration System

Configuration is managed through YAML files in `configs/`:

- **`iconfig.yml`**: Main instrument configuration (RunEngine metadata, databroker, file formats, EPICS timeouts)
- **`devices.yml`**: Device definitions using Guarneri-style YAML format (device class, name, prefix, labels)
- **`devices_aps_only.yml`**: Additional devices only loaded when on APS subnet

Devices are created using apsbits' `make_devices()` function which parses the YAML and instantiates ophyd devices.

### Bluesky Plans

Tomography plans are in `tomo_instrument/plans/tomoscan_plans.py`:

- **`tomo_fly_scan()`**: Complete tomo scan with dark/flat fields
- **`tomo_step_scan()`**: Step-scan mode variant
- **`tomo_multi_sample_scan()`**: Scan multiple XY positions
- **`tomo_grid_scan()`**: Rectangular grid of positions
- **`tomo_time_series()`**: Time-series scans with delay
- **`tomo_dark_flat_only()`**: Calibration-only (no projections)
- **`tomo_scan_with_shutter_control()`**: Explicit shutter control
- **`tomo_configuration_scan()`**: Load scan parameters from JSON file

All plans follow standard Bluesky protocols: stage/unstage devices, open/close runs, and use `bps.trigger()` for scan execution.

## Running the Instrument

### IPython Console

```python
# Start IPython and run:
from tomo_2bm.startup import *

# Run demo plans
RE(sim_print_plan())
RE(sim_count_plan())
RE(sim_rel_scan_plan())

# Run tomography scan
RE(tomo_fly_scan(tomoscan, md={'sample': 'test_sample'}))
```

### Jupyter Notebook

```python
from tomo_2bm.startup import *
# Then use RE() to run plans as above
```

### Queueserver

The queueserver allows remote queue management of the RunEngine:

```bash
# Start/restart queueserver host
./qserver/qs_host.sh restart

# Check status
./qserver/qs_host.sh status

# Launch GUI client
queue-monitor &
```

The queueserver host script (`qserver/qs_host.sh`) supports: `start`, `stop`, `restart`, `status`, `checkup`, `console`, `run`.

Configuration: `qserver/qs-config.yml` (see Bluesky queueserver docs for details)

## Development Notes

### Apsbits Dependency

This package heavily uses `apsbits` for:
- Core initialization functions (`init_RE`, `init_instrument`, `init_catalog`, `init_bec_peaks`)
- Device creation and management (`make_devices`)
- Configuration loading (`load_config`)
- Utility functions (`register_bluesky_magics`, `running_in_queueserver`, `setup_baseline_stream`)

### Working with Devices

When adding or modifying devices:
1. Define ophyd Device classes in `tomo_instrument/devices/` (generic) or `tomo_2bm/devices/` (beamline-specific)
2. Add device instantiation to `configs/devices.yml` using the format: class path, name, prefix, labels
3. Labels control behavior: "baseline" adds to baseline stream, "detectors" marks as detector, etc.
4. Use `kind` parameter on Components: "config" (saved once), "normal" (read each scan), "omitted" (not read)

### EPICS PV Naming

The TomoScan IOC PVs follow the pattern: `{prefix}{PVName}` where prefix is set in devices.yml (e.g., "2bm:Tomoscan:"). The base class defines standard PV suffixes like "RotationStart", "NumAngles", "ScanStatus", etc.

### Testing Approach

Tests should be placed in the same directory as the module being tested with a `test_` prefix. The pytest configuration uses `--import-mode=importlib` for proper module imports.

## Code Style

- Line length: 88 characters (ruff), 115 for black
- Use ruff for linting and formatting
- Import style: Single-line imports enforced by ruff (`force-single-line = true`)
- Python target: 3.11+
- Docstrings required for all public modules, classes, methods, and functions (D100-D107)

## Common Pitfalls

1. **Import order in startup.py**: Plans and device-specific imports must come AFTER RunEngine initialization
2. **Device labels**: Labels in devices.yml control automatic registration (baseline, detectors, etc.)
3. **Queueserver imports**: Uses different import strategy (star imports) vs console sessions (prefixed imports: bp, bps)
4. **File paths**: qserver directory should NOT be inside the installed package (may be read-only)
5. **EPICS timeouts**: Configured in iconfig.yml under OPHYD.TIMEOUTS
