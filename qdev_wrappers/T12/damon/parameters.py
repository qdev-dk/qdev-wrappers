from qcodes.instrument.parameter import MultiParameter
import numpy as np

class Dummyinstrument:

    def __init__(self):
        self.name = 'dummyinstrument'


class VoltageParameter(MultiParameter):
    """
    Amplified voltage measurement via an SR560 preamp and a measured voltage.

    To be used when you feed a voltage into an SR560, send the SR560's
    output voltage to a lockin or other voltage amplifier, and you have
    the voltage reading from that amplifier as a qcodes parameter.

    ``VoltageParameter.get()`` returns ``(voltage_raw, voltage)``

    Args:
        measured_param (Parameter): a gettable parameter returning the
            voltage read from the SR560 output.

        v_amp_ins (SR560): an SR560 instance where you manually
            maintain the present settings of the real SR560 amp.

            Note: it should be possible to use other voltage preamps, if they
            define parameters ``gain`` (V_out / V_in) and ``invert``
            (bool, output is inverted)

        name (str): the name of the current output. Default 'curr'.
            Also used as the name of the whole parameter.
    """
    def __init__(self, measured_param, v_amp_ins, name='volt'):
        p_name = measured_param.name

        super().__init__(name=name, names=(p_name+'_raw', name), shapes=((), ()))

        self._measured_param = measured_param
        self._instrument = v_amp_ins

        p_label = getattr(measured_param, 'label', None)
        p_unit = getattr(measured_param, 'unit', None)

        self.labels = (p_label, 'Voltage')
        self.units = (p_unit, 'V')

    def get(self):
        volt = self._measured_param.get()
        volt_amp = (volt / self._instrument.gain.get())

        if self._instrument.invert.get():
            volt_amp *= -1

        value = (volt, volt_amp)
        self._save_val(value)
        return value


class VoltageParameterDAC(MultiParameter):
    """
    Amplified voltage measurement via an SR560 preamp and a measured voltage.

    To be used when you feed a voltage into an SR560, send the SR560's
    output voltage to a lockin or other voltage amplifier, and you have
    the voltage reading from that amplifier as a qcodes parameter.

    ``VoltageParameter.get()`` returns ``(voltage_raw, voltage)``

    Args:
        measured_param (Parameter): a gettable parameter returning the
            voltage read from the SR560 output.

        v_amp_ins (SR560): an SR560 instance where you manually
            maintain the present settings of the real SR560 amp.

            Note: it should be possible to use other voltage preamps, if they
            define parameters ``gain`` (V_out / V_in) and ``invert``
            (bool, output is inverted)

        name (str): the name of the current output. Default 'curr'.
            Also used as the name of the whole parameter.
    """
    def __init__(self, measured_param, v_amp_ins, name='volt'):
        p_name = measured_param.name

        super().__init__(name=name, names=(p_name+'_raw', name), shapes=((), ()))

        self._measured_param = measured_param
        self._instrument = v_amp_ins

        p_label = getattr(measured_param, 'label', None)
        p_unit = getattr(measured_param, 'unit', None)

        self.labels = (p_label, 'Voltage')
        self.units = (p_unit, 'V')

    def get(self):
        volt = self._measured_param.get()
        volt_amp = ((volt * self._instrument.lockinsens.get()) / (10 * self._instrument.gain.get()))

        if self._instrument.invert.get():
            volt_amp *= -1

        value = (volt, volt_amp)
        self._save_val(value)
        return value


class CurrentParameter(MultiParameter):
    """
    Current measurement via an Ithaco preamp and a measured voltage.

    To be used when you feed a current into the Ithaco, send the Ithaco's
    output voltage to a lockin or other voltage amplifier, and you have
    the voltage reading from that amplifier as a qcodes parameter.

    ``CurrentParameter.get()`` returns ``(voltage_raw, current)``

    Args:
        measured_param (Parameter): a gettable parameter returning the
            voltage read from the Ithaco output.

        c_amp_ins (Ithaco_1211): an Ithaco instance where you manually
            maintain the present settings of the real Ithaco amp.

            Note: it should be possible to use other current preamps, if they
            define parameters ``sens`` (sensitivity, in A/V), ``sens_factor``
            (an additional gain) and ``invert`` (bool, output is inverted)

        name (str): the name of the current output. Default 'curr'.
            Also used as the name of the whole parameter.
    """
    def __init__(self, measured_param, c_amp_ins, name='curr'):
        p_name = measured_param.name

        super().__init__(name=name, names=(p_name+'_raw', name), shapes=((), ()))

        self._measured_param = measured_param
        self._instrument = c_amp_ins

        p_label = getattr(measured_param, 'label', None)
        p_unit = getattr(measured_param, 'unit', None)

        self.labels = (p_label, 'Current')
        self.units = (p_unit, 'A')

    def get(self):
        volt = self._measured_param.get()
        current = self._instrument.gain.get() * volt

        if self._instrument.invert.get():
            current *= -1

        value = (volt, current)
        self._save_val(value)
        return value

