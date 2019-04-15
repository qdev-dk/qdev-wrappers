from qcodes.instrument.parameter import Parameter
from warnings import warn


class PulseBuildingParameter(Parameter):
    def __init__(self, name, instrument, set_fn=None, **kwargs):
        self.set_fn = set_fn
        self.symbol_name = instrument.name + '_' + name
        super().__init__(name=name, instrument=instrument, **kwargs)

    def set_raw(self, val):
        """
        Executes relevant before set function and then sets the correspoinding
        symbol parameter on the repeat channel of the sequencer where possible.
        If not then attempts to set on the sequence channel.
        """
        if self.set_fn is not None:
            self.set_fn(val)
        if self.symbol_name in self.instrument._sequencer.repeat.parameters:
            self.instrument._sequencer.repeat.parameters[self.symbol_name](val)
        elif self.symbol_name in self.instrument._sequencer.sequence.parameters:
            self.instrument._sequencer.sequence.parameters[self.symbol_name](
                val)
        else:
            warn(f'Attempted to set {self.symbol_name } on sequencer but this '
                 'parameter was not found.')
        # TODO: what if the sequencer rounds the parameter in question...

    # def get_raw(self):
    #     """
    #     Gets the correspoinding symbol parameter value from the repeat channel
    #     of the sequencer where possible. If not then attempts to get from the
    #     sequence channel.
    #     """
    #     if self.symbol_name in self.instrument._sequencer.repeat.parameters:
    #         return self._sequencer.repeat.parameters[self.symbol_name]()
    #     elif self.symbol_name in self.instrument._sequencer.sequence.parameters:
    #         return self._sequencer.sequence.parameters[self.symbol_name]()
    #     else:
    #         warn(f'Attempted to set {self.symbol_name } on sequencer but this '
    #              'parameter was not found.')
    #         return None
