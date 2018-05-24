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
                 integrate_samples: bool=True) -> None:
        self._integrate_samples = integrate_samples
        self._average_records = average_records
        self._average_buffers = average_buffers

        if not integrate_samples:
            setpoint_names = ('time',)
            setpoint_labels = ('time',)
            setpoint_units = ('s',)
        if not average_records:
            setpoint_names = ('records',)
            setpoint_labels = ('Records',)
            setpoint_units = ('',)
        if not average_buffers:
            setpoint_names = ('buffers',)
            setpoint_labels = ('Buffers',)
            setpoint_units = ('',)
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

        super().__init__(name,
                         unit=unit,
                         instrument=instrument,
                         label=label,
                         shape=shape,
                         average_buffers=average_buffers,
                         average_records=average_records,
                         integrate_samples=integrate_samples)

    def set_setpoints_and_labels(self,
                                 record_setpoints=None,
                                 buffer_setpoints=None,
                                 record_setpoint_name=None,
                                 record_setpoint_label=None,
                                 record_setpoint_unit=None,
                                 buffer_setpoint_name=None,
                                 buffer_setpoint_label=None,
                                 buffer_setpoint_unit=None) -> None:


        r_checklist = [record_setpoint_name, record_setpoint_label,
                       record_setpoint_unit, record_setpoints]
        b_checklist = [buffer_setpoint_name, buffer_setpoint_label,
                       buffer_setpoint_unit, buffer_setpoints]
        if not self._integrate_samples:
            if (any([rb is not None for rb in r_checklist+b_checklist])):
                print(r_checklist, b_checklist)
                raise RuntimeError(
                    'Not allowed record or buffer setpoints when averaging'
                    ' over records and buffers')
            samples = self._instrument._parent.samples_per_record.get()
            sample_rate = self._instrument._parent._get_alazar().get_sample_rate()
            start = 0
            stop = samples / sample_rate
            self.shape = (samples,)
            self.setpoints = (tuple(np.linspace(start, stop, samples, endpoint=False)),)
            self.setpoint_names = ('time',)
            self.setpoint_labels = ('Time',)
            self.setpoint_units = ('S',)
        elif not self._average_records:
            if any([b is not None for b in b_checklist]):
                raise RuntimeError(
                    'Not allowed buffer setpoints, setpoint names labels '
                    'or units when averaging over buffers')
            records = self._instrument.records_per_buffer.get()
            if record_setpoints is None:
                record_setpoints = np.arange(records)
            self.shape = (records,)
            self.setpoints = (tuple(record_setpoints),)
            self.setpoint_names = (record_setpoint_name or 'records',)
            self.setpoint_labels = (record_setpoint_label or 'Records',)
            self.setpoint_units = (record_setpoint_unit or '',)
        elif not self._average_buffers:
            if any([r is not None for r in r_checklist]):
                raise RuntimeError(
                    'Not allowed record setpoints, setpoint names labels '
                    'or units when averaging over records')
            buffers = self._instrument.buffers_per_acquisition.get()
            if buffer_setpoints is None:
                buffer_setpoints = np.arange(buffers)
            self.shape = (buffers,)
            self.setpoints = (tuple(buffer_setpoints),)
            self.setpoint_names = (buffer_setpoint_name or 'buffers',)
            self.setpoint_labels = (buffer_setpoint_label or 'Buffers',)
            self.setpoint_units = (buffer_setpoint_unit or '',)


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
        self._integrate_samples = integrate_samples
        self._average_records = average_records
        self._average_buffers = average_buffers

        super().__init__(name,
                         unit=unit,
                         label=label,
                         shape=shape,
                         instrument=instrument,
                         average_buffers=average_buffers,
                         average_records=average_records,
                         integrate_samples=integrate_samples)

    def set_setpoints_and_labels(self,
                                 record_setpoints=None,
                                 buffer_setpoints=None,
                                 record_setpoint_name=None,
                                 record_setpoint_label=None,
                                 record_setpoint_unit=None,
                                 buffer_setpoint_name=None,
                                 buffer_setpoint_label=None,
                                 buffer_setpoint_unit=None):
        records = self._instrument.records_per_buffer()
        buffers = self._instrument.buffers_per_acquisition()
        samples = self._instrument._parent.samples_per_record.get()

        r_checklist = [record_setpoint_name, record_setpoint_label,
                       record_setpoint_unit, record_setpoints]
        b_checklist = [buffer_setpoint_name, buffer_setpoint_label,
                       buffer_setpoint_unit, buffer_setpoints]
        if self._integrate_samples:
            self.shape = (buffers, records)
            if record_setpoints is None:
                inner_setpoints = tuple(np.arange(records))
            else:
                inner_setpoints = record_setpoints
            if buffer_setpoints is None:
                outer_setpoints = tuple(np.arange(buffers))
            else:
                outer_setpoints = buffer_setpoints
            setpoint_names = (buffer_setpoint_name or 'buffers',
                              record_setpoint_name or 'records')
            setpoint_labels = (buffer_setpoint_label or 'Buffers',
                               record_setpoint_label or 'Records')
            setpoint_units = (buffer_setpoint_unit or '',
                              record_setpoint_unit or '')
        elif self._average_records:
            if any([r is not None for r in r_checklist]):
                raise RuntimeError(
                    'Not allowed record setpoints, setpoint names labels '
                    'or units when averaging over records')
            sample_rate = self._instrument._parent._get_alazar().get_sample_rate()
            stop = samples / sample_rate
            self.shape = (buffers, samples)
            inner_setpoints = tuple(np.linspace(0, stop, samples, endpoint=False))
            if buffer_setpoints is None:
                outer_setpoints = tuple(np.arange(buffers))
            else:
                outer_setpoints = buffer_setpoints
            setpoint_names = (buffer_setpoint_name or 'buffers', 'time')
            setpoint_labels = (buffer_setpoint_label or 'Buffers', 'Time')
            setpoint_units = (buffer_setpoint_unit or '', 'S')
        elif self._average_buffers:
            if any([b is not None for b in b_checklist]):
                raise RuntimeError(
                    'Not allowed buffer setpoints, setpoint names labels '
                    'or units when averaging over buffers')
            sample_rate = self._instrument._parent._get_alazar().get_sample_rate()
            stop = samples / sample_rate
            self.shape = (records, samples)
            inner_setpoints = tuple(np.linspace(0, stop, samples, endpoint=False))
            if record_setpoints is None:
                outer_setpoints = tuple(np.arange(records))
            else:
                outer_setpoints = record_setpoints
            setpoint_names = (record_setpoint_name or 'records', 'time')
            setpoint_labels = (record_setpoint_label or 'Records', 'Time')
            setpoint_units = (record_setpoint_unit or '', 'S')
        else:
            raise RuntimeError("Non supported Array type")
        self.setpoints = (outer_setpoints, tuple(
            inner_setpoints for _ in range(len(outer_setpoints))))
        self.setpoint_names = setpoint_names
        self.setpoint_labels = setpoint_labels
        self.setpoint_units = setpoint_units


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
