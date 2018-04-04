from typing import Callable

from qcodes.instrument.parameter import Parameter, MultiParameter
from qcodes.utils import validators


class GroupSetParameter(Parameter):
    """
    Group a number of parameters to be set simultaneaously.
    >>> p = GroupSetParameter('bound_channels', qdac.ch01.v, qdac.ch02.v)
    >>> p(1)
    here qdac.ch01.v and qdac.ch02.v will both set to 1V

    Beware that setting a stepping does apply to this parameter
    and is not inherited to the group of parameters.

    max_val_age not supported
    """
    def __init__(self,
                 name: str,
                 *parameters,
                 pre_set: Callable=None,
                 post_set: Callable=None,
                 **base_kwargs) -> None:
        # this class has a different footprint that the Parameter base class
        # because here the args must be given as kwargs.
        # this is fine for the Instrument.add_parameter method as it uses
        # kwargs.

        # type checking for compatibility
        if not all(isinstance(parameter, Parameter)
                   for parameter in parameters):
            raise RuntimeError("All supplied parameters must be of type Parameter")
        # include multiparameter and arrayparameter case at some point
        if any(isinstance(parameter, MultiParameter)
               for parameter in parameters):
            raise RuntimeError("Multiparameter not yet supported")
        # donnot allow for set_cmd/get_cmd
        if 'set_cmd' in base_kwargs:
            raise RuntimeError("Cannot supply set command to GroupSetParameter, because it is defined by setting the individual parameters. Use pre_set and post_set instead.")
        if 'get_cmd' in base_kwargs:
            raise RuntimeError("GroupSetParameter is nongettable.")

        # do not check for argument footprint of set functions

        # check that all units are identical
        if len(set(parameter.unit
                   for parameter in parameters)) > 1:
            raise RuntimeError("All supplied parameters must have the same unit")
        if not all(hasattr(parameter, 'set') for parameter in parameters):
            raise RuntimeError("All supplied parameters must have a set method")

        # construct label if not supplied
        if 'label' not in base_kwargs:
            labels = [parameter.label
                      for parameter in parameters
                      if parameter.label is not None]
            if not len(labels) == 0:
                base_kwargs['label'] = 'Group of {}'.format(labels[0])

        # use a MultitType validator, to only allow values that are allowed for
        # all parameters and the validator supplied to this parameter
        validator_list = [parameter.vals for parameter in parameters]
        if 'vals' in base_kwargs:
            validator_list.append(base_kwargs['vals'])
        base_kwargs['vals'] = validators.MultiType(*validator_list)

        # add post_set and pre_set callables
        self._pre_set = pre_set
        self._post_set = post_set

        self._parameters = parameters
        super().__init__(name,**base_kwargs)

    def set_raw(self, *args, **kwargs):
        if self._pre_set is not None:
            self._pre_set(*args, **kwargs)

        for p in self._parameters:
            p.set(*args, **kwargs)

        if self._post_set is not None:
            self._post_set(*args, **kwargs)
