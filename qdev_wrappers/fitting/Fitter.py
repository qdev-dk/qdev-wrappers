import qcodes as qc
import numpy as np

from qdev_wrappers.fitting.Converter import SQL_Converter, Legacy_Converter
from qdev_wrappers.fitting.Fitclasses import T1, T2
from scipy.optimize import curve_fit







class Fitter():
    
    def do_1d(self, xdata, ydata, fitclass, p0,**kwargs):
        
        if (p0==None and hasattr(fitclass,'guess')):
            p0 = getattr(fitclass,'guess')(xdata,ydata)      
            popt, pcov = curve_fit(fitclass.fun, xdata, ydata, p0=p0, **kwargs)
            return popt, pcov     
        elif p0!=None:
            popt, pcov = curve_fit(fitclass.fun, xdata, ydata, p0=p0, **kwargs)
            return popt, pcov 
        else:
            return "Could not find guess parameters for fit."
        

    def fit(self, data, fitclass, x=None, y=None, z=None, default_dependencies=False, dataname = None, cut='horizontal', p0=None,**kwargs):
        
        if type(fitclass) == type:  
            #Maybe I'm just an idiot, and this isn't necessary for the world-at-large, but 
            #I spent about 45 minutes trying to figure out what I broke before I realized 
            #that I just forgot the parentheses after the fitclass. So this is here for now.
            raise RuntimeError('It looks like there is something wrong with your fitclass(). Possibly you forgot the parentheses?')
        
        if (x==None or y==None) and default_dependencies==False:
            raise RuntimeError('Please either specify data for x, y (and optionally z) or set default_dependencies = True')
            
        if default_dependencies == True:
            dep_var = [key for key in data['dependencies'].keys()]
            indep_vars = [value for value in data['dependencies'].values()]
        
            if dataname==None:
                if len(dep_var) != 1:
                    raise RuntimeError('Dataset has more than one dataname. Choose dataname to be fitted from: {}.'.format(', '.join(dep_var)))
            
                indep_vars = indep_vars[0]
        
            else:
                if dataname not in dep_var:
                    raise RuntimeError('Dataname not in dataset. Input dataname was: \'{}\' while dataname(s) in dataset are: {}.'.format(dataname,', '.join(dep_var)))
            
                indep_vars = indep_vars[dep_var.index(dataname)]
                dep_var = [dataname]
            
                if len(indep_vars) > 2:
                    print('independent variables: {}'.format(indep_vars))
                    raise RuntimeError('That dataset seems to contain {} independent variables, which is {} too many.'.format(len(indep_vars), len(indep_vars)-2))

        
            if len(indep_vars) == 1:
                dimensions = 1
                x_dict = data[indep_vars[0]]
                y_dict = data[dep_var[0]] 
        
            if len(indep_vars) == 2:
                dimensions = 2
                x_dict = data[indep_vars[0]]
                y_dict = data[indep_vars[1]]
                z_dict = data[dep_var[0]]
            
            
        elif default_dependencies == False:
            
            for dataname in [x, y, z]:
                if (dataname not in data['variables']) and (dataname is not None):
                    raise RuntimeError('The specified variable "{}" is not found in the variables for this data dictionary. Variables are {}'.format(dataname, data['variables']))
                    
            x_dict = data[x]
            y_dict = data[y]
            dimensions = 1
            
            if z != None:
                z_dict = data[z]
                dimensions = 2

        # find parameter units
        if dimensions == 1:
            cut = 'horizontal'  #Must be horizontal for 1D plots for units to work. Now you can't mess it up.
        unit_template = fitclass.p_units
        param_units = []
        x = x_dict['unit']
        y = y_dict['unit']
        if dimensions == 2:
            z = z_dict['unit']

        for item in unit_template:
            template = list(item)
            if cut == 'horizontal':
                for i in range(len(template)):
                    if template[i] == 'x':
                        template[i] = x
                    if template[i] == 'y':
                        template[i] = y
                    if template[i] == 'z':
                        template[i] = z
            elif cut == 'vertical':
                for i in range(len(template)):
                    if template[i] == 'x':
                        template[i] = y
                    if template[i] == 'y':
                        template[i] = x
                    if template[i] == 'z':
                        template[i] = z
            unit = "".join(template)
            param_units.append(unit)
    
        #Do fit for 1D data
        if dimensions == 1:
            
            xdata = x_dict['data']     
            ydata = y_dict['data'] 
            
            fit1d = {}
            fit1d['parameters'] = {}
                                                       
            popt, pcov = self.do_1d(xdata, ydata, fitclass, p0,**kwargs)
                
            for parameter in fitclass.p_labels:   #parameters currently missing units, use fitclass.p_units
                fit1d['parameters'][parameter] = {'value': popt[fitclass.p_labels.index(parameter)]}
                fit1d['parameters'][parameter]['cov'] = pcov[fitclass.p_labels.index(parameter)]
                fit1d['parameters'][parameter]['unit'] = param_units[fitclass.p_labels.index(parameter)]
            
            fit1d['estimator'] = {'method': 'Least squared fit',
                                  'type': fitclass.name, 
                                  'function': 'save all text from fitter function and class function here?',
                                  'more?' : 'perhaps'} 
   
            fit1d['inferred_from'] = {'xdata': x_dict['name'], 
                                            'ydata': y_dict['name'], 
                                            'dataset': data['data_id'],
                                            'dependencies': data['dependencies']} #missing sample name
                    
            
            return fit1d
        
        
        #Do fit for 2D data   
        if dimensions == 2:
            
            xdata = x_dict['data']    
            ydata = y_dict['data'] 
            zdata = z_dict['data'] 
            
            fits2d = {}
            
            if cut == 'horizontal':
                setarray = ydata
                xarray = xdata
                
            if cut == 'vertical':
                setarray = xdata
                xarray = ydata
            
            setpoints = np.unique(setarray)
            yarray = zdata
            
            #reformats as array of set points, with a y-array and z-array corresponding to each set point
            
            xdata_lst = []
            ydata_lst = []
            
            for set_point in setpoints:
                x_dat = []
                y_dat = []         
                for setpoint, x, y in zip(setarray, xarray, yarray): 
                    if setpoint == set_point:
                        x_dat.append(x)
                        y_dat.append(y)
                xdata_lst.append(np.array(x_dat))
                ydata_lst.append(np.array(y_dat))
                                  
            
            xdata = np.array(xdata_lst)
            ydata = np.array(ydata_lst)  
            
            
            #fitting as a sequence of 1D plots for different set_values
            
            for set_value, xdata_1d, ydata_1d in zip(setpoints, xdata, ydata):
                
                popt, pcov = self.do_1d(xdata_1d, ydata_1d, fitclass, p0,**kwargs)
                
                fits2d[set_value] = {}
                fits2d[set_value]['parameters'] = {}
                
                for parameter in fitclass.p_labels:            #parameters currently missing units, use fitclass.p_units
                    fits2d[set_value]['parameters'][parameter] = {'value': popt[fitclass.p_labels.index(parameter)]}
                    fits2d[set_value]['parameters'][parameter]['cov'] = pcov[fitclass.p_labels.index(parameter)]
                    fits2d[set_value]['parameters'][parameter]['unit'] = param_units[fitclass.p_labels.index(parameter)]
            

            fits2d['estimator'] = {'method': 'Least squared fit',
                                  'type': fitclass.name, 
                                  'function': 'save all text from fitter function and class function here?',
                                  'more?' : 'perhaps'}
            
            
            #does this needs to be moved so that it specifies which cut the individual sets of parameters are inferred from? 
            fits2d['inferred_from'] = {'xdata': x_dict['name'],  
                                            'ydata': y_dict['name'], 
                                            'zdata': z_dict['name'],
                                            'dataset': data['data_id'],
                                            'dependencies': data['dependencies']} #missing sample name

            if cut == 'horizontal':
                fits2d['inferred_from']['setpoints'] = 'ydata'

            if cut == 'vertical':
                fits2d['inferred_from']['setpoints'] = 'xdata'


            return fits2d            
        

