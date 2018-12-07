from qdev_wrappers.customised_instruments.parameters.delegate_parameters import DelegateParameter, DelegateArrayParameter, DelegateMultiParameter
import logging

logger = logging.getLogger(__name__)


class SettingsParameter(DelegateParameter):
    def __init__(self, name, source, settings_instr, **kwargs):
        self._settings_instr = settings_instr
        super().__init__(name, source, **kwargs)

    def _to_saveable_value(self):
        return {'value': self._latest['value'],
                'parameter': self.source.full_name}

    def set_raw(self, val):
        if self.source._latest['value'] != val:
            self.source(val)
        self._save_val(val)
        self._settings_instr._save_to_file()


class SettingsArrayParameter(DelegateArrayParameter):
    def to_saveable_value(self):
        return {'parameter': self.source.full_name}


class SettingsMultiParameter(DelegateMultiParameter):
    def to_saveable_value(self):
        return {'parameter': self.source.full_name}

    def set_raw(self):
        raise RuntimeError('Cannot set measurable parameter')


class SettingsMultiChannelParameter(DelegateMultiParameter):
    def to_saveable_value(self):
        return {'parameter': self._full_name}

    def set_raw(self):
        raise RuntimeError('Cannot set measurable parameter')
