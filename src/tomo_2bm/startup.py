"""
Start Bluesky Data Acquisition sessions of all kinds.

Includes:

* Python script
* IPython console
* Jupyter notebook
* Bluesky queueserver
"""

# Standard Library Imports
import logging
from pathlib import Path

# Core Functions
from apsbits.core.best_effort_init import init_bec_peaks
from apsbits.core.catalog_init import init_catalog
from apsbits.core.instrument_init import init_instrument
from apsbits.core.instrument_init import make_devices
from apsbits.core.run_engine_init import init_RE

# Utility functions
from apsbits.utils.aps_functions import host_on_aps_subnet
from apsbits.utils.baseline_setup import setup_baseline_stream

# Configuration functions
from apsbits.utils.config_loaders import load_config
from apsbits.utils.helper_functions import register_bluesky_magics
from apsbits.utils.helper_functions import running_in_queueserver

from apstools.utils.aps_data_management import dm_setup as aps_dm_setup

# Configuration block
# Get the path to the instrument package
# Load configuration to be used by the instrument.
instrument_path = Path(__file__).parent
iconfig_path = instrument_path / "configs" / "iconfig.yml"
iconfig = load_config(iconfig_path)

logger = logging.getLogger(__name__)
logger.info("Starting Instrument with iconfig: %s", iconfig_path)

# initialize instrument
instrument, oregistry = init_instrument("guarneri")

# Discard oregistry items loaded above.
oregistry.clear()

# Setup APS Data Management
aps_dm_setup(iconfig.get("DM_SETUP_FILE"))

# Command-line tools, such as %wa, %ct, ...
register_bluesky_magics()

# Bluesky initialization block
bec, peaks = init_bec_peaks(iconfig)
cat = init_catalog(iconfig)
RE, sd = init_RE(iconfig, subscribers=[bec, cat])

# Optional Nexus callback block
# delete this block if not using Nexus
if iconfig.get("NEXUS_DATA_FILES", {}).get("ENABLE", False):
    from .callbacks.demo_nexus_callback import nxwriter_init

    nxwriter = nxwriter_init(RE)

# These imports must come after the above setup.
# Queue server block
if running_in_queueserver():
    ### To make all the standard plans available in QS, import by '*', otherwise import
    ### plan by plan.
    from apstools.plans import lineup2  # noqa: F401
    from bluesky.plans import *  # noqa: F403
else:
    # Import bluesky plans and stubs with prefixes set by common conventions.
    # The apstools plans and utils are imported by '*'.
    from apstools.plans import *  # noqa: F403
    from apstools.utils import *  # noqa: F403
    from bluesky import plan_stubs as bps  # noqa: F401
    from bluesky import plans as bp  # noqa: F401

# Experiment specific logic, device and plan loading. # Create the devices.
make_devices(clear=False, file="devices.yml", device_manager=instrument)

# if host_on_aps_subnet():
#     make_devices(clear=False, file="devices_aps_only.yml", device_manager=instrument)

# Setup baseline stream with connect=False is default
# Devices with the label 'baseline' will be added to the baseline stream.
setup_baseline_stream(sd, oregistry, connect=False)

from .plans.plans_with_dm import tomo_single_scan_dm  # noqa: E402, F401
from .plans.sim_plans import sim_count_plan  # noqa: E402, F401
from .plans.sim_plans import sim_print_plan  # noqa: E402, F401
from .plans.sim_plans import sim_rel_scan_plan  # noqa: E402, F401
from .plans.tomo_single import tomo_single_scan  # noqa: E402, F401
