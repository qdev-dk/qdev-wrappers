import logging
from typing import Sequence, Optional

import numpy as np

from qcodes import Parameter, ArrayParameter
from qcodes.instrument.channel import MultiChannelInstrumentParameter

logger = logging.getLogger(__name__)


class Alazar0DParameter(Parameter):
    def __init__(self,
                 name: str,
                 instrument,
                 label: str,
                 unit: str,
                 average_buffers: bool=True,
                 average_records: bool=True,
                 integrate_samples: bool=True) -> None:
        self._integrate_samples = integrate_samples
        self._average_records = average_records
        self._average_buffers = average_buffers

        super().__init__(name,
                         unit=unit,
                         label=label,
                         snapshot_get=False,
                         instrument=instrument)

    def get_raw(self) -> float:
        channel = self._instrument
        cntrl = channel._parent
        alazar_channels = 2
        cntrl.active_channels_nested = [
            {'ndemods': 0,
             'nsignals': 0,
             'demod_freqs': [],
             'demod_types': [],
             'numbers': [],
             'raw': False} for _ in range(alazar_channels)]
        alazar_channel = channel.alazar_channel.raw_value
        channel_info = cntrl.active_channels_nested[alazar_channel]
        channel_info['nsignals'] = 1
        if channel._demod:
            channel_info['ndemods'] = 1
            channel_info['demod_freqs'].append(channel.demod_freq.get())
            channel_info['demod_types'].append(channel.demod_type.get())
        else:
            channel_info['raw'] = True
        cntrl.shape_info['average_buffers'] = channel._average_buffers
        cntrl.shape_info['average_records'] = channel._average_records
        cntrl.shape_info['integrate_samples'] = channel._integrate_samples
        cntrl.shape_info['output_order'] = [0]
        params_to_kwargs = ['samples_per_record', 'records_per_buffer',
                            'buffers_per_acquisition', 'allocated_buffers']
        acq_kwargs = self._instrument.acquisition_kwargs.copy()
        controller_acq_kwargs = {key: val.get() for key, val in cntrl.parameters.items() if
                                 key in params_to_kwargs}
        channel_acq_kwargs = {key: val.get() for key, val in channel.parameters.items() if
                              key in params_to_kwargs}
        acq_kwargs.update(controller_acq_kwargs)
        acq_kwargs.update(channel_acq_kwargs)
        if acq_kwargs['buffers_per_acquisition'] > 1:
            acq_kwargs['allocated_buffers'] = 4
        else:
            acq_kwargs['allocated_buffers'] = 1

        output = self._instrument._parent._get_alazar().acquire(
            acquisition_controller=self._instrument._parent,
            **acq_kwargs)
        logger.info("calling acquire with {}".format(acq_kwargs))
        return output


class AlazarNDParameter(ArrayParameter):
    def __init__(self,
                 name: str,
                 shape: Sequence[int],
                 instrument,
                 label: str,
                 unit: str,
                 average_buffers: bool=True,
                 average_records: bool=True,
                 integrate_samples: bool=True,
                 setpoint_names=None,
                 setpoint_labels=None,
                 setpoint_units=None) -> None:
        self._integrate_samples = integrate_samples
        self._average_records = average_records
        self._average_buffers = average_buffers
        super().__init__(name,
                         shape=shape,
                         instrument=instrument,
                         label=label,
                         unit=unit,
                         setpoint_names=setpoint_names,
                         setpoint_labels=setpoint_labels,
                         setpoint_units=setpoint_units)

    def get_raw(self) -> np.ndarray:
        channel = self._instrument
        if channel._stale_setpoints:
            raise RuntimeError(
                "Must run prepare channel before capturing data.")
        cntrl = channel._parent
        cntrl.shape_info = {}
        alazar_channels = 2
        cntrl.active_channels_nested = [
            {'ndemods': 0,
             'nsignals': 0,
             'demod_freqs': [],
             'demod_types': [],
             'numbers': [],
             'raw': False} for _ in range(alazar_channels)]
        alazar_channel = channel.alazar_channel.raw_value
        channel_info = cntrl.active_channels_nested[alazar_channel]
        channel_info['nsignals'] = 1
        if channel._demod:
            channel_info['ndemods'] = 1
            channel_info['demod_freqs'].append(channel.demod_freq.get())
            channel_info['demod_types'].append(channel.demod_type.get())
        else:
            channel_info['raw'] = True
        cntrl.shape_info['average_buffers'] = channel._average_buffers
        cntrl.shape_info['average_records'] = channel._average_records
        cntrl.shape_info['integrate_samples'] = channel._integrate_samples
        cntrl.shape_info['output_order'] = [0]

        params_to_kwargs = ['samples_per_record', 'records_per_buffer',
                            'buffers_per_acquisition', 'allocated_buffers']
        acq_kwargs = self._instrument.acquisition_kwargs.copy()
        controller_acq_kwargs = {key: val.get() for key, val in cntrl.parameters.items() if
                                 key in params_to_kwargs}
        channel_acq_kwargs = {key: val.get() for key, val in channel.parameters.items() if
                              key in params_to_kwargs}
        acq_kwargs.update(controller_acq_kwargs)
        acq_kwargs.update(channel_acq_kwargs)
        if acq_kwargs['buffers_per_acquisition'] > 1:
            acq_kwargs['allocated_buffers'] = 4
        else:
            acq_kwargs['allocated_buffers'] = 1

        logger.info("calling acquire with {}".format(acq_kwargs))
        output = self._instrument._parent._get_alazar().acquire(
            acquisition_controller=self._instrument._parent,
            **acq_kwargs)
        return output


