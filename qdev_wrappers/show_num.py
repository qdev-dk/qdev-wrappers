import qcodes as qc
from qdev_wrappers.file_setup import CURRENT_EXPERIMENT
from qcodes.plots.pyqtgraph import QtPlot
from qcodes.plots.qcmatplotlib import MatPlot

def check_experiment_is_initialized():
    if not getattr(CURRENT_EXPERIMENT, "init", True): 
        raise RuntimeError("Experiment not initalized. "
                           "use qc.Init(mainfolder, samplename)")


def show_num(id, useQT=False, ave_col=False, ave_row=False, do_plots=True, savepng=False, **kwargs):
    """
    Show  and return plot and data for id in current instrument.
    Args:
        id(number): id of instrument
        useQT (boolean): If true plots with QTplot instead of matplotlib
        ave_col (boolean): If true subtracts average from each collumn
        ave_row (boolean): If true subtracts average from each row
        do_plots: Default False: if false no plots are produced.
        savepng (boolean): If true saves matplotlib figure as png
        **kwargs: Are passed to plot function

    Returns:
        data, plots : returns the plot and the dataset

    """
    check_experiment_is_initialized()
    str_id = '{0:03d}'.format(id)

    t = qc.DataSet.location_provider.fmt.format(counter=str_id)
    data = qc.load_data(t)
    keys = [key for key in data.arrays.keys() if "_set" not in key[-4:]]

    if do_plots:
        plots = []
        avestr = ''
        num = ''
        l = len(keys)

        for j, value in enumerate(keys):
            arrays = getattr(data, value)
            if ave_row:
                for i in range(np.shape(arrays)[0]):
                    arrays[i,:] -= arrays[i,:].mean()
                avestr = '_row'
            if ave_col:
                for i in range(np.shape(arrays)[1]):
                    arrays[:,i] -= arrays[:,i].mean()
                avestr = '_col'
            if useQT:
                plot = QtPlot(
                    getattr(data, value),
                    fig_x_position=CURRENT_EXPERIMENT['plot_x_position'],
                    **kwargs)
                title = "{} #{}".format(CURRENT_EXPERIMENT["sample_name"],
                                        str_id)
                plot.subplots[0].setTitle(title)
                plot.subplots[0].showGrid(True, True)
                if savepng:
                    print('Save plot only working for matplotlib figure. Set useQT=False to save png.')
            else:
                plot = MatPlot(getattr(data, value), **kwargs)
                if savepng:
                    title_list_png = plot.get_default_title().split(sep)
                    title_list_png.insert(-1, CURRENT_EXPERIMENT['png_subfolder'])
                    title_png = sep.join(title_list_png)
                    if l>1:
                        num = '_{}'.format(j+1)
                    plt.savefig("{}{}{}.png".format(title_png,num,avestr),dpi=500)
            plots.append(plot)
    else:
        plots = None
    return data, plots


def show_meta(id,instruments,key_word=''):
    '''
    Print meta data in command line for datafile id.
    id (int): 
    instruments (list): List of strings with instruments names for which metadata is printed.
    key_word (string): Optional - String in label of metadata if printed.
    '''
    check_experiment_is_initialized()

    str_id = '{0:03d}'.format(id)

    t = qc.DataSet.location_provider.fmt.format(counter=str_id)
    data = qc.load_data(t)
    for instr in instruments:
        new_dic = ParaPrint([data.metadata['station']['instruments'][instr]],key_word)
        for i in range(15):
            new_dic = ParaPrint(new_dic,key_word)




def ParaPrint(dic_list,key_word):
    '''
    Helper function for show_meta. Division value is assumed added as an extra metadata attribute to parameters using 'VoltageDivider' function.
    '''
    new_dic_list = []
    for dictionary in dic_list:
        for name in dictionary.keys():
            if (name == 'parameters') and not (not dictionary['parameters']):
                for p_name in dictionary['parameters'].keys():
                    p = dictionary['parameters'][p_name]
                    if ((not (not p['value']) and not np.shape(p['value'])) or p['value']==0) and key_word in p['label']:
                        if 'division_value' in dictionary['parameters'][p_name].keys():
                            print('{}: {} = {} {}. Divider = {}'.format(p['instrument_name'],p['label'],p['value'],p['unit'],p['division_value']))
                        else:
                            print('{}: {} = {} {}'.format(p['instrument_name'],p['label'],p['value'],p['unit']))
            if isinstance(dictionary[name], dict):
                new_dic_list.append(dictionary[name])
    return new_dic_list
