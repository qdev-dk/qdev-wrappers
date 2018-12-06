from qcodes.instrument.parameter import Parameter

# TODO: doctrings

class InterfaceParameter(Parameter):
    def __init__(self, name, source=None, get_fn=None,
                 set_fn=None, *args, **kwargs):
        self._source = source
        self._set_fn = set_fn
        self._get_fn = get_fn
        super().__init__(name=name, *args, **kwargs)

    def get_raw(self):
        if self._source is not None:
            return self.source.get()
        elif self._get_fn is not None:
            return self._get_fn()
        else:
            return self._latest['value']

    def set_raw(self, val):
        if self._source is not None:
            self.source.set(val)
        elif self._set_fn is False:
            raise RuntimeError(f'Parmeter {self.name} not settable')
        elif self._set_fn is not None:
            self._set_fn(val)
