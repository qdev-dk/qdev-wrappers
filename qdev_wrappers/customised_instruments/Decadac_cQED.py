from qcodes.instrument_drivers.Harvard.Decadac import DacChannel, DacSlot, Decadac
from qcodes.instrument_drivers.devices import VoltageDivider
from qcodes.utils import validators as vals


class DacChannel_cQED(DacChannel):
    """
    A Decadac Channel with a fine_volt parameter
    This alternative channel representation is chosen by setting the class
    variable DAC_CHANNEL_CLASS in the main Instrument
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_parameter("fine_volt",
                           get_cmd=self._get_fine_voltage,
                           set_cmd=self._set_fine_voltage,
                           label="Voltage", unit="V"
                           )

    def _get_fine_voltage(self):
        slot = self._parent
        if slot.slot_mode.get_latest() not in ['Fine', 'FineCald']:
            raise RuntimeError(
                "Cannot get fine voltage unless slot in Fine mode")
        if self._channel == 0:
            fine_chan = 2
        elif self._channel == 1:
            fine_chan = 3
        else:
            raise RuntimeError("Fine mode only works for Chan 0 and 1")
        return self.volt.get() + (slot.channels[fine_chan].volt.get() + 10) / 200

    def _set_fine_voltage(self, voltage):
        slot = self._parent
        if slot.slot_mode.get_latest() not in ['Fine', 'FineCald']:
            raise RuntimeError(
                "Cannot get fine voltage unless slot in Fine mode")
        if self._channel == 0:
            fine_chan = 2
        elif self._channel == 1:
            fine_chan = 3
        else:
            raise RuntimeError("Fine mode only works for Chan 0 and 1")
        coarse_part = self._dac_code_to_v(
            self._dac_v_to_code(round(voltage, 2) - 0.01))

        fine_part = voltage - coarse_part
        fine_scaled = fine_part * 200 - 10
        self.volt.set(coarse_part)
        slot.channels[fine_chan].volt.set(fine_scaled)


class DacSlot_cQED(DacSlot):
    SLOT_MODE_DEFAULT = "Fine"


class Decadac_cQED(Decadac):
    """
    A Decadac with one voltage dividers
    """
    DAC_CHANNEL_CLASS = DacChannel_cQED
    DAC_SLOT_CLASS = DacSlot_cQED

    def __init__(self, name, address, config, **kwargs):
        self.config = config
        deca_physical_min = -10
        deca_physical_max = 10
        kwargs.update({'min_val': deca_physical_min,
                       'max_val': deca_physical_max})

        super().__init__(name, address, **kwargs)
        '''
        config file redesigned to have all channels for overview. Indices in
        config_settings[] for each channel are:
        0: Channels name for deca.{}
        1: Channel label
        2: Channels unit (included as we are using decadac to control
            the magnet)
        3: Voltage division factor
        4: step size
        5: delay
        6: max value
        7: min value
        8: Fine or coarse mode channel
        '''

        for channelNum, settings in config.get('Decadac').items():
            channel = self.channels[int(channelNum)]
            config_settings = settings.split(',')

            name = config_settings[0]
            label = config_settings[1]
            unit = config_settings[2]
            divisor = float(config_settings[3])
            step = float(config_settings[4])
            delay = float(config_settings[5])
            rangemin = float(config_settings[6])
            rangemax = float(config_settings[7])
            fine_mode = config_settings[8]

            if fine_mode == 'fine':
                param = channel.fine_volt
            elif fine_mode == 'coarse':
                param = channel.volt
            else:
                raise RuntimeError(
                    'Invalid config file. Need to specify \'fine\' '
                    'or \'coarse\' not {}'.format(fine_mode))

            channel.volt.set_step(step)
            channel.volt.set_delay(delay)

            param.label = label
            param.unit = unit
            param.set_validator(vals.Numbers(rangemin, rangemax))

            if divisor != 1.:
                # maybe we want a different label
                setattr(self, name, VoltageDivider(
                    param, divisor, label=label))
                param.division_value = divisor
                param._meta_attrs.extend(["division_value"])
            else:
                setattr(self, name, param)
