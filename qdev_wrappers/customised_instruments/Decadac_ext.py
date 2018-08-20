from qcodes.instrument_drivers.Harvard.Decadac import DacChannel, DacSlot, Decadac
from qcodes.instrument_drivers.devices import VoltageDivider
from qcodes.utils import validators as vals


class DacChannel_ext(DacChannel):
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


class DacSlot_ext(DacSlot):
    SLOT_MODE_DEFAULT = "Fine"


class Decadac_ext(Decadac):
    """
    A Decadac with one voltage dividers
    """
    DAC_CHANNEL_CLASS = DacChannel_local
    DAC_SLOT_CLASS = DacSlot_local

    def __init__(self, name, address, **kwargs):
        deca_physical_min = -10
        deca_physical_max = 10
        kwargs.update({'min_val': deca_physical_min,
                       'max_val': deca_physical_max})

        super().__init__(name, address, **kwargs)