class CurrentParameterDAC(MultiParameter):
    """
    Current measurement via an Ithaco preamp and a measured voltage.

    To be used when you feed a current into the Ithaco, send the Ithaco's
    output voltage to a lockin, and read that out via a DAC connected to the channel output
    so the DAC reads a voltage from 0 to 10 V, where 10 is the full range at
    the lockin's sensitivity.

    ``CurrentParameterDAC.get()`` returns ``(voltage_raw, current)``

    Args:
        measured_param (Parameter): a gettable parameter returning the
            voltage read from the DAC.

        c_amp_ins (Ithaco_1211): an Ithaco instance where you manually
            maintain the present settings of the real Ithaco amp.

        lockin_sensitivity (SR830): The sensitivity of the lockin.

            Note: it should be possible to use other current preamps, if they
            define parameters ``sens`` (sensitivity, in A/V), ``sens_factor``
            (an additional gain) and ``invert`` (bool, output is inverted)

        name (str): the name of the current output. Default 'curr'.
            Also used as the name of the whole parameter.
    """
    def __init__(self, measured_param, c_amp_ins, name='curr'):
        p_name = measured_param.name

        super().__init__(name=name, names=(p_name+'_raw', name), shapes=((), ()))

        self._measured_param = measured_param
        self._instrument = c_amp_ins


        p_label = getattr(measured_param, 'label', None)
        p_unit = getattr(measured_param, 'unit', None)

        self.labels = (p_label, 'Current')
        self.units = (p_unit, 'A')

    def get(self):
        volt = self._measured_param.get()
        current = self._instrument.gain.get() * volt * 0.1 * self._instrument.lockinsens.get()

        if self._instrument.invert.get():
            current *= -1

        value = (volt, current)
        self._save_val(value)
        return value



class CurrentParameterList(MultiParameter):
    def __init__(self, measured_param, c_amp_ins, name='curr'):
        p_name = measured_param.name

        super().__init__(name=name, names=(p_name+'_raw', name), shapes=((), ()))

        self._measured_param = measured_param
        self._instrument = c_amp_ins

        p_labels = getattr(measured_param, 'labels', None)
        p_units = getattr(measured_param, 'units', None)
        p_names = getattr(measured_param, 'names', None)


        self.names = (*p_names, *['curr%d'%i for i in range(len(p_labels))])
        self.labels = (*p_labels, *['Current' for i in range(len(p_labels))])
        self.units = (*p_units, *['A' for _ in p_units])
        self.shapes=(*[() for _ in p_names], *[() for _ in p_names])

    def get(self):
        volt = self._measured_param.get()
        current = self._instrument.gain.get() * volt

        if self._instrument.invert.get():
            current *= -1

        value = (*volt, *current)
        self._save_val(value)
        return value



class VoltageParameterList(MultiParameter):
    def __init__(self, measured_param, v_amp_ins, name='curr'):
        p_name = measured_param.name

        super().__init__(name=name, names=(p_name+'_raw', name), shapes=((), ()))

        self._measured_param = measured_param
        self._instrument = v_amp_ins

        p_labels = getattr(measured_param, 'labels', None)
        p_units = getattr(measured_param, 'units', None)
        p_names = getattr(measured_param, 'names', None)


        self.names = (*p_names, *['volt%d'%i for i in range(len(p_labels))])
        self.labels = (*p_labels, *['Voltage' for i in range(len(p_labels))])
        self.units = (*p_units, *['V' for _ in p_units])
        self.shapes=(*[() for _ in p_names], *[() for _ in p_names])

    def get(self):
        volt_raw = self._measured_param.get()
        volt = (volt_raw / self._instrument.gain.get())

        if self._instrument.invert.get():
            volt *= -1

        value = (*volt_raw, *volt)
        self._save_val(value)
        return value

from qcodes import MultiParameter

class ConductanceParameter(MultiParameter):
    def __init__(self, volt_param, curr_param, name='conductance'):
        p_name = 'conductance'

        super().__init__(name=name, names=(name, volt_param.name, curr_param.name), shapes=((), (), ()))

        self._volt_param = volt_param
        self._curr_param = curr_param

        v_label = getattr(volt_param, 'label', None)
        v_unit = getattr(volt_param, 'unit', None)

        self.labels = ('Conductance', v_label, c_label)
        self.units = ('S', v_unit, c_unit)

    def get(self):
        volt = self._volt_param.get()
        curr = self._curr_param.get()
        if volt == 0:
            volt = np.inf
        cond = curr/volt

        value = (volt, curr, cond)
        self._save_val(value)
        return value





