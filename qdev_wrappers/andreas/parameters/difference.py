# -*- coding: utf-8 -*-
"""
Created on Fri May 31 11:58:18 2019

@author:  Andreas
"""

from qcodes.instrument.parameter import Parameter


class Difference(Parameter):    
    def __init__(self, name, label, unit, parameters_plus_list, parameters_minus_list, setpoint=None):
        '''Unifies parameters, such that they have the same value and can be 
        swept together as one unit with common value.'''
        super().__init__(name=name, label=label, unit=unit,get_cmd=self.get_value, set_cmd=self.set_value)
        self.parameters_plus = parameters_plus_list
        self.parameters_minus = parameters_minus_list
        self.setpoint = setpoint
        self.val=None
        print('Created difference parameter ', name, ' out of: \n')
        print( 'name', '  ,', 'label', '  ,', 'value', '\n' )
        for param in self.parameters_plus:
            print( param.name, '  ,', param.label, '  ,', str(param.get()), '\n' ) 
        for param in self.parameters_minus:
            print( param.name, '  ,', param.label, '  ,', str(param.get()), '\n' )
        print('WARNING, setting the diff parameter, will set parameters to offset by the difference value!')
#        self.add_parameter('value',
#                           get_cmd=self.get_value,
#                           set_cmd=self.set_value)
        
    def get_value(self):
        return self.val

    def set_value(self, x):
        for param in self.parameters_plus:
            param(self.setpoint + x/2.)
        for param in self.parameters_minus:
            param(self.setpoint -x/2.)
        self.val = x