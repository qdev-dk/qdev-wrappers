from qcodes.instrument.parameter import Parameter
from qdev_wrappers.customised_instruments.composite_instruments.parametric_sequencer.parametric_sequencer import OutOfRangeException


class PulseBuildingParameter(Parameter):
    def __init__(self, name, instrument,
                 set_fn=None,
                 symbol_name=None,
                 **kwargs):
        self.set_fn = set_fn
        if symbol_name is not None:
            self.symbol_name = symbol_name
        elif instrument._pulse_building_prepend:
            self.symbol_name = '_'.join([instrument.name, name])
        else:
            self.symbol_name = name
        super().__init__(name=name, instrument=instrument, **kwargs)

    def set_raw(self, val):
        """
        Executes relevant before set function and then sets the correspoinding
        symbol parameter on the repeat channel of the sequencer where possible.
        If not then attempts to set on the sequence channel.
        """
        sequencer = self.instrument.sequencer
        repeat_params = sequencer.repeat.parameters
        sequence_params = sequencer.sequence.parameters
        if self.set_fn is not None:
            self.set_fn(val)
        if self.symbol_name in repeat_params:
            try:
                repeat_params[self.symbol_name](val)
            except RuntimeWarning as e:
                # with sequencer.no_upload():
                #     sequence_params[self.symbol_name](val)
                raise RuntimeError(str(e) + '. Try changing the setpoints to '
                    'include this value or set them to None')
        else:
            sequence_params[self.symbol_name](val)

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