class QConductanceParameterDAC(MultiParameter):

    def __init__(self, measured_param, c_amp_ins, name='curr'):
        p_name = measured_param.name

        super().__init__(name=name, names=(p_name+'_raw', name), shapes=((), ()))

        self._measured_param = measured_param
        self._instrument = c_amp_ins


        p_label = getattr(measured_param, 'label', None)
        p_unit = getattr(measured_param, 'unit', None)

        self.labels = (p_label, 'Conductance')
        self.units = (p_unit, '2e2/h')

    def get(self):
        volt = self._measured_param.get()
        current = self._instrument.gain.get() * volt * 0.1 * self._instrument.lockinsens.get()
        excitation = self._instrument.ac_excitation.get() * self._instrument.ac_divider.get()
        conductance = (current*12906)/excitation

        if self._instrument.invert.get():
                current *= -1

        value = (volt, conductance)
        self._save_val(value)
        return value


class ResistanceParameterDAC1(MultiParameter):

    def __init__(self, measured_param, c_amp_ins, name='curr'):
        p_name = measured_param.name

        super().__init__(name=name, names=(p_name+'_raw', name), shapes=((), ()))

        self._measured_param = measured_param
        self._instrument = c_amp_ins


        p_label = getattr(measured_param, 'label', None)
        p_unit = getattr(measured_param, 'unit', None)

        self.labels = (p_label, 'Resistance')
        self.units = (p_unit, 'Ohm')

    def get(self):
        volt = self._measured_param.get()
        current = self._instrument.gain.get() * volt * 0.1 * self._instrument.lockinsens.get()
        excitation = self._instrument.ac_excitation.get() * self._instrument.ac_divider.get()
        resistance = excitation/current

        if self._instrument.invert.get():
            current *= -1

        value = (volt, resistance)
        self._save_val(value)
        return value


class ResistanceParameterDAC(MultiParameter):
    def __init__(self, volt_param, curr_param, v_amp_ins, c_amp_ins, name='conductance'):
        p_name = 'resistance'

        super().__init__(name=name, names=(name, volt_param.name), shapes=((), ()))

        self._volt_param = volt_param
        self._curr_param = curr_param
        self._instrument = v_amp_ins
        self._instrumentcurr = c_amp_ins

        v_label = getattr(volt_param, 'label', None)
        v_unit = getattr(volt_param, 'unit', None)

        self.labels = ('Resistance', v_label)
        self.units = ('Ohm', v_unit)

    def get(self):
        volt = (0.1 * self._volt_param.get() * self._instrument.lockinsens.get())/self._instrument.gain.get()
        curr = (0.1 * self._curr_param.get() * self._instrumentcurr.lockinsens.get() * self._instrumentcurr.gain.get())
        if volt == 0:
            volt = np.inf
        resist = volt/curr

        value = (resist, volt)
        self._save_val(value)
        return value



class QConductanceParameter(MultiParameter):
    def __init__(self, volt_param, curr_param, v_amp_ins, c_amp_ins, name='conductance'):
        p_name = 'resistance'

        super().__init__(name=name, names=(name, volt_param.name), shapes=((), ()))

        self._volt_param = volt_param
        self._curr_param = curr_param
        self._instrumentvolt = v_amp_ins
        self._instrumentcurr = c_amp_ins
        #self._instrument = Dummyinstrument()

        v_label = getattr(volt_param, 'label', None)
        v_unit = getattr(volt_param, 'unit', None)

        self.labels = ('Conductance', v_label)
        self.units = ('2e2/h', v_unit)

    def get(self):
        volt = (self._volt_param.get() /self._instrumentvolt.gain.get())
        curr = (self._curr_param.get()  * self._instrumentcurr.gain.get())
        if volt == 0:
            volt = 0.0000000001
        conductance = curr/volt * 12906

        value = (conductance, volt)
        self._save_val(value)
        return value

class QConductanceParameterDAC4pt(MultiParameter):
    def __init__(self, volt_param, curr_param, v_amp_ins, c_amp_ins, name='conductance'):
        p_name = 'resistance'

        super().__init__(name=name, names=(name, volt_param.name), shapes=((), ()))

        self._volt_param = volt_param
        self._curr_param = curr_param
        self._instrument = v_amp_ins
        self._instrumentcurr = c_amp_ins
        #self._instrument = Dummyinstrument()

        v_label = getattr(volt_param, 'label', None)
        v_unit = getattr(volt_param, 'unit', None)

        self.labels = ('Conductance', v_label)
        self.units = ('2e2/h', v_unit)

    def get(self):
        volt = (10 * self._volt_param.get() * self._instrument.lockinsens.get())/self._instrument.gain.get()
        curr = (10 * self._curr_param.get() * self._instrumentcurr.lockinsens.get() * self._instrumentcurr.gain.get())
        if volt == 0:
            volt = 0.0000000001
        conductance = curr/volt * 12906

        value = (conductance, volt)
        self._save_val(value)
        return value