class Alazar1DParameter(AlazarNDParameter):
    def __init__(self,
                 name: str,
                 instrument,
                 label: str,
                 unit: str,
                 average_buffers: bool=True,
                 average_records: bool=True,
                 integrate_samples: bool=True,
                 shape: Sequence[int] = (1,)):

        if not integrate_samples:
            setpoint_names = ('time',)
            setpoint_labels = ('Time',)
            setpoint_units = ('s',)
        elif not average_records:
            setpoint_names = ('records',)
            setpoint_labels = ('Records',)
            setpoint_units = ('',)
        elif not average_buffers:
            setpoint_names = ('buffers',)
            setpoint_labels = ('Buffers',)
            setpoint_units = ('',)
        super().__init__(name,
                         unit=unit,
                         instrument=instrument,
                         label=label,
                         shape=shape,
                         average_buffers=average_buffers,
                         average_records=average_records,
                         integrate_samples=integrate_samples,
                         setpoint_names=setpoint_names,
                         setpoint_labels=setpoint_labels,
                         setpoint_units=setpoint_units)

    def set_setpoints_and_labels(self,
                                 setpoints=None,
                                 setpoint_name=None,
                                 setpoint_label=None,
                                 setpoint_unit=None) -> None:

        if not self._integrate_samples:
            samples = self._instrument._parent.samples_per_record.get()
            sample_rate = self._instrument._parent._get_alazar().get_sample_rate()
            start = 0
            stop = samples / sample_rate
            self.shape = (samples,)
            self.setpoints = (
                tuple(np.linspace(start, stop, samples, endpoint=False)),)
            self.setpoint_names = ('time',)
            self.setpoint_labels = ('Time',)
            self.setpoint_units = ('S',)
            return
        if setpoint_name is not None:
            self.setpoint_names = (setpoint_name,)
        if setpoint_label is not None:
            self.setpoint_labels = (setpoint_label,)
        if setpoint_unit is not None:
            self.setpoint_units = (setpoint_unit,)
        if not self._average_records:
            records = self._instrument.records_per_buffer.get()
            if setpoints is None and (self.setpoints is None or (len(self.setpoints[0]) != records)):
                self.setpoints = (tuple(np.arange(records)),)
            elif setpoints is not None:
                self.setpoints = (tuple(setpoints),)
            self.shape = (records,)
        elif not self._average_buffers:
            buffers = self._instrument.buffers_per_acquisition.get()
            if setpoints is None and (self.setpoints is None or len(self.setpoints[0]) != buffers):
                self.setpoints = (tuple(np.arange(buffers)),)
            elif setpoints is not None:
                self.setpoints = (tuple(setpoints),)
            self.shape = (buffers,)


