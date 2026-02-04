"""
Bluesky plans that execute APS Data Management workflows.

Assumes ``apstools.utils.aps_data_management.dm_setup(bash_setup_file)``
has been called before accessing any function from the ``aps-dm-api``
package.  This is usually called in ``startup.py``.
"""

# FIXME: work-in-progress

from typing import Any, Optional

from apstools.devices.aps_data_management import DM_WorkflowConnector
from bluesky.utils import plan as bluesky_plan

_FOREVER = 999_999_999_999
DM_WORKFLOW_REPORTING_TIMEOUT = _FOREVER


@bluesky_plan
def tomo_single_scan_dm(
    *,  # kwargs-only (for queueserver use)
    # TODO: experimentName: str = "",   # Name of APS DM experiment
    workflow: str = "",  # Name of APS DM workflow
    filePath: str = "",  # path to APS DM experiment files
    dm_kwargs,: Optional[dict[atr, Any]] = {},  # _Any_ other kwargs for the DM workflow.
    md: Optional[dict[atr, Any]] = {},
):
    """Run the tomo_single_scan() plan, then start a DM workflow."""
    from tomo_2bm.plans.tomo_single import tomo_single_scan

    # Add DM metadata to bluesky's metadata
    _md = dict(
        workflow=workflow,
        filePath=filePath,
    )
    _md.update(dm_kwargs)
    _md.update(md or {})

    dm_workflow = DM_WorkflowConnector(name="dm_workflow", labels=["DM"])
    dm.concise_reporting.put(True)  # brief DM workflow reports
    dm.reporting_period.put(_FOREVER)  # (effectively) disable periodic DM workflow reporting

    # Run tomoscan
    yield from tomo_single_scan(md=_md)

    # Start APS DM workflow, don't wait for it to finish.
    yield from dm_workflow.run_as_plan(
        workflow=workflow,
        filePath=filePath,
        wait=False,  # TODO: confirm: start the workflow, don't wait for it to finish
        timeout=DM_WORKFLOW_REPORTING_TIMEOUT,
        **dm_kwargs,
    )
