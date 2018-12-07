from qcodes.instrument.parameter import Parameter
import logging

logger = logging.getLogger(__name__)


class PWAPulseBuildingParameter(Parameter):
    """
    A Parameter representing a parameter of a pulse sequence running
    on a ParametricSequencer (ie used to build the context).
    It has a pulse_building_name attribute for use in sequence building
    and updates the sequence on setting.
    """

    def __init__(self, name, instrument, pulse_building_name=None,
                 set_allowed=True, **kwargs):
        self._set_allowed = set_allowed
        self.pulse_building_name = pulse_building_name or name
        pwa_instr = instrument
        while hasattr(pwa_instr, '_parent'):
            pwa_instr = pwa_instr._parent
        self._pwa = pwa_instr
        super().__init__(
            name, instrument=instrument,
            get_cmd=None, **kwargs)

    def set_raw(self, val):
        if not self._set_allowed:
            raise RuntimeError(f"Setting {self.full_name} not allowed")
        self._save_val(val)
        self._attempt_set_on_sequencer(val)

    def _attempt_set_on_sequencer(self, val):
        setpoint_symbols = list(self._pwa._sequencer.repeat.parameters.keys())
        if self.pulse_building_name in setpoint_symbols:
            if self._pwa.sequence.mode():
                logger.warning(
                    f'Sequence mode is on and {self.pulse_building_name} '
                    'is varied in the sequence. Setting it will only become '
                    'relevant when a new sequence is uploaded which does not '
                    'vary this parameter or if'
                    'sequence mode is turned off')
            sequencer_param = self._pwa._sequencer.repeat.parameters[self.pulse_building_name]
            sequencer_param.set(val)
        else:
            self._pwa.sequence._set_not_up_to_date()

    def get_raw(self):
        if self.pulse_building_name in self._pwa._sequencer.repeat.parameters:
            if self._pwa.sequence.mode():
                logging.warning(
                    f'Sequence mode is on and {self.pulse_building_name} is '
                    'varied in the sequence. Value returned will only become '
                    'relevant when a new sequence is uploaded which does not '
                    'vary this parameter or if sequence mode is turned off')
        return self._latest['raw_value']
