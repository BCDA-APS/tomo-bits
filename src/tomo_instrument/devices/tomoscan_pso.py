"""PSO-based ophyd Device class for tomoscan Bluesky integration

This module provides the TomoScanPSODevice class that implements fly-scan
tomography using Aerotech PSO (Position Synchronized Output) triggering.
"""

from ophyd import Component as Cpt
from ophyd import EpicsSignal
from ophyd import EpicsSignalRO

from .tomoscan_base import TomoScanDevice


class TomoScanPSODevice(TomoScanDevice):
    """ophyd Device for tomography scanning using Aerotech PSO triggering

    This class extends TomoScanDevice to add PSO fly-scan capabilities.

    Attributes
    ----------
    pso : PSOController
        The PSO controller device
    motor_speed : float
        Calculated motor speed for the scan
    rotation_start_new : float
        Adjusted rotation start position accounting for taxi distance
    """

    # PSO-specific configuration
    pso_model = Cpt(EpicsSignal, 'PSOControllerModel', string=True, kind='config')
    pso_axis = Cpt(EpicsSignal, 'PSOAxisName', string=True, kind='config')
    pso_counts_per_rotation = Cpt(EpicsSignal, 'PSOCountsPerRotation', kind='config')
    pso_encoder_counts_per_step = Cpt(EpicsSignal, 'PSOEncoderCountsPerStep', kind='config')
    pso_start_taxi = Cpt(EpicsSignal, 'PSOStartTaxi', kind='config')
    pso_end_taxi = Cpt(EpicsSignal, 'PSOEndTaxi', kind='config')
    pso_pulse_width = Cpt(EpicsSignal, 'PSOPulseWidth', kind='config')
    pso_encoder_input = Cpt(EpicsSignal, 'PSOEncoderInput', kind='config')
    program_pso_flag = Cpt(EpicsSignal, 'ProgramPSO', string=True, kind='config')

    # PSO command interface
    pso_command_out = Cpt(EpicsSignal, 'PSOCommand.BOUT', string=True, kind='omitted')
    pso_command_in = Cpt(EpicsSignalRO, 'PSOCommand.BINP', string=True, kind='omitted')
