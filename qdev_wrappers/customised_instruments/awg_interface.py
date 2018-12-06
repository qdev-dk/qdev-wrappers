from lomentum.types import ForgedSequenceType
from lomentum.plotting import plotter


class AWGInterface:

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

    def get_SR(self):
        raise NotImplementedError()


class SimulatedAWGInterface(AWGInterface):
    def __init__(self):
        self.forged_sequence = None

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

    def get_SR(self):
        # fake this for now
        return 1e9


class AWG5014Interface(AWGInterface):
    def __init__(self, awg):
        self.awg = awg
        self.last_repeated_element = None
        self.forged_sequence = None
        self.last_repeated_element_series = (None, None)

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

    def get_SR(self):
        return self.awg.clock_freq()

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
