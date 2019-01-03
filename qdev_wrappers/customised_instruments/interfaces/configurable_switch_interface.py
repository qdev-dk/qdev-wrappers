from functools import partial
from qcodes import Instrument
from qcodes.utils import validators as vals
from qdev_wrappers.customised_instruments.interfaces.interface_parameters import InterfaceParameter


class _ConfigurableSwitchInterface(Instrument):
    """
    Instrument which given stores a configuration dictionary and has a
    parameter called 'configuration' which will run _set_configuration
    when called.

    Switch configuration should be provided like:
    {'frequency_domain': {'a': 1, 'b': 2},
     'time_domain': {'a': 2, 'b': 1}}
    which would result in the switch parameter 'configuration' having vals
    'frequency_domain' and 'time_domain' and setting one of these would
    set the 'a' and 'b' parameters of the switch to the corresponding values
    as implemented in the subclasses _ConfigurableSwitchInterface.
    """
    def __init__(self, name, switch_configuration):
        switch_params = set(next(iter(switch_configuration.values())).keys())
        for config in switch_configuration.values():
            if set(config.keys()) != switch_params:
                raise RuntimeError(
                    'All configurations must have same keys: '
                    '{} does not match {}',format(config.keys, switch_params))
        super().__init__(name)
        self._switch_configuration = switch_configuration
        for param in switch_params:
            self.add_parameter(name=param,
                               set_fn=partial(self._set_switch_param, param),
                               parameter_class=InterfaceParameter)
        self.add_parameter(
            name='configuration',
            set_cmd=self._set_configuration,
            vals=vals.Enum(*[k for k in switch_configuration.keys()]))
        switch_configuration.keys()

    def _set_configuration(self, val):
        config = self._switch_configuration.get(val, {})
        for k, v in config.items():
            self._set_switch_param(k, v)

    def _set_switch_param(self, paramname, val):
        self.configuration._save_val(None)

class RealConfigurableSwitchInterface(_ConfigurableSwitchInterface):
    """
    'Real' instrument implementation which sets the configuration on the
    switch instrument provided
    """
    def __init__(self, name, switch_configuration, switch):
        switch_params = set(next(iter(switch_configuration.values())).keys())
        if any(p not in switch.parameters.keys() for p in switch_params):
            raise RuntimeError('Switch parameters do not match instrument parameters')
        self._switch = switch
        super().__init__(name, switch_configuration)
        for p in switch_params:
            self.parameters[p].source = self._switch.parameters[p]

"""
Simulated instrument implementation which just chills and
doesnt complain so that the value of the 'configuration' parameter
is stored but setting it doesnt actually do anything.
"""
SimulatedConfigurableSwitch = _ConfigurableSwitchInterface
