import qcodes as qc
import numpy as np
from os.path import sep
from qcodes.dataset.data_export import get_data_by_id
from qcodes.dataset.sqlite_base import connect
from qdev_wrappers.file_setup import CURRENT_EXPERIMENT
from qdev_wrappers.show_num import check_experiment_is_initialized


def data_to_dict(id, samplefolder=None, datatype='SQL'):
    if datatype == 'qcodes_legacy':
        converter = Legacy_Converter()

    if datatype == 'SQL':
        converter = SQL_Converter()

    return converter.convert(id, samplefolder)


class DataConverter():
    
    def convert(self, id, samplefolder = None):
        
        data = self.find_data(id, samplefolder) 
        data_dict = self.make_data_dictionary(data)
        
        dependencies = self.find_dependencies(id, data)  #SQL needs only id number to find dependencies, Legacy needs only data
        all_variables = self.find_variables(data)
        
        data_dict['data_id'] = id
        data_dict['dependencies'] = dependencies
        data_dict['variables'] = all_variables
        
        return data_dict
    


class SQL_Converter(DataConverter):
    
    def find_data(self, id, samplefolder):  
        
            '''sample folder does nothing except act as placeholder.                    
            This function currently proceeds under the assumption that the experiment is set up, and doesn't
            check anything to confirm that. Also, I think this doesn't return any error if it can't find 
            the dataset with that id number.'''
          
            data = get_data_by_id(id)                   
            
            return data  

        
    def find_dependencies(self, id, data):      #SQL converter only needs id, not data
        conn = connect('experiments.db')    #the name of the file to access can't be set manually right now 
        cur = conn.cursor()
        
        names = {}
        dependencies = {}

        for row in cur.execute('SELECT layout_id, parameter FROM layouts WHERE run_id is ?', str(id)):
            names[row[0]] = row[1]

        for row in cur.execute('SELECT dependent, independent FROM dependencies'):
            if row[0] in names.keys():
                dependencies[names[row[0]]] = []
            
        for row in cur.execute('SELECT dependent, independent FROM dependencies'):     
            if row[0] in names.keys():
                dependencies[names[row[0]]].append(names[row[1]])

        conn.close()

        return dependencies

    
    def find_variables(self, data):
        
        all_variables = []
        
        for data_subset in data:
            for variable in data_subset:
                if variable['name'] not in all_variables:
                    all_variables.append(variable['name'])
                    
        return all_variables

    
    def make_data_dictionary(self, data):
        
        data_dict = {}
        
        for data_subset in data:
            for variable in data_subset:
                
                name = variable['name']
        
                if name in data_dict.keys():
                    print(name)
                    if not np.array_equal(variable['data'], data_dict[name]['data']):
                        raise RuntimeError('Variables with identical names contain non-identical data arrays!')
        
                data_dict[name] = variable
            
        return data_dict
            


class Legacy_Converter(DataConverter):
    
    def find_data(self, id, samplefolder):
        
        str_id = '{0:03d}'.format(id)
        
        if samplefolder==None:
            check_experiment_is_initialized()    
            #check_experiment_is_initialized() doesn't do anything at the moment
            
            path = qc.DataSet.location_provider.fmt.format(counter=str_id)
            data = qc.load_data(path)

        else:
            path = '{}{}{}'.format(samplefolder,sep,str_id)
            data = qc.load_data(path)
            
        return data
    
    
    def find_dependencies(self, id, data):    #legacy only needs data, not id
        
        dep_vars   = [key for key in data.arrays.keys() if "_set" not in key[-4:]]
        indep_vars = [key for key in data.arrays.keys() if "_set" in key[-4:]]
        
        dependencies = {}
        
        for variable in dep_vars:
            dependencies[variable] = indep_vars
            
        return dependencies
    
    
    def find_variables(self, data):
        
        all_variables = [variable for variable in data.arrays.keys()]
        return all_variables
    
    
    def resize_data(self, data1, data2):
    
        scan_size = len(data1[0])
    
        new_data2 = []
    
        for setvalue in data2:
            array = np.array([setvalue for datapoint in range(scan_size)])
            new_data2.append(array)
        
        return np.array(new_data2)

    
    def make_data_dictionary(self, data):
        
        data_dict = {}
        
        all_variables = self.find_variables(data)
        
        for variable in all_variables:
            qc_data = getattr(data, variable)
            name = getattr(qc_data, 'name', 'No Name')
            label = getattr(qc_data, 'label', '')
            unit = getattr(qc_data, 'unit', '')
            np_data = qc_data.ndarray
            
            data_dict[variable] = {'name': variable,
                                  'label': label,
                                   'var_name': name,
                                  'unit': unit,
                                  'data': np_data}
            
            
        '''checks if the data set used set points - if so, it reformats the data
        arrays so that it looks the same as it would look if it were imported
        from SQL. All data is stored as arrays of the same length, rather than
        set_points being stored as single numbers
        (i.e. for setpoints = [1, 2, 3] , data = [[a, b, c], [d, e, f], [g, h, i]] 
        becomes setpoints = [[1, 1, 1], [2, 2, 2], [3, 3, 3]], data = data)'''
        dependencies = self.find_dependencies(id, data)
        
        dep_vars = [key for key in dependencies.keys()]
        indep_vars = dependencies[dep_vars[0]]
        
        if len(indep_vars) == 2:
            data1 = data_dict[dep_vars[0]]['data']    
            data2 = data_dict[indep_vars[0]]['data']  
            data3 = data_dict[indep_vars[1]]['data']
            
            if type(data2[0]) != np.ndarray:
                data_dict[indep_vars[0]]['data'] = self.resize_data(data1, data2)
            if type(data3[0]) != np.ndarray:
                data_dict[indep_vars[1]]['data'] = self.resize_data(data1, data3)
          
        
        
            '''reformatting nested arrays as a single 1d array, i.e.
            setpoints = [[1, 1, 1], [2, 2, 2], [3, 3, 3]], data = [[a, b, c], [d, e, f], [g, h, i]]
            becomes setpoints [1, 1, 1, 2, 2, 2, 3, 3, 3], data = [a, b, c, d, e, f, g, h, i]'''
            
            for variable in all_variables:
                data1 = data_dict[variable]['data']
                
                new_data = []
                for array in data1:
                    for datapoint in array:
                        new_data.append(datapoint)
                    
                data_dict[variable]['data'] = np.array(new_data)
                
                
        return data_dict
       
        
