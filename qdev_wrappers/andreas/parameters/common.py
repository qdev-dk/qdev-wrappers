# -*- coding: utf-8 -*-
"""
Created on Fri May 31 11:58:18 2019

@author:  Andreas
"""

from qcodes.instrument.parameter import Parameter


class Common(Parameter):    
    def __init__(self, name, label, unit, parameter_list, offset_value_list=None):
        '''Accesses the common mode of multiple parameters. Sets them to the same value,
        if init_value_list is given all values are offset by that value.'''
        super().__init__(name=name, label=label, unit=unit,get_cmd=self.get_value, set_cmd=self.set_value)
        self.parameters = parameter_list
        if offset_value_list != None:
            self.offset  = offset_value_list
        else:
            self.offset_value_list=[0]*len(parameter_list)
        self.val=None
        print('Created common parameter ', name, ' out of: \n')
        print( 'name', '  ,', 'label', '  ,', 'value', '\n' )
        
        for ind, param in enumerate(self.parameters):
            print( param.name, '  ,', param.label, '  ,', str(param.get()), ' offset by', str(self.offset_value_list[ind]), '\n' )
        print('WARNING, setting the common parameter, will change all parameters to the same value shifted by an offset.')
#        self.add_parameter('value',
#                           get_cmd=self.get_value,
#                           set_cmd=self.set_value)
        
    def get_value(self):
        return self.val

    def set_value(self, x):
        self.val=x
        for ind, param in enumerate(self.parameters):
            param.set(x+self.offset_value_list[ind])