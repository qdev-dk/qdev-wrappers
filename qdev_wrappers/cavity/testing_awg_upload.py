from pulsbuilding import waveform_builder_from_file
from qcodes.instrument_drivers.tektronix.AWG5014 import Tektronix_AWG5014  # <--- The instrument driver
from qcodes.instrument_drivers.tektronix.AWGFileParser import parse_awg_file  # <--- A helper function
from broadbean import Sequence

filename = "./experimental_puls_description.yml"

awg1 = Tektronix_AWG5014(name='AWG', address='TCPIP0::AWG-3289382193::inst0::INSTR', timeout=40)

base_parameters = {'readout_delay': 1e-3,
                   'readout_duration': 2e-3,
                   'readout_frequency': 10e3,
                   'readout_amplitude': 0.1,
                   'readout_stage_duration': 4e-3 ,
                   'readout_basename': 'channel'}
builder = waveform_builder_from_file(filename, 'simple_readout')
seq = Sequence()
seq.setSR(1e9)
for i in range(1000):
    base_parameters['readout_duration'] = i/1000000
    elem = builder(**base_parameters)
    seq.pushElement(elem)

# 7x
# seq.setChannelVoltageRange('channel_I', 0.3, 0)
# seq.setChannelVoltageRange('channel_Q', 0.3, 0)
seq.setChannelAmplitude('channel_I', 0.3)
seq.setChannelAmplitude('channel_Q', 0.3)
seq.setChannelOffset('channel_Q', 0)
seq.setChannelOffset('channel_I', 0)
package = seq.outputForAWGFile()
awg1.make_send_and_load_awg_file(*package[:])
