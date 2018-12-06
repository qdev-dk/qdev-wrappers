from functools import partial
from qcodes import Instrument
from qcodes.utils import validators as vals


class _ConfigurableSwitchBase(Instrument):
    """
    Instrument which given stores a configuration dictionary and has a
    parameter called 'configuration' which will run _set_configuration
    when called.
    """
    def __init__(self, name, switch_configuration):
        self._switch_configuration = switch_configuration
        super().__init__(name)
        self.add_parameter(
            name='configuration',
            set_cmd=self._set_configuration,
            vals=vals.Enum(*[k for k in switch_configuration.keys()]))
        for name, config in switch_configuration.items():
            setattr(name, partial(self._set_configuration, name))

    def _set_configuration(self, val):
        raise NotImplementedError


class ConfigurableSwitch(_ConfigurableSwitchBase):
    """
    'Real' instrument implementation which sets the configuration on the
    switch instrument provided
    """
    def __init__(self, name, switch_configuration, switch):
        self._switch = switch
        super().__init__(name, switch_configuration)

    def _set_configuration(self, val):
        settings = self._switch_configuration[val]
        for k, v in settings.items():
            try:
                self._switch.parameters[k](v)
            except KeyError:
                self._switch.submodules[k](v)


class SimulatedConfigurableSwitch(Instrument):
    """
    Simulated instrument implementation which just chills and
    doesnt complain.
    """
    def _set_configuration(self, val):
        pass
