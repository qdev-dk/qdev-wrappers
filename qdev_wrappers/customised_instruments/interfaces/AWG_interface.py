from lomentum.types import ForgedSequenceType
from lomentum.plotting import plotter
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
                           set_cmd=self.set_sequence_mode,
                           vals=vals.Enum('element', 'sequence'))
        self.add_parameter(name='repetition_mode',
                           set_cmd=self.set_repetition_mode,
                           vals=vals.Enum('single', 'inf'))
        self.add_parameter('sleep_time',
                           label='Sleep time',
                           unit='s',
                           initial_value=5,
                           set_cmd=None,
                           docstring="Time to sleep after "
                                     "setting repeated_element")
        self.sequence_mode._save_val('sequence')
        self.repetition_mode._save_val('inf')

    def upload(self, forged_sequence: ForgedSequenceType):
        """
        Uploads a broadbean forged sequence, keeping the sequence_mode and
        repetition_mode from before (but setting element index to 0 if
        sequence_mode is "element")
        """
        raise NotImplementedError

    def set_sequence_mode(self, seq_mode):
        """
        Sets the sequence mode so that either an individual element will be
        played or a whole sequence. Implemented in children.
        """
        raise NotImplementedError

    def set_repetition_mode(self, rep_mode):
        """
        Sets the repetition mode so that the sequence or element will play
        either on loop (inf) or only once (single). Implemented in children
        """
        raise NotImplementedError

    def set_element(self, index):
        """
        Sets the element at the given index to play (either once or on loop
        depending on the repetition_mode, sequence_mode is set to "element").
        Implemented in children.
        """
        raise NotImplementedError

    def run(self):
        """
        Runs the sequence or element
        """
        raise NotImplementedError

    def stop(self):
        """
        Stops the sequence or element from running
        """
        raise NotImplementedError

    def to_default(self):
        """
        Convenience function which sets up some defaults for sample_rate and
        Vpp.
        """
        self.sample_rate(1e9)
        for ch in self.channels:
            ch.Vpp(1)


class SimulatedAWGInterface(_AWGInterface):
    def __init__(self, name, chan_num=4):
        self.CHAN_NUM = chan_num
        super().__init__(name)
        self.to_default()
        self.sequence_mode._save_val('sequence')
        self.repetition_mode._save_val('inf')
        self.sleep_time(0)

    def upload(self, forged_sequence: ForgedSequenceType):
        print(f'uploading')
        self.forged_sequence = forged_sequence
        self.last_index = len(forged_sequence) - 1
        self.index = 0
        if self.sequence_mode() == 'element':
            self.set_element(0)
        else:
            sleep(self.sleep_time())
            plotter(forged_sequence, SR=self.sample_rate())
            if self.repetition_mode() == 'inf':
                self.run()

    def set_sequence_mode(self, seq_mode):
        print(f'setting sequence_mode to {seq_mode}')
        if seq_mode == 'element':
            self.set_element(self.index)
        else:
            sleep(self.sleep_time())
            plotter(self.forged_sequence, SR=self.sample_rate())
            if self.repetition_mode() == 'inf':
                self.run()

    def set_repetition_mode(self, rep_mode):
        print(f'setting repetition_mode to {rep_mode}')
        sleep(self.sleep_time())
        if rep_mode == 'inf':
            self.run()

    def set_element(self, index):
        print(f'setting element to {index}')
        if index > self.last_index:
            raise RuntimeError(
                f'Cannot set element to {index} as this is '
                'longer than the last sequence index {self.last_index}')
        self.sequence_mode._save_val('element')
        self.index = index
        sleep(self.sleep_time())
        plotter(self.forged_sequence[index], SR=self.sample_rate())
        if self.repetition_mode() == 'inf':
            self.run()

    def run(self):
        print('running')

    def stop(self):
        print('stop')


