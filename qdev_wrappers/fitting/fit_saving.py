
import sqlite3
import dill
import qcodes as qc
from os.path import expanduser
from collections import namedtuple


FitInfo = namedtuple(
    'FitInfo',
    'fitclass est_name est_label est_unit param_units data_run_id '
    'exp_id predicts estimator analysis dill_obj start_params '
    'param_labels table_rows table_columns tablename')


def is_table(tablename, cursor):
    """
    Args:
        tablename (str)
        cursor: connection to an SQL database
    Returns:
        is_table (bool): True if a table with that name exists,
            False if not.

    Error if it finds multiple tables with the same name, or if the
    sql count function returns something unexpected.
    """

    table_count = "SELECT count(*) FROM sqlite_master WHERE type = 'table' AND name='{}'".format(tablename)
    execute = cursor.execute(table_count)
    count = execute.fetchone()[0]

    if count == 0:
        return False

    elif count == 1:
        return True

    else:
        raise RuntimeError(
            'Attempt to check existing table names failed.'
            ' Count of tables with name {} returned {} '
            'instead of 1 or 0.'.format(tablename, count))


def make_table(tablename, cursor):
    """
    Args:
        tablename (str)
        cursor: connection to an SQL database.
    Returns:
        tablename (str): same as arg if this name was available,
            otherwise a numbered variant
    """
    name = tablename
    n = 0

    while is_table(name, cursor):
        n += 1
        name = "{}_{}".format(tablename, n)

    cursor.execute('CREATE TABLE {} (id INTEGER)'.format(name))
    return name


def reorganise_fit_dict(fit):
    """
    Information from the fit dictionary is retrieved and organized

    Args:
        fit (dict): as output by fitter
    Returns:
        FitInfo (NamedTuple)
    """
    fitclass_pckl = fit['inferred_from']['estimator']['dill']['fitclass']
    fitclass = dill.loads(fitclass_pckl)

    est_values = fit['estimate']['values']
    est_name = '{}_estimate'.format(fit['estimate']['name'])
    est_label = fit['estimate']['label']
    est_unit = fit['estimate']['unit']

    param_values = fit['estimate']['parameters']
    param_units = fit['parameter units']

    data_run_id = fit['inferred_from']['run_id']
    exp_id = fit['inferred_from']['exp_id']
    predicts = est_name.strip("estimate").strip("_")
    estimator = "{}, {}".format(
        fit['inferred_from']['estimator']['method'],
        fit['inferred_from']['estimator']['type'])
    analysis = str(fit['inferred_from']['estimator']['function used'])
    dill_obj = str(fit['inferred_from']['estimator']['dill'])
    start_params = str(fit['start_params'])
    param_labels = fitclass.p_names

    # reorganize parameters to fit into rows,
    # [a1, a2, a3...] and [b1, b2, b3...] --> [ [a1, b1], [a2, b2]...]
    param_list = []
    data_length = len(est_values)
    for i in range(data_length):
        params = []
        for parameter in fitclass.p_labels:
            params.append(param_values[parameter][i])
        param_list.append(params)

    # make list of table row contents,
    # [(row1), (row2), (row3)...], row1 = (id_nr1, estimate1, a1, b1...)
    table_rows = []
    for estimate, parameters, index in zip(est_values, param_list, range(data_length)):
        id_nr = index + 1
        row = (id_nr, estimate, *parameters)
        table_rows.append(row)

    # make list of column titles (estimated output, param1, param2...)
    table_columns = [est_name]
    for parameter in fitclass.p_labels:
        table_columns.append(parameter)

    tablename = 'analysis_{}_{}'.format(
        fit['inferred_from']['run_id'], fitclass.name)

    return FitInfo(
        fitclass, est_name, est_label, est_unit, param_units, data_run_id,
        exp_id, predicts, estimator, analysis, dill_obj, start_params,
        param_labels, table_rows, table_columns, tablename)


def save_fit_dict(fit_info):
    """
    A connection to the SQL database is created and the fit data is
    saved to the database.

    Args:
        fit_info (FitInfo named_tuple)
    """
    # create a connection to the SQL database
    file = expanduser(qc.config['core']['db_location'])
    conn = sqlite3.connect(file)
    cur = conn.cursor()

    # Create table for fit parameter and predicted output values, store data

    table = make_table(fit_info.tablename, cur)

    for column in fit_info.table_columns:
        cur.execute('ALTER TABLE {} ADD {}'.format(table, column))

    num_cols = len(fit_info.table_rows[0])
    placeholder = ('?,' * num_cols).strip(',')
    cur.executemany('INSERT INTO {} VALUES ({})'.format(
        table, placeholder), fit_info.table_rows)

    # Create 'analyses' table if it does not already exist,
    # store info about analysis in 'analyses'
    if not is_table('analyses', cur):
        cur.execute(
            '''CREATE TABLE analyses
                        (data_run_id INTEGER, exp_id INTEGER, run_id INTEGER, analysis_table_name TEXT,
                        predicts TEXT, estimator TEXT, function TEXT, start_parameters TEXT, dill TEXT)''')
    run_id = 1
    max_id = cur.execute('SELECT MAX(run_id) FROM layouts').fetchone()[0]
    if max_id is not None:
        run_id += max_id

    sql_analyses = 'INSERT INTO analyses VALUES (?,?,?,?,?,?,?,?,?)'
    cur.execute(sql_analyses,
                (fit_info.data_run_id, fit_info.exp_id, fit_info.run_id,
                 table, fit_info.predicts, fit_info.estimator,
                 fit_info.analysis, fit_info.start_params, fit_info.dill_obj))

    # Store unit and label info in 'layouts' table
    layout_id = 1
    max_id = cur.execute('SELECT MAX(layout_id) FROM layouts').fetchone()[0]
    if max_id is not None:
        layout_id += max_id

    layout_rows = []
    for parameter, label, unit in zip(fit_info.fitclass.p_labels, fit_info.param_labels, fit_info.param_units):
        row = (layout_id, run_id, parameter, label, unit, "inferred_from")
        layout_rows.append(row)
        layout_id += 1
    layout_rows.append((layout_id, run_id, fit_info.est_name,
                        fit_info.est_label, fit_info.est_unit, "inferred_from"))

    sql_layout = 'INSERT INTO layouts VALUES (?,?,?,?,?,?)'
    cur.executemany(sql_layout, layout_rows)

    # Store summary in 'runs' SQL table, with run type 'analysis'
    sql_runs = 'INSERT INTO runs VALUES (?,?,?,?,?,?,?,?,?,?)'
    cur.execute(sql_runs, (run_id, exp_id, 'analysis',
                           table, "", "", "", 1, "", ""))

    # save changes to SQL database and close connection
    conn.commit()
    conn.close()

    print("Table {} created".format(table))


def save_fit_dict(fit):
    """
    Organises and saves the fit dictionary in SQL database
    Args:
        fit (dict): as output by fitter
    """
    fit_info_tuple = reorganise_fit_dict(fit)
    save_fit_dict(fit_info_tuple)
