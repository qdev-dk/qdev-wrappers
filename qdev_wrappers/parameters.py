from qcodes.instrument.parameter import Parameter


class DelegateParameter(Parameter):

    def __init__(self, name: str, source: Parameter, *args, **kwargs):
        self.source = source
        super().__init__(name=name, *args, **kwargs)

    def get_raw(self, *args, **kwargs):
        return self.source.get(*args, **kwargs)

    def set_raw(self, *args, **kwargs):
        self.source(*args, **kwargs)

