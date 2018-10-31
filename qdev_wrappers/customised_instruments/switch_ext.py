from qcodes import Instrument
from qcodes.utils import validators as vals


class Switch_ext(Instrument):
    def __init__(self, name, switch, switch_confuguration):
        self._switch = switch
        self._switch_configuration = switch_confuguration
        super().__init__(name)
        self.add_parameter(
            name='configuration',
            set_cmd=self._set_configuration,
            vals=vals.Enum(*[k for k in switch_confuguration.keys()]))

    def _set_configuration(self, val):
        settings = self._switch_configuration[val]
        for k, v in settings.items():
            self._switch.parameters[k](v)
