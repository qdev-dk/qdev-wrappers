from broadbean.types import ForgedSequenceType
from broadbean.plotting import plotter
from time import sleep
import qcodes.utils.validators as vals
from qcodes.instrument.base import Instrument
from qcodes.instrument.channel import InstrumentChannel, ChannelList
from qdev_wrappers.customised_instruments.parameters.delegate_parameters import DelegateParameter


class AWGChannelInterface(InstrumentChannel):
    def __init__(self, parent, name):
        super().__init__(parent, name)
        # self.add_parameter('power') # TODO replace Vpp with power
        self.add_parameter(name='Vpp',
                           unit='V',
                           label='Peak to Peak Voltage',
                           parameter_class=DelegateParameter)


class _AWGInterface(Instrument):
    CHAN_NUM = 4

    def __init__(self, name):
        super().__init__(name)
        self.index = 0
        self.last_index = None
        self.forged_sequence = None
        channels = ChannelList(self, 'channels', AWGChannelInterface)
        self.add_submodule('channels', channels)
        for ch in range(self.CHAN_NUM):
            channel = AWGChannelInterface(self, f'ch{ch}')
            self.channels.append(channel)
            self.add_submodule(f'ch{ch}', channel)
        self.add_parameter(name='sample_rate',
                           label='Sample Rate',
                           unit='Hz',
                           parameter_class=DelegateParameter)
        self.add_parameter(name='sequence_mode',
                           set_cmd=self._set_seq_mode,
                           vals=vals.Enum('element', 'sequence'))
        self.add_parameter(name='repetition_mode',
                           set_cmd=self._set_rep_mode,
                           vals=vals.Enum('single', 'inf'))

    def upload(self, forged_sequence: ForgedSequenceType):
        raise NotImplementedError

    def set_sequence_mode(self, seq_mode):
        raise NotImplementedError

    def set_repetition_mode(self, rep_mode):
        raise NotImplementedError

    def set_element(self, index):
        raise NotImplementedError

    def run(self):
        raise NotImplementedError

    def to_default(self):
        self.sample_rate(1e9)
        for ch in self.channels:
            ch.Vpp(1)


class SimulatedAWGInterface(_AWGInterface):
    def __init__(self, name, chan_num=4):
        self.CHAN_NUM = chan_num
        super().__init__(name)
        self.to_default()

    def upload(self, forged_sequence: ForgedSequenceType):
        print(f'uploading')
        self.forged_sequence = forged_sequence
        self.last_index = len(forged_sequence) - 1
        self.index = 0
        if self.sequence_mode() == 'element':
            self.set_element(0)
        plotter(forged_sequence, SR=self.sample_rate())

    def set_sequence_mode(self, seq_mode):
        print(f'setting sequence_mode to {seq_mode}')
        if seq_mode == 'element':
            self.set_element(self.index)

    def set_repetition_mode(self, rep_mode):
        print(f'setting repetition_mode to {rep_mode}')

    def set_element(self, index):
        print(f'setting element to {index}')
        if index > self.last_index:
            raise RuntimeError(
                f'Cannot set element to {index} as this is '
                'longer than the last sequence index {self.last_index}')
        self.sequence_mode._save_val('element')
        self.index = index
        plotter(forged_sequence[index], SR=self.sample_rate())

    def run(self):
        print('running')

    # def set_repeated_element(self, index):
    #     print(f'setting repeated element to {index}')
    #     # AWG is not zero indexed but one, convert to zero index
    #     index -= 1
    #     if self.forged_sequence is None:
    #         print(f'but there was not sequence uploaded')
    #         return
    #     print(f'running element {index}')
    #     plotter(self.forged_sequence[index], SR=self.get_SR())

    # def set_repeated_element_series(self, start_index, stop_index):

    #     # AWG is not zero indexed but one, convert to zero index
    #     start_index -= start_index
    #     stop_index -= stop_index
    #     if self.forged_sequence is None:
    #         print(f'but there was not sequence uploaded')
    #         return
    #     print(f'setting repeated element series from {start_index} to '
    #           '{stop_index}')
    #     plotter(self.forged_sequence[start_index:stop_index], SR=self.get_SR())


