from qcodes.instrument.base import Instrument
from .pulse_building_parameter import PulseBuildingParameter


class Sidebander(Instrument):
    """
    An instrument which represents a sequencer and microwave drive where the
    sequencer is used to sideband the microwave drive.
    """

    def __init__(self, name, sequencer, carrier, **kwargs):
        super().__init__(name, **kwargs)
        self._microwave_source = carrier
        self._sequencer = sequencer

        self.add_parameter(
            name='frequency',
            set_cmd=self._set_frequency,
            get_cmd=self._get_frequency,
            docstring='Setting updates sideband to generate required'
            ' frequency, getting calculates resultant sidebanded frequency')
        self.add_parameter(
            name='status',
            set_fn=self._set_status,
            source=self._microwave_source.status)

        # pulse building parameters
        self.add_parameter(
            name='sideband_frequency',
            set_fn=self._set_sideband,
            parameter_class=PulseBuildingParameter,
            docstring='Setting this also updates the frequency parameter')
        self.add_parameter(
            name='I_offset',
            parameter_class=PulseBuildingParameter)
        self.add_parameter(
            name='Q_offset',
            parameter_class=PulseBuildingParameter)
        self.add_parameter(
            name='gain_offset',
            parameter_class=PulseBuildingParameter)
        self.add_parameter(
            name='phase_offset',
            parameter_class=PulseBuildingParameter)
        self.add_parameter(
            name='base_amplitude',
            parameter_class=PulseBuildingParameter)
        self.I_offset._save_val(0)
        self.Q_offset._save_val(0)
        self.base_amplitude._save_val(0.8)
        self.phase_offset._save_val(0)
        self.gain_offset._save_val(0)
        self.frequency._save_val(self._microwave_source.frequency())
        self.sideband_frequency._save_val(0)

    def change_sequence(self, **kwargs):
        s_context = self._generate_context()
        s_context.update(kwargs.pop('context', {}))
        self._sequencer.change_sequence(context=s_context, **kwargs)

    def to_default(self):
        self._sequencer.sequence_mode('element')
        self._sequencer.repetition_mode('inf')
        self.status(1)

    # Parameter getters and setters
    def _set_frequency(self, val):
        new_sideband = val - self._microwave_source.frequency()
        self.sideband_frequency(new_sideband)

    def _get_frequency(self):
        return self._microwave_source.frequency() + self.sideband_frequency()

    def _set_status(self, val):
        if str(val).upper() in ['1', 'TRUE', 'ON']:
            self._sequencer.run()
        else:
            self._sequencer.stop()

    def _set_sideband(self, val):
        self.frequency._save_val(self._microwave_source.frequency() + val)

    # Properties
    @property
    def pulse_building_parameters(self):
        param_dict = {n: p for n, p in self.parameters.items() if
                      isinstance(p, PulseBuildingParameter)}
        return param_dict

    # Private methods
    def _generate_context(self):
        return {param.full_name: param() for param in
                self.pulse_building_parameters.values()}