class Alazar2DParameter(AlazarNDParameter):
    def __init__(self,
                 name: str,
                 instrument,
                 label: str,
                 unit: str,
                 average_buffers: bool=True,
                 average_records: bool=True,
                 integrate_samples: bool=True,
                 shape: Sequence[int] = (1, 1)) -> None:

        if average_buffers:
            setpoint_names = ('time', 'records')
            setpoint_labels = ('Time', 'Records')
            setpoint_units = ('s', '')
        elif average_records:
            setpoint_names = ('time', 'buffers')
            setpoint_labels = ('Time', 'Buffers')
            setpoint_units = ('s', '')
        else:
            setpoint_names = ('records', 'buffers')
            setpoint_labels = ('Records', 'Buffers')
            setpoint_units = ('', '')

        super().__init__(name,
                         unit=unit,
                         label=label,
                         shape=shape,
                         instrument=instrument,
                         average_buffers=average_buffers,
                         average_records=average_records,
                         integrate_samples=integrate_samples,
                         setpoint_names=setpoint_names,
                         setpoint_labels=setpoint_labels,
                         setpoint_units=setpoint_units)

    def set_setpoints_and_labels(self,
                                 record_setpoints=None,
                                 buffer_setpoints=None,
                                 record_setpoint_name=None,
                                 buffer_setpoint_name=None,
                                 record_setpoint_label=None,
                                 buffer_setpoint_label=None,
                                 record_setpoint_unit=None,
                                 buffer_setpoint_unit=None):
        records = self._instrument.records_per_buffer()
        buffers = self._instrument.buffers_per_acquisition()
        samples = self._instrument._parent.samples_per_record.get()

        if not self._average_buffers:
            outer_shape = buffers
            if buffer_setpoints is not None:
                outer_setpoints = tuple(buffer_setpoints,)
            elif self.setpoints is None or len(self.setpoints[-1]) != buffers:
                outer_setpoints = tuple(np.arange(buffers))
            else:
                outer_setpoints = self.setpoints[-1]
            if buffer_setpoint_name is not None:
                outer_setpoint_name = buffer_setpoint_name
            else:
                outer_setpoint_name = self.setpoint_names[-1]
            if buffer_setpoint_label is not None:
                outer_setpoint_label = buffer_setpoint_label
            else:
                outer_setpoint_label = self.setpoint_labels[-1]
            if buffer_setpoint_unit is not None:
                outer_setpoint_unit = buffer_setpoint_unit
            else:
                outer_setpoint_unit = self.setpoint_units[-1]

        if not self._integrate_samples:
            inner_shape = samples
            sample_rate = self._instrument._parent._get_alazar().get_sample_rate()
            stop = samples / sample_rate
            self.shape = (records, samples)
            inner_setpoints = tuple(np.linspace(
                0, stop, samples, endpoint=False))
            inner_setpoint_name = 'time'
            inner_setpoint_label = 'Time'
            inner_setpoint_unit = 's'

        if not self._average_records and not self._integrate_samples:
            outer_shape = records
            if record_setpoints is not None:
                outer_setpoints = tuple(record_setpoints,)
            elif self.setpoints is None or len(self.setpoints[-1]) != records:
                outer_setpoints = tuple(np.arange(records))
            else:
                outer_setpoints = self.setpoints[-1]
            if record_setpoint_name is not None:
                outer_setpoint_name = record_setpoint_name
            else:
                outer_setpoint_name = self.setpoint_names[-1]
            if record_setpoint_label is not None:
                outer_setpoint_label = record_setpoint_label
            else:
                outer_setpoint_label = self.setpoint_labels[-1]
            if record_setpoint_unit is not None:
                outer_setpoint_unit = record_setpoint_unit
            else:
                outer_setpoint_unit = self.setpoint_units[-1]
        elif not self._average_records and not self._average_buffers:
            inner_shape = records
            if record_setpoints is not None:
                inner_setpoints = tuple(record_setpoints,)
            elif self.setpoints is None or len(self.setpoints[0]) != records:
                inner_setpoints = tuple(np.arange(records))
            else:
                inner_setpoints = self.setpoints[0]
            if record_setpoint_name is not None:
                inner_setpoint_name = record_setpoint_name
            else:
                inner_setpoint_name = self.setpoint_names[0]
            if record_setpoint_label is not None:
                inner_setpoint_label = record_setpoint_label
            else:
                inner_setpoint_label = self.setpoint_labels[0]
            if record_setpoint_unit is not None:
                inner_setpoint_unit = record_setpoint_unit
            else:
                inner_setpoint_unit = self.setpoint_units[-1]

        if outer_shape == 1:
            self.shape = (inner_shape,)
            self.setpoints = (inner_setpoints,)
            self.setpoint_names = (inner_setpoint_name,)
            self.setpoint_labels = (inner_setpoint_label,)
            self.setpoint_units = (inner_setpoint_unit,)
        elif inner_shape == 1:
            self.shape = (outer_shape,)
            self.setpoints = (outer_setpoints,)
            self.setpoint_names = (outer_setpoint_name,)
            self.setpoint_labels = (outer_setpoint_label,)
            self.setpoint_units = (outer_setpoint_unit,)
        else:
            self.shape = (outer_shape, inner_shape)
            self.setpoints = (outer_setpoints, tuple(
                inner_setpoints for _ in range(len(outer_setpoints))))
            self.setpoint_names = (outer_setpoint_name, inner_setpoint_name)
            self.setpoint_labels = (outer_setpoint_label, inner_setpoint_label)
            self.setpoint_units = (outer_setpoint_name, inner_setpoint_unit)


