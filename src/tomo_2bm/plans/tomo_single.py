"""
Bluesky plan replacing tomoscan_cli.py tomo_single_scan functionality
"""

import bluesky.plan_stubs as bps
import bluesky.preprocessors as bpp
from apsbits.core.instrument_init import with_registry


@with_registry
def tomo_single_scan(oregistry, *, md=None):
    """Single tomography scan

    Equivalent to: tomoscan single

    Executes a complete tomography scan including dark fields, flat fields,
    and projections.

    Parameters
    ----------
    oregistry : dict
        Object registry containing the tomoscan device
    md : dict, optional
        Additional metadata to include in the run

    Yields
    ------
    Msg
        Bluesky messages for the scan

    Examples
    --------
    >>> RE(tomo_single_scan())
    """
    tomoscan = oregistry["tomoscan"]

    _md = {
        'plan_name': 'tomo_single_scan',
        'scan_type': 'single',
        'detectors': [tomoscan.name],
    }
    _md.update(md or {})

    @bpp.stage_decorator([tomoscan])
    @bpp.run_decorator(md=_md)
    def inner():
        # Check that server is running
        server_running = yield from bps.rd(tomoscan.server_running)
        if not server_running:
            raise RuntimeError(
                f"TomoScan server is not running at {tomoscan.prefix}"
            )

        # Check scan status - must be idle/complete to start new scan
        scan_status = yield from bps.rd(tomoscan.scan_status)
        if scan_status != 'Scan complete':
            raise RuntimeError(
                f"TomoScan is busy (status: {scan_status}). "
                "Wait for current scan to complete."
            )

        # Set scan type to 'Single'
        yield from bps.mv(tomoscan.scan_type, 'Single')

        # Check if in testing mode
        testing_mode = yield from bps.rd(tomoscan.testing)
        if testing_mode:
            print("Testing mode enabled - scan would run here")
        else:
            # Trigger the scan by setting StartScan to 1
            # The timeout is set to 360000 seconds (100 hours) to handle long scans
            print("Starting tomography scan...")
            yield from bps.mv(tomoscan.start_scan, 1)

        # Reset scan type back to 'Single' (as done in CLI)
        yield from bps.mv(tomoscan.scan_type, 'Single')

    yield from inner()
