from qcodes.instrument.parameter import Parameter

class GroupSetParameter(Parameter):

    def __init__(self, name, *parameters, **base_kwargs):
        if not all(isinstance(parameter, Parameter)
                   for parameter in parameters):
            raise RuntimeError("All supplied parameters must be of type Parameter")
        # include multiparameter and arrayparameter case at some point
        if len(set(parameter.unit
                   for parameter in parameters)) > 1:
            raise RuntimeError("All supplied parameters must have the same unit")
        if not all(hasattr(parameter, 'set') for parameter in parameters):
            raise RuntimeError("All supplied parameters must have a set method")

        # construct label if not supplied
        if 'label' not in base_kwargs:
            labels = (parameter.label
                    for parameter in parameters
                    if parameter.label is not None)
            if not len(labels) == 0:
                base_kwargs['label'] = 'Group of {}'.format(labels[0])
            

        self._parameters = parameters

