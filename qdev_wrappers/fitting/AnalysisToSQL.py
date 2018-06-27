

import sqlite3
from qdev_wrappers.fitting.Fitclasses import T1, T2


def is_table(tablename, cursor):  # Checks if table already exists. Assumes database connection and cursor already established

    table_count = "SELECT count(*) FROM sqlite_master WHERE type = 'table' AND name='{}'".format(tablename)
    execute = cursor.execute(table_count)
    count = execute.fetchone()[0]

    if count == 0:
        return False

    if count == 1:
        return True


def make_table(tablename, cursor):
    name = tablename
    n = 0

    while is_table(name, cursor):
        n += 1
        name = "{}_{}".format(tablename, n)
    else:
        cursor.execute('CREATE TABLE {} (id INTEGER)'.format(name))

    return name


def fit_to_SQL(data, fitclass, fit):    #it would be an improvement if it were able to get the fitclass from the fit information 

    if fit['estimator']['type'] != fitclass.name:       #maybe this should be more general in this function, like 'analysis_class? - so it makes sense e.g. in the case of Baysian inference
        raise RuntimeError('The data given was analyzed using {}. This does not seem to match {} specified in this function'.format(fit['estimator']['type'], fitclass.name))
    
    dim = 1
    if 'zdata' in fit['inferred_from'].keys():
        dim = 2
    
    xname = fit['inferred_from']['xdata']
    xdata = data[xname]['data']
    
    yname = fit['inferred_from']['ydata']
    ydata = data[yname]['data']
    
    est = []    #estimated/predicted value for the measured data given the fitted parameters
    est_name = '{}_estimate'.format(yname)
    est_label = data[yname]['label']
    est_unit = data[yname]['unit']

    
    p_values = []
    
    if dim == 2:
        zname = fit['inferred_from']['zdata']
        zdata = data[zname]['data'] 
        est_name = '{}_estimate'.format(zname)
        est_label = data[zname]['label']
        est_unit = data[zname]['unit']
    
    #make array of estimated values based on parameters and model used
    if dim == 1:

        param_units = [fit['parameters'][param]['unit'] for param in list(fitclass.p_labels)]

        params = list(fitclass.p_labels)
        for index, parameter in enumerate(params):
            if parameter not in fit['parameters']:
                raise KeyError('The list of parameters for the fitclass {} contains a parameter, {}, which is not present in the fit dictionary.'.format(fitclass.name, parameter))
            params[index] = fit['parameters'][parameter]['value']  
    
        for datapoint in xdata:
            y = fitclass.fun(datapoint, *params)
            est.append(y)
            p_values.append(params)

            
    if dim == 2:

        setpoints = [key for key in fit.keys()]
        param_units = [fit[setpoints[0]]['parameters'][param]['unit'] for param in list(fitclass.p_labels)]
        
        for xpoint, ypoint in zip(xdata, ydata):
        
            if xpoint in setpoints:
                setpoint = xpoint
                datapoint = ypoint
            elif ypoint in setpoints:
                setpoint = ypoint
                datapoint = xpoint
        
            params = list(fitclass.p_labels)
            for index, parameter in enumerate(params):
                if parameter not in fit[setpoint]['parameters']:
                    raise KeyError('The list of parameters for the fitclass {} contains a parameter, {}, which is not present in the fit dictionary.'.format(fitclass.name, parameter))
                params[index] = fit[setpoint]['parameters'][parameter]['value']
        
            z = fitclass.fun(datapoint, *params)
            est.append(z)
            p_values.append(params)



    tablename = 'data_{}_{}'.format(data['run_id'], fitclass.name)
    

    table_columns = [est_name]
    for parameter in fitclass.p_labels:
        table_columns.append(parameter)
       
    table_rows = []
    if dim == 1:
        for estimate in est:
            id_nr = est.index(estimate) + 1
            row = (id_nr, estimate, *params)
            table_rows.append(row)
    elif dim == 2:
        for estimate, parameters in zip(est, p_values):
            id_nr = est.index(estimate) + 1
            row = (id_nr, estimate, *parameters)
            table_rows.append(row)



    run_id = data['run_id']
    exp_id = data['exp_id']
    analysis_id = 1
    predicts = est_name.strip("estimate").strip("_")
    estimator = "{}, {}".format(fit['estimator']['method'], fit['estimator']['type'])
    analysis = fit['estimator']['function']
    parameters = fitclass.p_labels
    param_labels = fitclass.p_names


    conn = sqlite3.connect('analysis.db')  # should this go in a separate analysis database, or just go in experiments.db?
    cur = conn.cursor()

    #Alternative: have a separate function that sets up the general analysis database with tables, so that this doesn't have to be here
    if not is_table('analyses', cur):
        cur.execute('''CREATE TABLE analyses 
                        (run_id INTEGER, exp_id INTEGER, analysis_id INTEGER, result_table_name TEXT, 
                        predicts TEXT, estimator TEXT, function TEXT)''')
    if not is_table('overview', cur):
        cur.execute('''CREATE TABLE overview 
                        (id INTEGER, analysis_id INTEGER, 
                        parameter TEXT, label TEXT, unit TEXT, inferred_from TEXT)''')


    table = make_table(tablename, cur)


    sql_analyses = 'INSERT INTO analyses VALUES (?,?,?,?,?,?,?)'

    max_id = cur.execute('SELECT MAX(analysis_id) FROM analyses').fetchone()[0]
    if max_id != None:
        analysis_id += max_id

    cur.execute(sql_analyses, (run_id, exp_id, analysis_id, table, predicts, estimator, analysis))


    sql_overview = 'INSERT INTO overview VALUES (?,?,?,?,?,?)'

    result_id = 1
    max_id = cur.execute('SELECT MAX(id) FROM overview').fetchone()[0]
    if max_id != None:
        result_id += max_id

    overview_rows = []
    for parameter, label, unit in zip(parameters, param_labels, param_units):
        row = (result_id, analysis_id, parameter, label, unit, "inferred_from")
        overview_rows.append(row)
        result_id += 1
    overview_rows.append((result_id, analysis_id, est_name, est_label, est_unit, "inferred_from"))

    cur.executemany(sql_overview, (overview_rows))


    for column in table_columns:
        cur.execute('ALTER TABLE {} ADD {}'.format(table, column))
    
    num_cols = len(table_rows[0])
    placeholder = ('?,'*num_cols).strip(',')

    cur.executemany('INSERT INTO {} VALUES ({})'.format(table, placeholder), table_rows)


    conn.commit()
    conn.close()

    print("Table {} created in analysis.db".format(table))
