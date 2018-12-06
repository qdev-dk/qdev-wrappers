from qcodes.instrument.parameter import Parameter


class InterfaceParameter(Parameter):
    def __init__(self, name, source=None, get_fn=None,
                 set_fn=None, *args, **kwargs):
    """
    Parameter which by default behaves like ManualParameter but can
    be easily configured to get/set a source parameter or run a
    function when get/set is called. The functions if specified
    have priority over the source. If a function is False
    it means the parameter cannot be get/set.
    """
        self._source = source
        self._set_fn = set_fn
        self._get_fn = get_fn
        super().__init__(name=name, *args, **kwargs)

    def get_raw(self):
        if self._get_fn is False:
            raise RuntimeError(f'Parmeter {self.name} not gettable')
        elif self._get_fn is not None:
            return self._get_fn()
        elif self._source is not None:
            return self.source.get()
        else:
            return self._latest['value']

    def set_raw(self, val):
        if self._set_fn is False:
            raise RuntimeError(f'Parmeter {self.name} not settable')
        elif self._set_fn is not None:
            self._set_fn(val)
        elif self._source is not None:
            self.source.set(val)
