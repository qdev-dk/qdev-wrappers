import logging
import numpy as np
from qcodes.instrument.base import Instrument
import math
from qdev_wrappers.customised_instruments.composite_instruments.parametric_waveform_analyser.readout_drive_channel import ReadoutChannel, DriveChannel
from qdev_wrappers.customised_instruments.composite_instruments.parametric_waveform_analyser.sequence_channel import SequenceChannel

logger = logging.getLogger(__name__)


class ParametricWaveformAnalyser(Instrument):
    """
    The PWA represents a composite instrument. It comprises a parametric
    sequencer, an Alazar card, an alazar controller instrument, a heterodyne
    source and a qubit source. The idea is that the parametric sequencer is
    used to sideband the heterodyne and qubit sources to create a drive and
    readout tone per qubit and also optionally to vary some parameter in a
    sequence. The setpoints of this sequence and the demodulation frequencies
    calculated from the heterodyne source demodulation frequency and the
    parametric sequencer sideband frequencies are communicated to the Alazar
    controller.
    """

    def __init__(self,
                 name: str,
                 sequencer,
                 alazar,
                 alazar_controller,
                 heterodyne_source,
                 qubit_source) -> None:
        super().__init__(name)
        self.sequencer = sequencer
        self.alazar = alazar
        self.alazar_controller = alazar_controller
        self.heterodyne_source = heterodyne_source
        self.qubit_source = qubit_source
        sequence_channel = SequenceChannel(self, 'sequence')
        self.add_submodule('sequence', sequence_channel)
        readout_channel = ReadoutChannel(self, 'readout')
        self.add_submodule('readout', readout_channel)
        drive_channel = DriveChannel(self, 'drive', sequencer, qubit_source)
        self.add_submodule('drive', drive_channel)
        self.sequence.reload_template_element_dict()
        self.set_defaults()


    def set_defaults(self):
        """
        Sets defaults such that adD_qubit will not fail.
        """
        self.readout.measurement_duration(1e-6)
        self.readout.measurement_delay(0)
        self.readout.demodulation_type('magphase')
        self.readout.num(1)
        self.readout.integrate_time(True)
        self.readout.single_shot(False)

    def add_qubit(self, readout_frequency: float=7e9,
                  drive_frequency: float=5e9):
        """
        Adds a SidebandingChannel to each of the
        ReadoutChannel and DriveChannels.
        """
        self.readout._add_sidebanding_channel(readout_frequency)
        self.drive._add_sidebanding_channel(drive_frequency)

    def clear_qubits(self):
        """
        Clears the alazar channels and all SidebandingChannels
        (both from the ReadoutChannel and the DriveChannel)
        """
        self._alazar_controller.alazar_channels.clear()
        self.readout._sidebanding_channels.clear()
        self.drive._sidebanding_channels.clear()

    @property
    def _pulse_building_parameters(self):
        return {**self.readout._pulse_building_parameters,
                **self.drive._pulse_building_parameters}

    @property
    def alazar_ch_settings(self):
        """
        Based on the current instrument settings calculates the settings
        configuration for an alazar channel as a dictionary with keys:

        buffers: int
        average_buffers: bool
        records: int
        average_records: bool

        and optionally:

        buffer_setpoints: array
        buffer_setpoint_name: str, None
        buffer_setpoint_label: str, None
        buffer_setpoint_unit: str, None
        records_setpoints: array, None
        records_setpoint_name: str, None
        records_setpoint_label: str, None
        records_setpoint_unit: str, None
        """
        seq_mode = self.sequence.mode()
        num = self.readout.num() or 1
        single_shot = self.readout.single_shot()
        settings = {}
        if not single_shot:
            settings['average_buffers'] = True
            if (seq_mode and self.sequence.inner_setpoints.symbol() is not None):
                if self.sequence.outer_setpoints.setpoints is not None:
                    logger.warn('Averaging channel will average over '
                                'outer setpoints of sequencer sequence')
                record_symbol = self.sequence.inner_setpoints.setpoints[0]
                record_setpoints = self.sequence.inner_setpoints.setpoints[1]
                settings['records'] = len(record_setpoints)
                settings['buffers'] = num
                settings['average_records'] = False
                settings['record_setpoints'] = record_setpoints
                settings['record_setpoint_name'] = record_symbol
                settings['record_setpoint_label'] = record_symbol  # TODO
                settings['record_setpoint_unit'] =  '' # TODO

            else:
                settings['average_records'] = True
                max_samples = self._alazar_controller.board_info['max_samples']
                samples_per_rec = self._alazar_controller.samples_per_record()
                max_records_per_buffer = math.floor(
                    max_samples / samples_per_rec)
                tot_samples = num * samples_per_rec
                if tot_samples > max_samples:
                    settings['records'] = max_records_per_buffer
                    settings['buffers'] = math.ceil(
                        num / max_records_per_buffer)
                else:
                    settings['records'] = num
                    settings['buffers'] = 1
        else:
            settings['average_buffers'] = False
            settings['average_records'] = False
            if seq_mode and self.sequence.inner_setpoints.symbol() is not None:
                if self.sequence.outer_setpoints is not None and num > 1:
                    raise RuntimeError(
                        'Cannot have outer setpoints and multiple nreps')
                record_symbol = self.sequence.inner_setpoints.setpoints[0]
                record_setpoints = self.sequence.inner_setpoints.setpoints[1]
                settings['records'] = len(record_setpoints)
                settings['record_setpoints'] = record_setpoints
                settings['record_setpoint_name'] = record_symbol
                settings['record_setpoint_label'] = record_symbol  # TODO
                settings['record_setpoint_unit'] = '' # TODO
                if self.sequence.outer_setpoints.symbol() is not None:
                    buffer_symbol = self.sequence.outer_setpoints.setpoints[0]
                    buffer_setpoints = self.sequence.outer_setpoints.setpoints[1]
                    settings['buffers'] = len(buffer_setpoints)
                    settings['buffer_setpoints'] = buffer_setpoints
                    settings['buffer_setpoint_name'] = buffer_symbol
                    settings['buffer_setpoint_label'] = buffer_symbol # TODO
                    settings['buffer_setpoint_unit'] = '' # TODO
                else:
                    settings['buffers'] = num
                    settings['buffer_setpoints'] = np.arange(num)
                    settings['buffer_setpoint_name'] = 'repetitions'
                    settings['buffer_setpoint_label'] = 'Repetitions'
                    settings['buffer_setpoint_unit'] = None
            else:
                max_samples = self._alazar_controller.board_info['max_samples']
                samples_per_rec = self._alazar_controller.samples_per_record()
                tot_samples = num * samples_per_rec
                if tot_samples > max_samples:
                    records = math.floor(max_samples / samples_per_rec)
                    buffers = math.ceil(max_samples / records)
                else:
                    records = num
                    buffers = 1
                settings['records'] = records
                settings['buffers'] = buffers
                settings['record_setpoints'] = np.arange(records)
                settings['record_setpoint_name'] = 'record_repetitions'
                settings['record_setpoint_label'] = 'Record Repetitions'
                settings['buffer_setpoints'] = np.arange(buffers)
                settings['buffer_setpoint_name'] = 'buffer_repetitions'
                settings['buffer_setpoint_label'] = 'Buffer Repetitions'
                self._drive_setpoints_from_sideband_setpoints(settings)
        return settings

    def _drive_setpoints_from_sideband_setpoints(self, settings):
        setpoint_types = ['record_setpoint', 'buffer_setpoint']
        for setpoint_type in setpoint_types:
            name = settings[setpoint_type + '_name']
            if 'sideband' in name:
                if 'drive' in name:
                    carrier_freq = self.drive.carrier_frequency()
                else:
                    carrier_freq = self.readout.carrier_frequency()
                settings[setpoint_type + '_name'] = name[:8] + 'frequency'
                settings[setpoint_type + '_label'] = settings[setpoint_type +
                                                              '_label'][:8] + 'Frequency'
                settings[setpoint_type + 's'] += carrier_freq
