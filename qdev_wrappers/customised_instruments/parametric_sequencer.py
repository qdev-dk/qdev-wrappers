from typing import Callable, Dict, List
from copy import deepcopy
import re
from itertools import compress
from functools import partial
from os.path import sep
import numpy as np
from qcodes import Station, Instrument
from qdev_wrappers.alazar_controllers.ATSChannelController import ATSChannelController
from qdev_wrappers.alazar_controllers.acquisition_parameters import NonSettableDerivedParameter
from qdev_wrappers.alazar_controllers.alazar_channel import AlazarChannel
from qdev_wrappers.transmon.file_helpers import get_subfolder_location
from qcodes.instrument.channel import InstrumentChannel
from qcodes import Parameter
logger = logging.getLogger(__name__)


class BuilderParameter(Parameter):
    """
    a pretty hack param used to save the name of the function used to build the
    sequence
    """

    def __init__(self,
                 name: str,
                 instrument,
                 label: str,
                 unit: str) -> None:

        super().__init__(name,
                         unit=unit,
                         label=label,
                         instrument=instrument)

    def set_raw(self, builder_fn):
        self._save_val(builder_fn.__name__)


class DictWithDefaultParameter(Parameter):
    """
    is there a better way of doing this? It's my idea for how to make the
    readable params which go into the builder stored without having to always
    set all of them
    """

    def __init__(self,
                 name: str,
                 instrument,
                 initial_val: Dict) -> None:
        self._default = default_dict
        super().__init__(name,
                         instrument=instrument,
                         initial_val=initial_val)

    def set_raw(self, val):
        new_dict = self._default.copy()
        new_dict.update(val)
        self._instrument._sequence_up_to_date = False
        self._save_val(new_dict)


class ParametricSequencer(Instruement):
    """
    Take a step back to make it more general, and keep the
    ParametricWaveforms in the background

    I've put in the awg and the idea is that now the parametric
    sequencer knows about whether or not the sequence on the awg is up to date,
    also stores the setpoints and dict for default params. These still need
    refactoring ot work with the interface we agree on and as a result the
    'update_sequence' function is more of a blueprint
    """
    default_inner_setpoints = {'name': 'records',
                               'label': 'Records',
                               'unit': '',
                               setpoints: None}
    default_outer_setpoints = {'name': 'buffers',
                               'label': 'Buffers',
                               'unit': '',
                               setpoints: None}

    def __init__(self, awg, default_builder_parms: Dict=None):
        self.awg = awg
        self.builder = None
        self.save_sequence_on_upload = True
        self._sequence_up_to_date = False
        self.add_parameter(name='seq_mode',
                           set_cmd=self._set_seq_mode,
                           get_cmd=self._get_seq_mode)
        self.add_parameter(name='builder',
                           set_cmd=self._set_sequence_builder,
                           parameter_class=BuilderParameter)
        self.add_parameter(name='inner_setpoints',
                           initial_val=default_inner_setpoints,
                           parameter_class=DictWithDefaultParameter)
        self.add_parameter(name='outer_setpoints',
                           initial_val=default_outer_setpoints,
                           parameter_class=DictWithDefaultParameter)
        self.add_parameter(name='default_builder_parms',
                           initial_val=default_builder_parms,
                           parameter_class=DictWithDefaultParameter)
        self.add_parameter(name='sequence_element_val',
                           set_cmd=self._set_seq_elem_val,
                           get_cmd=self._get_seq_elem_val)

    def _set_seq_elem_val(self, value):
        """
        assumes records == elements, and is for use when seq mode is off
        """
        if self.seq_mode():
            raise RuntimeError('must turn off sequence mode to'
                               ' set output of one element on loop')
        array = np.asarray(self.inner_setpoints()['setpoints'])
        idx = (np.abs(array - value)).argmin()
        self.awg.sequence_pos(idx)

    def _get_seq_elem_val(self, value):
        """
        assumes records == elements, and is for use when seq mode is off
        """
        if self.seq_mode():
            raise RuntimeError('must turn off sequence mode to'
                               ' set output of one element on loop')
        array = np.asarray(self.inner_setpoints()['setpoints'])
        return array[self.awg.sequence_pos(idx)]

    def _set_seq_mode(self, status):
        """
        not sure if seq mode needs to also live in the builder parms,
        probably that can go, otherwise point is to make awg play each elem
        infinitely many times until you manually switch to the next one
        """
        self.default_builder_parms({'seq_mode': status})
        if status:
            for i in range(self.sequence_length()):
                self.set_sqel_loopcnt(i, 1)
        else:
            for i in range(self.sequence_length()):
                self.set_sqel_loopcnt_to_inf(i)

    def _get_seq_mode(self):
        if self.set_sqel_loopcnt() == '1':
            awg_val = False
        else:
            print(self.set_sqel_loopcnt() +
                  'Fix me!! get seq mode of parametric sequencer')
            # TODO: need to check what it outputs for inf to make the
            # if/else secure
            awg_val = True
        if awg_val != self.default_builder_parms()['seq_mode']:
            raise RuntimeError('seq mode of awg does not match '
                               'paremeters of current sequence')
        else return awg_val

    def _create_sequence(self):  # -> bb.Sequence:
        """
        At the moment this makes a list of dictionaries and then gives this
        list to the function, you wanted this a different way so lets work
        on it together
        """
        seq_parms = []
        for setpoint in self.inner_setpoints()['setpoints']:
            parms = copy(self.default_builder_parms())
            parms.update({self.inner_setpoints()['name']: setpoint})
            seq_parms.append(parms)
        return self.builder(seq_parms)

    def update_sequence(self):
        """
        should create a sequence based on the builder fn, default params and
        setpoints and then
        upload it to the awg
        """
        seq = self._create_sequence()
        if save_sequence_on_upload:
            unwrapped_seq = sequence.unwrap()[0]
            awg_file = self.awg.make_awg_file(*unwrapped_seq)
            filename = sequence.name + '.awg'
            self.awg.send_and_load_awg_file(awg_file, filename)
            self.awg.all_channels_on()
            self.awg.run()
            if save_sequence:
                # TODO: remove dependence on file_helpers
                local_filename = sep.join(
                    [get_subfolder_location('waveforms'), filename])
                with open(local_filename, 'wb') as fid:
                    fid.write(awg_file)
        self._sequence_up_to_date = True

    def serialize(self) -> str:
        return "Not yet implemented"  # TODO:??

    def deserialize(self, str) -> None:
        pass  # TODO: ??
