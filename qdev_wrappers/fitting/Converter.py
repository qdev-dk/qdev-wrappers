import qcodes as qc
import numpy as np
from os.path import sep, expanduser
from qcodes.dataset.data_export import get_data_by_id
from qcodes.dataset.sqlite_base import connect
from qdev_wrappers.file_setup import CURRENT_EXPERIMENT
from qdev_wrappers.show_num import check_experiment_is_initialized


def data_to_dict(id, samplefolder=None, datatype='SQL'):
    if datatype == 'qcodes_legacy':
        converter = Legacy_Converter()

    elif datatype == 'SQL':
        converter = SQL_Converter()

    else:
        raise NotImplementedError('datatype {} is not currently supported'.format(datatype))

    return converter.convert(id, samplefolder)


class DataConverter:

    """This is the base class for converters that convert data stored in files into a python dictionary."""

    def find_data(self, id, samplefolder):

        """ Takes data run id as argument, as well as a samplefolder, which can be set
        to None if the run is part of the current configuration. Retrieves the data from the file
        it is stored in, based on either the sample folder or qc.config. Returns data. """

        raise NotImplementedError('find_data not implemented in the base class.')

    def make_data_dictionary(self, data):

        """ Takes data (as returned by find_data). Organizes data into as a dictionary. Each key
        is one of the variables from the data, and its corresponding value is a dictionary in
        the format {'name': str, 'label': str, 'unit': str, 'data': np.array }. Returns data dict
        containing name, label, unit and data array for each variable in the dataset. """

        raise NotImplementedError('make_data_dictionary not implemented in the base class.')

    def find_experiment(self, run_id, samplefolder):

        """ Takes run_id, and returns corresponding experiment id """

        raise NotImplementedError('find_experiment not implemented in the base class.')

    def find_dependencies(self, run_id, data, samplefolder):

        """ Takes run_id and data dict. Finds dependencies of the variables, and returns them as a
        dependencies dict. E.g. if A and B were measured, and they both depend on C and D:
        dependencies = {A: [C, D], B: [C, D]} """

        raise NotImplementedError('find_dependencies not implemented in the base class.')

    def find_variables(self, data):

        """ Takes data dict. Returns list of all variables contained in the data dict."""

        raise NotImplementedError('find_variables not implemented in the base class.')
    
    def convert(self, id, samplefolder=None):

        """ Takes run_id and optionally a samplefolder name. Sample folder name should only be
        necessary if the run in question isn't part of the current experimental configuration.
        Returns a dictionary containing all the data from the specified run as numpy arrays,
        plus relevant metadata (experiment id, run id, dependencies, names, labels, and units). """
        
        data = self.find_data(id, samplefolder) 
        data_dict = self.make_data_dictionary(data)

        exp_id = self.find_experiment(id, samplefolder)
        dependencies = self.find_dependencies(id, data, samplefolder)  # SQL needs only id, Legacy needs only data
        all_variables = self.find_variables(data)

        data_dict['exp_id'] = exp_id
        data_dict['run_id'] = id
        data_dict['dependencies'] = dependencies
        data_dict['variables'] = all_variables
        
        return data_dict


class SQL_Converter(DataConverter):
    
    def find_data(self, id, samplefolder):
        
            """ This isn't actually set up to use the samplefolder if one is given - it can only use
            the qc.config via the get_data_by_id function. If this were set up to retrieve the data as
            get_data_by_id does, but with get_DB_location() returning expanduser(sampefolder) instead
            of expanduser(qcodes.config["core"]["db_location"]), then I think everything would work
            for manual specification of database location """

            if samplefolder is None:
                data = get_data_by_id(id)
            else:
                raise NotImplementedError('Manual specification of database location not implemented for SQL')

            if len(data) == 0:
                raise RuntimeError('No data found for run id {}'.format(id))
            
            return data  

    def find_dependencies(self, id, data, samplefolder):  # SQL converter only needs id, not data

        if samplefolder is None:
            file = expanduser(qc.config['core']['db_location'])
        else:
            file = expanduser(samplefolder)
        conn = connect(file)
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

    def find_experiment(self, id, samplefolder):

        if samplefolder is None:
            file = expanduser(qc.config['core']['db_location'])
        else:
            file = expanduser(samplefolder)
        conn = connect(file)
        cur = conn.cursor()

        execute = cur.execute('SELECT exp_id FROM runs WHERE run_id is {}'.format(id))
        exp_id = execute.fetchone()[0]

        return exp_id

    def make_data_dictionary(self, data):
        
        data_dict = {}
        
        for data_subset in data:
            for variable in data_subset:
                
                name = variable['name']
        
                if name in data_dict.keys():
                    if not np.array_equal(variable['data'], data_dict[name]['data']):
                        print(name)
                        raise RuntimeError('Variables with identical names contain non-identical data arrays!')
        
                data_dict[name] = variable
            
        return data_dict


class Legacy_Converter(DataConverter):
    
    def find_data(self, id, samplefolder):
        
        str_id = '{0:03d}'.format(id)
        
        if samplefolder is None:
            check_experiment_is_initialized()    
            # check_experiment_is_initialized() doesn't do anything at the moment
            
            path = qc.DataSet.location_provider.fmt.format(counter=str_id)
            data = qc.load_data(path)

        else:
            path = '{}{}{}'.format(samplefolder, sep, str_id)
            data = qc.load_data(path)
            
        return data
    
    def find_dependencies(self, id, data, samplefolder=None):  # legacy only needs data, not id or sample folder
        
        dep_vars = [key for key in data.arrays.keys() if "_set" not in key[-4:]]
        indep_vars = [key for key in data.arrays.keys() if "_set" in key[-4:]]
        
        dependencies = {}
        
        for variable in dep_vars:
            dependencies[variable] = indep_vars
            
        return dependencies
    
    def find_variables(self, data):
        
        all_variables = [variable for variable in data.arrays.keys()]
        return all_variables

    def find_experiment(self, id, samplefolder=None):  # samplefolder only needed in sql converter

        exp_id = id
        return exp_id
    
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