class AlazarMultiChannelParameter(MultiChannelInstrumentParameter):
    """


    """
    
    def get_raw(self) -> np.ndarray:
        if self._param_name == 'data':
            channel = self._channels[0]
            cntrl = channel._parent
            instrument = cntrl._get_alazar()
            cntrl.shape_info = {}
            alazar_channels = 2
            cntrl.active_channels_nested = [
                {'ndemods': 0,
                 'nsignals': 0,
                 'demod_freqs': [],
                 'demod_types': [],
                 'demod_order': [],
                 'raw_order': [],
                 'numbers': [],
                 'raw':False} for _ in range(alazar_channels)]

            for i, channel in enumerate(self._channels):
                # change this to use raw value once mapping is
                # complete
                alazar_channel = channel.alazar_channel.raw_value
                channel_info = cntrl.active_channels_nested[alazar_channel]
                channel_info['nsignals'] += 1

                if channel._demod:
                    channel_info['ndemods'] += 1
                    channel_info['demod_order'].append(i)
                    channel_info['demod_freqs'].append(
                        channel.demod_freq.get())
                    channel_info['demod_types'].append(
                        channel.demod_type.get())
                else:
                    channel_info['raw'] = True
                    channel_info['raw_order'].append(i)
                cntrl.shape_info['average_buffers'] = channel._average_buffers
                cntrl.shape_info['average_records'] = channel._average_records
                cntrl.shape_info['integrate_samples'] = channel._integrate_samples
                cntrl.shape_info['channel'] = channel.alazar_channel.get()

            output_order = []
            for achan in cntrl.active_channels_nested:
                output_order += achan['raw_order']
                output_order += achan['demod_order']
            cntrl.shape_info['output_order'] = output_order
            params_to_kwargs = ['samples_per_record', 'records_per_buffer',
                                'buffers_per_acquisition', 'allocated_buffers']
            acq_kwargs = channel.acquisition_kwargs.copy()
            controller_acq_kwargs = {key: val.get() for key, val in cntrl.parameters.items() if
                                     key in params_to_kwargs}
            channels_acq_kwargs = []
            for i, channel in enumerate(self._channels):
                channels_acq_kwargs.append({key: val.get() for key, val in channel.parameters.items() if
                                            key in params_to_kwargs})
                if channels_acq_kwargs[i] != channels_acq_kwargs[0]:
                    raise RuntimeError(
                        "Found non matching kwargs. Got {} and {}".format(
                            channels_acq_kwargs[0],
                            channels_acq_kwargs[i]))
            acq_kwargs.update(controller_acq_kwargs)
            acq_kwargs.update(channels_acq_kwargs[0])
            if acq_kwargs['buffers_per_acquisition'] > 1:
                acq_kwargs['allocated_buffers'] = 4
            else:
                acq_kwargs['allocated_buffers'] = 1

            logger.info("calling acquire with {}".format(acq_kwargs))
            output = instrument.acquire(
                acquisition_controller=cntrl,
                **acq_kwargs)
        else:
            output = tuple(chan.parameters[self._param_name].get()
                           for chan in self._channels)
        return output