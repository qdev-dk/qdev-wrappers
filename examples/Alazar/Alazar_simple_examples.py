# -*- coding: utf-8 -*-
"""
Simple examples of using the alazar meant to be used with the alazar station 
config example
"""
import qcodes as qc
from qdev_wrappers.alazar_controllers.alazar_channel import AlazarChannel

alazar_ctrl.int_delay(2e-7)
alazar_ctrl.int_time(2e-6)

#%%

alazar_sample_chan.num_averages(1000)

alazar_sample_chan.alazar_channel('A')
alazar_sample_chan.prepare_channel()

# Measure this 
data1 = qc.Measure(alazar_sample_chan.data).run()
qc.MatPlot(data1.AlazarController_AlazarSampleChannel_data)

#%%


alazar_records_chan.num_averages(1000)
alazar_records_chan.records_per_buffer(100)
alazar_records_chan.alazar_channel('A')
alazar_records_chan.prepare_channel()

# Measure this 
data1 = qc.Measure(alazar_records_chan.data).run()
qc.MatPlot(data1.AlazarController_AlazarRecordChannel_data)

#%%


alazar_buffer_chan.num_averages(1000)
alazar_buffer_chan.buffers_per_acquisition(100)
alazar_buffer_chan.alazar_channel('A')
alazar_buffer_chan.prepare_channel()

# Measure this 
data1 = qc.Measure(alazar_buffer_chan.data).run()
qc.MatPlot(data1.AlazarController_AlazarBufferChannel_data)

#%% 


alazar_sample_record_chan.records_per_buffer(100)
alazar_sample_record_chan.num_averages(1000)
alazar_sample_record_chan.alazar_channel('A')
alazar_sample_record_chan.prepare_channel()

# Measure this 
data1 = qc.Measure(alazar_sample_record_chan.data).run()
qc.MatPlot(data1.AlazarController_AlazarSampleRecordChannel_data)

#%% 


alazar_sample_buffer_chan.buffers_per_acquisition(100)
alazar_sample_buffer_chan.num_averages(1000)
alazar_sample_buffer_chan.alazar_channel('A')
alazar_sample_buffer_chan.prepare_channel()

# Measure this 
data1 = qc.Measure(alazar_sample_buffer_chan.data).run()
qc.MatPlot(data1.AlazarController_AlazarSampleBufferChannel_data)

#%%


alazar_record_buffer_chan.buffers_per_acquisition(100)
alazar_record_buffer_chan.records_per_buffer(100)
#alazar_record_buffer_chan.num_averages(1000)
alazar_record_buffer_chan.alazar_channel('A')
alazar_record_buffer_chan.prepare_channel()

# Measure this 
data1 = qc.Measure(alazar_record_buffer_chan.data).run()
qc.MatPlot(data1.AlazarController_AlazarRecordBufferChannel_data)
