from broadbean.types import ForgedSequenceType
from broadbean.plotting import plotter
from qcodes.instrument.base import Instrument
from qcodes.instrument.channel import InstrumentChannel, ChannelList
from qdev_wrappers.interfaces.interface_parameter import InterfaceParameter

# TODO SR to be a parameter and propagate that upwards (parametric sequencer)

class AWGChannelInterface(InstrumentChannel):
    def __init__(self, parent, name):
        # self.add_parameter('power') # TODO replace Vpp with power
        self.add_parameter(name='Vpp',
                           unit='V',
                           label='Peak to Peak Voltage',
                           parameter_class=InterfaceParameter)


class AWGInterface(Instrument):
    CHAN_NUM = 4

    def __init__(self, name):
        super().__init__(name)
        channels = ChannelList(self, 'channels', AWGChannelInterface)
        self.add_submodule('channels', channels)
        for ch in range(self.CHAN_NUM):
            channel = AWGChannelInterface(self, f'ch{ch}')
            self.channels.append(channel)
            self.add_submodule(f'ch{ch}', channel)
        self.add_parameter(name='sample_rate',
                           label='Sample Rate',
                           unit='Hz',
                           parameter_class=InterfaceParameter)

    def upload(self, forged_sequence: ForgedSequenceType):
        raise NotImplementedError()

    def set_infinit_loop(self, element_index: int,
                         true_on_false_off: bool):
        raise NotImplementedError()

    def set_repeated_element(self, index):
        raise NotImplementedError()

    def set_repeated_element_series(self, start_index, stop_index):
        raise NotImplementedError()

    def repeat_full_sequence(self):
        raise NotImplementedError()


class SimulatedAWGInterface(AWGInterface):
    def __init__(self, name, chan_num=4):
        self.CHAN_NUM = chan_num
        self.forged_sequence = None
        super().__init__(name)
        self.sample_rate._save_val(1e9)

    def upload(self, forged_sequence: ForgedSequenceType):
        print(f'uploading')
        SR = self.get_SR()
        self.forged_sequence = forged_sequence
        plotter(forged_sequence, SR=SR)

    def set_repeated_element(self, index):
        print(f'setting repeated element to {index}')
        # AWG is not zero indexed but one, convert to zero index
        index -= 1
        if self.forged_sequence is None:
            print(f'but there was not sequence uploaded')
            return
        plotter(self.forged_sequence[index], SR=self.get_SR())

    def set_repeated_element_series(self, start_index, stop_index):
        print(f'setting repeated element series from {start_index} to '
              f'{stop_index}')
        # AWG is not zero indexed but one, convert to zero index
        start_index -= start_index
        stop_index -= stop_index
        if self.forged_sequence is None:
            print(f'but there was not sequence uploaded')
            return
        plotter(self.forged_sequence[start_index:stop_index], SR=self.get_SR())

    def repeat_full_sequence(self):
        print(f'repeating full series')
        plotter(self.forged_sequence, SR=self.get_SR())


class AWG5014Interface(AWGInterface):
    CHAN_NUM = 4

    def __init__(self, name, awg):
        self.awg = awg
        self.last_repeated_element = None
        self.forged_sequence = None
        self.last_repeated_element_series = (None, None)
        super().__init__(name)
        self.sample_rate.source = awg.clock_freq
        for ch in np.range(self.CHAN_NUM):
            self.submodules[f'ch{ch}'].Vpp.source = awg.parmaeters['ch{ch}_amp']

    def upload(self, forged_sequence: ForgedSequenceType):
        self.awg.make_send_and_load_awg_file_from_forged_sequence(
            forged_sequence)
        self.forged_sequence = forged_sequence
        # uploading a sequence results in reverting the information on the
        # elements
        self.last_repeated_element = None
        self.last_repeated_element_series = (None, None)
        self.awg.all_channels_on()
        self.awg.run()

    def set_repeated_element(self, index):
        print(f'stop repeating {self.last_repeated_element} start {index}')
        self.awg.set_sqel_loopcnt_to_inf(index, state=1)
        self.awg.sequence_pos(index)
        if (self.last_repeated_element is not None and
                self.last_repeated_element != index):
            self.awg.set_sqel_loopcnt_to_inf(self.last_repeated_element,
                                             state=0)
        self.last_repeated_element = index

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
