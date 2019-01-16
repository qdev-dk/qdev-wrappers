from functools import partial
from qcodes.utils import validators as vals
from qcodes.instrument.parameter import Parameter
from qdev_wrappers.customised_instruments.parameters.delegate_parameters import DelegateParameter
from qdev_wrappers.customised_instruments.parametric_waveform_analyser.setpoints_channel import SetpointsChannel
from qdev_wrappers.customised_instruments.spectrum_analyser_calibration.base import SpectrumAnalyserCalibrator


class SidebandCalibratorPulseBuildingParameter(Parameter):
    def __init__(self, name, sequencer, **kwargs):
        self._sequencer = sequencer
        super().__init__(name, **kwargs)

    def set_raw(self, val):
        self._save_val(val)
        self._attempt_set_on_sequencer(val)

    def _attempt_set_on_sequencer(self, val):
        if self.name in self._sequencer.repeat.parameters.keys():
            sequencer_param = self._sequencer.repeat.parameters[self.name]
            sequencer_param.set(val)
        else:
            self._pwa.sequence._set_not_up_to_date()


class SidebandCalibrator(SpectrumAnalyserCalibrator):
    sideband_params = ['I_offset', 'Q_offset', 'gain_imbalance',
                       'phase_imbalance', 'pulse_amplitude', 'total_duration',
                       'sideband_frequency']
    sideband_labels = ['I Offset', 'Q Offset', 'Gain Imbalance',
                       'Phase Imbalance', 'Base Pulse Amplitude',
                       ' Cycle Duration', 'Sideband Frequency']
    sindeband_units = ['V', 'V', None, 'degrees', None, 's', 'Hz']

    def __init__(self, name, spectrum_analyser_interface,
                 microwave_source_interface, sequencer, template_element):
        self._template_element = template_element
        self._microwave_source_interface = microwave_source
        self._sequencer = sequencer
        self._awg = sequencer.awg.awg
        super().__init__(name, spectrum_analyser_interface)
        self.signal_frequency._set_fn = False
        self.signal_frequency._get_fn = self._get_signal_frequency
        self._sequencer._routes.update()
        self._up_to_date = False
        self._awg_channels = {'I': 1, 'Q': 2}
        setpoints_channel = SetpointsChannel(self, 'setpoints')
        self.add_submodule('setpoints', setpoints_channel)
        self.setpoints.symbol.vals = vals.Enum(self.sideband_params)

        # microwave_source_params
        self.add_parameter(name='carrier_power',
                           label='Carrier Power',
                           unit='dBm',
                           source=microwave_source.power,
                           parameter_class=DelegateParameter)
        self.add_parameter(name='carrier_frequency',
                           label='Carrier Frequency',
                           unit='dBm',
                           source=microwave_source.frequency,
                           parameter_class=DelegateParameter)

        # awg params
#        self.add_parameter(name='sideband_power', # TODO
#                           unit='dBm',
#                           set_cmd=self._set_sideband_power,
#                           get_cmd=self._get_sideband_power)
        self.add_paramaeter(name='awg_Vpp',
                            label='Peak to Peak Voltage',
                            unit='V',
                            set_cmd=self._set_awg_ch_voltage)
        self._pulse_building_parameters = {}
        for i, p in enumerate(self.sideband_params):
            self.add_parameter(
                name=p,
                label=self.sideband_labels[i],
                unit=self.sideband_units[i],
                parameter_class=SidebandCalibratorPulseBuildingParameter)
            self._pulse_building_parameters[p] = self.parameters[p]
        self.add_parameter(name='I_channel',
                           set_cmd=partial('I', self._update_routes),
                           vals=vals.Ints())
        self.add_parameter(name='Q_channel',
                           set_cmd=partial('Q', self._update_routes),
                           vals=vals.Ints())

        # measurement parameters
        self.add_parameter(name='measure_carrier',
                           label='Signal at Carrier Frequency',
                           unit='dBm',
                           get_cmd=self._measure_carrier)
        self.add_parameter(name='measure_other_sideband',
                           label='Signal at Other Sideband Frequency',
                           unit='dBm',
                           get_cmd=self._measure_other_sideband)
        self.add_parameter(name='measure_SCR',
                           label='Signal to Carrier Ratio',
                           unit='dB',
                           get_cmd=self._measure_scr)
        self.add_parameter(name='measure_SSR',
                           label='Signal to Other Sideband Ratio',
                           unit='dB',
                           get_cmd=self._get_ssr)

    def _get_signal_frequency(self):
        return self.carrier_frequency() + self.sideband_frequency()

    def _update_routes(self, IQ, val):
        self._sequencer._routes[IQ] = val
        self._awg_channels[IQ] = val
        self._up_to_date = False

    def _measure_carrier(self):
        return self.measure_at_frequency(self.carrier_frequency())

    def _measure_other_sideband(self):
        return self.measure_at_frequency(self.other_sidebend_frequency)

    def _measure_scr(self):
        signal = self._measure_signal()
        carrier = self._measure_other_sideband()
        return signal - carrier

    def _get_ssr(self):
        signal = self._measure_signal()
        other_sideband = self._measure_other_sideband()
        return signal - other_sideband

    @property
    def signal_frequency(self):
        return self.carrier_frequency() + self.sideband_frequency()

    @property
    def other_sidebend_frequency(self):
        return self.carrier_frequency() - self.sideband_frequency()

    def _set_awg_ch_voltage(self, val):
        for num in self._awg_channels.values():
            self._awg.parameters[f'ch{num}_amp'].set(val)

    def _update_for_trace(self, **kwargs):
        if not self.instrument._sequencer.repeat_mode.get_latest() == 'element':
            # TODO should we trust this to be done from outside?
            self.instrument._sequencer.repeat_mode('element')
            self.instrument._sync_repeat_parameters()
        if not self.instrument._up_to_date:
            self.instrument._update_sequence()
        super()._update_for_trace(**kwargs)

    def _generate_context(self):
        context = {}
        labels = {}
        units = {}
        for name, param in self._pulse_building_parameters.items():
            context[name] = param()
            labels[name] = param.label
            units[name] = param.unit
        return {'context': context, 'labels': labels, 'units': units}

    def _sync_repeat_parameters(self):
        for paramname, param in self._sequencer.repeat.parameters.items():
            param.set(self._pulse_building_parameters[paramname].get())

    def _update_sequence(self):
        if not self._up_to_date:
            self._parent._sequencer.set_template(
                self._template_element,
                inner_setpoints=self.inner_setpoints.setpoints,  # TODO add outer_setpoints
                **self._generate_context())
            self._up_to_date = True
            self._sync_repeat_parameters()

#    def _set_sideband_power(self, val):
#        watt_power = 10 **((val - 30) / 10)
#        vrms = np.sqrt(watt_power * 50)
#        vpp = 2 * np.sqrt(2) * vrms
#        vpp_w_amp_scaling = vpp / self.pulse_amplitude()
#        for ch_num in self._channels_map.values():
#            self._awg.parameters[f'ch{ch_num}_amp'].set(vpp)
#
#    def _get_sideband_power(self):
#        I_chan = self._channels_map['I']
#        vpp = self._awg.parameters[f'ch{I_chan}_amp'].get()
#        vrms = vpp / (2 * np.sqrt(2))
#        watt_power =  vrms ** 2 / 50
#        dbm_power = 10 * np.log10(watt_power) + 30
#        return dbm_power
