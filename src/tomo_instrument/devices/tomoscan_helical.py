"""Helical scan ophyd Device class for tomoscan Bluesky integration

This module provides the TomoScanHelicalDevice class that extends
PSO fly-scan with helical vertical motion capability.
"""


from ophyd import Component as Cpt
from ophyd import EpicsSignal

from .tomoscan_pso import TomoScanPSODevice


class TomoScanHelicalDevice(TomoScanPSODevice):
    """ophyd Device for helical tomography scanning

    This class extends TomoScanPSODevice to add helical scanning capability,
    where the sample moves vertically (Y direction) during rotation to
    increase the effective field of view.

    The helical motion is synchronized with the rotation so that the sample
    moves a specified number of pixels per 360-degree rotation.
    """

    # Helical scan configuration
    scan_type = Cpt(EpicsSignal, 'ScanType', string=True, kind='config')
    pixels_y_per_360deg = Cpt(EpicsSignal, 'PixelsYPer360Deg', kind='config')