class QConductanceParameter4pt(MultiParameter):
    def __init__(self, volt_param, curr_param, v_amp_ins, c_amp_ins, name='conductance'):
        p_name = 'resistance'

        super().__init__(name=name, names=(name, volt_param.name), shapes=((), ()))

        self._volt_param = volt_param
        self._curr_param = curr_param
        self._instrument = v_amp_ins
        self._instrumentcurr = c_amp_ins
        #self._instrument = Dummyinstrument()

        v_label = getattr(volt_param, 'label', None)
        v_unit = getattr(volt_param, 'unit', None)

        self.labels = ('Conductance', v_label)
        self.units = ('2e2/h', v_unit)

    def get(self):
        volt = (self._volt_param.get())/self._instrument.gain.get()
        curr = (self._curr_param.get() * self._instrumentcurr.gain.get())
        if volt == 0:
            volt = 0.0000000001
        conductance = curr/volt * 12906

        value = (conductance, volt)
        self._save_val(value)
        return value



class ResistanceParameter(MultiParameter):
    def __init__(self, volt_param, curr_param, v_amp_ins, c_amp_ins, name='conductance'):
        p_name = 'resistance'

        super().__init__(name=name, names=(name, volt_param.name), shapes=((), ()))

        self._volt_param = volt_param
        self._curr_param = curr_param
        self._instrument = v_amp_ins
        self._instrumentcurr = c_amp_ins
        #self._instrument = Dummyinstrument()

        v_label = getattr(volt_param, 'label', None)
        v_unit = getattr(volt_param, 'unit', None)

        self.labels = ('Resistance', v_label)
        self.units = ('Ohm', v_unit)

    def get(self):
        volt = (self._volt_param.get() /self._instrument.gain.get())
        curr = (self._curr_param.get()  * self._instrumentcurr.gain.get())
        if curr ==0:
            resist = 0
        else:
            resist = volt/curr

        value = (resist, volt)
        self._save_val(value)
        return value


class ConductanceParameterList(MultiParameter):
    def __init__(self, volt_param, curr_param, name='conductance'):
        p_name = 'conductance'
        super().__init__(name=name, names=(volt_param.name), shapes=((), (), ()))



        self._volt_param = volt_param
        self._curr_param = curr_param

        v_labels = getattr(volt_param, 'labels', None)
        v_units = getattr(volt_param, 'units', None)
        v_names = getattr(volt_param, 'names', None)

        c_labels = getattr(curr_param, 'labels', None)
        c_units = getattr(curr_param, 'units', None)
        c_names = getattr(curr_param, 'names', None)

        self.names = list('cond%d'%i for i in range(len(v_names)))
        self.labels = list('Conductance' for _ in v_names)
        self.units = list('S' for _ in v_names)
        self.shapes = list(() for _ in v_names)

    def get(self):
        volt = self._volt_param.get_latest()
        curr = self._curr_param.get_latest()

        volt[volt==0] = np.inf

        cond = curr/volt

        value = tuple(cond)
        self._save_val(value)
        return value

class PhaseParameterDAC(MultiParameter):
    """
    Current measurement via an Ithaco preamp and a measured voltage.

    To be used when you feed a current into the Ithaco, send the Ithaco's
    output voltage to a lockin, and read that out via a DAC connected to the channel output
    so the DAC reads a voltage from 0 to 10 V, where 10 is the full range at
    the lockin's sensitivity.

    ``PhaseParameterDAC.get()`` returns ``(voltage_raw, phase)``

    Args:
        measured_param (Parameter): a gettable parameter returning the
            voltage read from the DAC.

        name (str): the name of the current output. Default 'curr'.
            Also used as the name of the whole parameter.
    """
    def __init__(self, measured_param, name='curr'):
        p_name = measured_param.name

        super().__init__(name=name, names=(p_name+'_raw', name), shapes=((), ()))

        self._measured_param = measured_param


        p_label = getattr(measured_param, 'label', None)
        p_unit = getattr(measured_param, 'unit', None)

        self.labels = (p_label, 'Phase')
        self.units = (p_unit, 'degrees')

    def get(self):
        volt = self._measured_param.get()
        phase =  volt * 18

        value = (volt, phase)
        self._save_val(value)
        return value