class AWG5014Interface(_AWGInterface):
    CHAN_NUM = 4

    def __init__(self, name, awg):
        self.awg = awg
        self.awg.delete_all_waveforms_from_list()
        super().__init__(name)
        self.sample_rate.source = awg.clock_freq
        for ch in np.range(self.CHAN_NUM):
            self.submodules[f'ch{ch}'].Vpp.source = awg.parameters['ch{ch}_amp']

    def upload(self, forged_sequence: ForgedSequenceType):
        self.awg.make_send_and_load_awg_file_from_forged_sequence(
            forged_sequence)
        self.awg.all_channels_on()
        self.forged_sequence = forged_sequence
        self.last_index = len(forged_sequence) - 1
        if self.sequence_mode() == 'element':
            self.set_element(0)
        elif self.repetition_mode() == 'single':
            last_index = self.last_index + 1
            self.awg.set_sqel_goto_target_index(last_index, 0)
            sleep(self.sleep_time())
        else:
            self.run()

    def set_sequence_mode(self, seq_mode):
        if seq_mode == 'element':
            self.set_element(self.index)
            return
        elif seq_mode == 'sequence':
            rep_mode = self.repetition_mode()
            index = self.index + 1
            last_index = self.last_index + 1
            if rep_mode == 'single':
                self.awg.set_sqel_goto_target_index(index, index + 1)
                self.awg.set_sqel_goto_target_index(last_index, 0)
            elif rep_mode == 'inf':
                self.awg.set_sqel_loopcnt_to_inf(index, state=0)
                self.awg.set_sqel_goto_target_index(last_index, 1)
        sleep(self.sleep_time())
        if rep_mode == 'inf':
            self.run()

    def set_repetition_mode(self, rep_mode):
        seq_mode = self.sequence_mode()
        if seq_mode == 'element':
            index = self.index + 1
            if rep_mode == 'single':
                # play element once and do not go to the next element after
                self.awg.set_sqel_loopcnt_to_inf(index, state=0)
                self.awg.set_sqel_goto_target_index(index, 0)
            elif rep_mode == 'inf':
                # play element infinitely and go to the next element after
                self.awg.set_sqel_loopcnt_to_inf(index, state=1)
                self.awg.set_sqel_goto_target_index(index, index + 1)
        elif seq_mode == 'sequence':
            last_index = self.last_index + 1
            if rep_mode == 'single':
                # at the end of the sequence stop
                self.awg.set_sqel_goto_target_index(last_index, 0)
            elif rep_mode == 'inf':
                # at the end of the sequence start again
                self.awg.set_sqel_goto_target_index(last_index, 1)
        sleep(self.sleep_time())
        if rep_mode == 'inf':
            self.run()

    def set_element(self, index):
        if index > self.last_index:
            raise RuntimeError(
                f'Cannot set element to {index} as this is '
                'longer than the last sequence index {self.last_index}')

        # configure rest of sequence to defaults
        seq_mode = self.sequence_mode()
        rep_mode = self.repetition_mode()
        if seq_mode == 'sequence':
            # change sequence_mode to 'element' if necessary
            self.sequence_mode._save_val('element')
            if rep_mode == 'single':
                # if the previous mode was to play the sequence once the last
                # element should be reset so that it starts the sequence again
                last_index = self.last_index + 1
                self.awg.set_sqel_goto_target_index(last_index, 1)
        elif seq_mode == 'element':
            old_index = self.index + 1
            if rep_mode == 'inf':
                # if the previous mode was to play one element infinitely that
                # element needs to be reset to play only once
                self.awg.set_sqel_loopcnt_to_inf(old_index, state=0)
            elif rep_mode == 'single':
                # if the previous mode was to play one element once that
                # element needs to be reset to go to the next element after
                self.awg.set_sqel_goto_target_index(old_index, old_index + 1)

        # set element up to play according to repetition_mode
        new_index = index + 1
        if rep_mode == 'single':
            # do not go to the next element after
            self.awg.set_sqel_goto_target_index(new_index, 0)
        elif rep_mode == 'inf':
            # play element infinitely
            self.awg.set_sqel_loopcnt_to_inf(new_index, state=1)
        self.awg.sequence_pos(new_index)
        self.index = index
        sleep(self.sleep_time())
        if rep_mode == 'inf':
            self.run()

    def run(self):
        self.awg.run()

    def stop(self):
        self.awg.stop()