class AWG5014Interface(_AWGInterface):
    CHAN_NUM = 4

    def __init__(self, name, awg):
        self.awg = awg
        # self.last_repeated_element = None
        # self.last_repeated_element_series = (None, None)
        super().__init__(name)
        self.sample_rate.source = awg.clock_freq
        for ch in np.range(self.CHAN_NUM):
            self.submodules[f'ch{ch}'].Vpp.source = awg.parameters['ch{ch}_amp']
        self.add_parameter('sleep_time',
                           label='Sleep time',
                           unit='s',
                           initial_value=5,
                           set_cmd=None,
                           docstring="Time to sleep before and after "
                                     "setting repeated_element")

    def upload(self, forged_sequence: ForgedSequenceType):
        self.awg.make_send_and_load_awg_file_from_forged_sequence(
            forged_sequence)
        self.awg.all_channels_on()
        self.forged_sequence = forged_sequence
        self.last_index = len(forged_sequence) - 1
        if self.sequence_mode() == 'element':
            self.set_element(0)

    def set_sequence_mode(self, seq_mode):
        rep_mode = self.repetition_mode()
        if rep_mode == 'single':
            if seq_mode == 'element':
                self.set_element()

        if rep_mode == 'single' and seq_mode == 'element':
            self.set_goto_index(self._index, -1)
            self.set_goto_index(self._last_index, 0)
            self.set_element(self._index)
        elif rep_mode == 'single' and seq_mode == 'sequence':
            self.set_goto_index(self._index, self._index + 1)
            self.set_goto_index(self._last_index, -1)
            self.set_element(0)
        elif rep_mode == 'single' and seq_mode == 'sequence':
            self.set_goto_index(self._index, self._index + 1)
            self.set_goto_index(self._last_index, -1)
            self.set_element(0)
        if seq_mode == 'element':
            self.set_element(self.index)

    def set_repetition_mode(self, rep_mode):
        seq_mode = self.sequence_mode()
        if seq_mode == 'element':
            index = self.index + 1
            self.repetition_mode._save_val(rep_mode)
            self.set_element()
            if rep_mode == 'single':
                self.awg.set_sqel_loopcnt_to_inf(index, state=0)
                self.awg.set_sqel_goto_target_index(index, 0)
            elif rep_mode == 'inf':
                self.awg.set_sqel_loopcnt_to_inf(index, state=1)
                self.awg.set_sqel_goto_target_index(index, index + 1)
        elif seq_mode == 'sequence':
            last_index = self.last_index + 1
            if rep_mode == 'single':
                self.awg.set_sqel_goto_target_index(last_index, 0)
            elif rep_mode == 'inf':
                self.awg.set_sqel_goto_target_index(last_index, 1)

    def set_element(self, index):
        """
        Given the element index:
        - sets up the element to play once or on loop depending on the
          repetition_mode
        - sets the sequence_mode to element if it isn't already
        - resets the other elements to play as part of a default (looping)
          sequence
        """
        if index > self.last_index:
            raise RuntimeError(
                f'Cannot set element to {index} as this is '
                'longer than the last sequence index {self.last_index}')
        # setting other elements to default looping sequence and updating
        # sequence_mode
        seq_mode = self.sequence_mode()
        rep_mode = self.repetition_mode()
        if seq_mode == 'sequence':
            self.sequence_mode._save_val('element')
            if rep_mode == 'single':
                last_index = self.last_index + 1
                self.awg.set_sqel_goto_target_index(last_index, 1)
        elif seq_mode == 'element':
            old_index = self.index + 1
            if rep_mode == 'inf':
                self.awg.set_sqel_loopcnt_to_inf(old_index, state=0)
            elif rep_mode == 'single':
                self.awg.set_sqel_goto_target_index(old_index, old_index + 1)
        # setting element up to play according to repetition_mode
        new_index = index + 1
        if rep_mode == 'single':
            self.awg.set_sqel_goto_target_index(new_index, 0)
        elif rep_mode == 'inf':
            self.awg.set_sqel_loopcnt_to_inf(new_index, state=1)
        self.awg.sequence_pos(new_index)
        self.index = index



    def set_repeated_element(self, index):
        self.awg.set_sqel_loopcnt_to_inf(index, state=1)
        self.awg.sequence_pos(index)
        if (self.last_repeated_element is not None and
                self.last_repeated_element != index):
            self.awg.set_sqel_loopcnt_to_inf(self.last_repeated_element,
                                             state=0)
        self.last_repeated_element = index
        sleep_time = self.sleep_time.get()
        sleep(sleep_time)

    def set_repeated_element_series(self, start_index, stop_index):
        self._restore_sequence_state()
        self.awg.set_sqel_goto_target_index(stop_index, start_index)
        self.awg.sequence_pos(start_index)

    def repeat_full_sequence(self):
        self._restore_sequence_state()
        self.awg.sequence_pos(1)

    def _restore_sequence_state(self):
        if self.last_repeated_element is not None:
            self.awg.set_sqel_loopcnt_to_inf(self.last_repeated_element,
                                             state=0)
        lres = self.last_repeated_element_series
        if lres[0] is not None or lres[1] is not None:
            assert (lres[0] is not None and
                    lres[1] is not None and
                    self.forged_sequence is not None)
            if lres[0] == len(self.forged_sequence):
                goto_element = 1
            else:
                goto_element = 0
            self.awg.set_sqel_goto_target_index(lres[0], goto_element)

    def _set_seq_mode(self, seq_mode):
        rep_mode = self.repetition_mode()
        if rep_mode == 'single' and seq_mode == 'element':
            self.set_goto_index(self._index, -1)
            self.set_goto_index(self._last_index, 0)
            self.set_element(self._index)
        elif rep_mode == 'single' and seq_mode == 'sequence':
            self.set_goto_index(self._index, self._index + 1)
            self.set_goto_index(self._last_index, -1)
            self.set_element(0)
        elif rep_mode == 'single' and seq_mode == 'sequence':
            self.set_goto_index(self._index, self._index + 1)
            self.set_goto_index(self._last_index, -1)
            self.set_element(0)

    def _set_rep_mode(self, rep_mode):
        seq_mode = self.sequence_mode()
        if seq_mode == 'element' and rep_mode == 'single':
            self.set_goto_index(self._index, -1)
            self.set_nreps(self._index, 1)
            self.set_element(self._index)
        elif seq_mode == 'element' and rep_mode == 'inf':
            self.set_goto_index(self._index, self._index + 1)
            self.set_nreps(self._index, 'inf')
            self.set_element(self._index)
        elif seq_mode == 'sequence' and rep_mode == 'single':
            self.set_goto_index(self._last_index, -1)
            self.set_element(0)
        elif seq_mode == 'sequence' and rep_mode == 'inf':
            self.set_goto_index(self._last_index, 0)
            self.set_element(0)
