import qcodes as qc
import numpy as np
from os.path import sep
import collections
from typing import Optional, Union, Tuple, cast
import matplotlib.pyplot as plt

from qdev_wrappers.file_setup import CURRENT_EXPERIMENT
from qcodes.utils.plotting import auto_range_iqr, apply_color_scale_limits
from qcodes.plots.pyqtgraph import QtPlot
from qcodes.plots.qcmatplotlib import MatPlot
import qcodes

Number = Union[float, int]

def check_experiment_is_initialized():
    if not getattr(CURRENT_EXPERIMENT, "init", True): 
        raise RuntimeError("Experiment not initalized. "
                           "use qc.Init(mainfolder, samplename)")


def show_num(ids, samplefolder=None, useQT=False, avg_sub='',
             do_plots=True, savepng=True, fig_size=[6,4], clim=None,
             dataname=None, xlim=None, ylim=None, transpose=False,
             auto_color_scale: Optional[bool]=None,
             cutoff_percentile: Optional[Union[Tuple[Number, Number], Number]]=None,
             **kwargs):
    """
    Show and return plot and data.
    Args:
        ids (number, list): id or list of ids of dataset(s)
        samplefolder (str): Sample folder if loading data from different sample than the initialized. 
        useQT (boolean): If true plots with QTplot instead of matplotlib
        avg_sub (str: 'col' or 'row'): Subtracts average from either each collumn ('col') or each row ('row')
        do_plots: (boolean): if false no plots are produced.
        dataname (str): If given only plots dataset with that name
        savepng (boolean): If true saves matplotlib figure as png
        fig_size [6,4]: Figure size in inches
        clim [cmin,cmax]: Set min and max of colorbar to cmin and cmax respectrively
        xlim [xmin,xmax]: Set limits on x axis
        ylim [ymin,ymax]: set limits on y axis
        transpose (boolean): Transpose data to be plotted (only works for 2D scans and qc.MatPlot)
        auto_color_scale: if True, the colorscale of heatmap plots will be
            automatically adjusted to disregard outliers.
        cutoff_percentile: percentile of data that may maximally be clipped
            on both sides of the distribution.
            If given a tuple (a,b) the percentile limits will be a and 100-b.
            See also the plotting tuorial notebook.
        **kwargs: Are passed to plot function

    Returns:
        data, plots : returns the plots and the datasets

    """
    # default values
    if auto_color_scale is None:
        auto_color_scale = qcodes.config.plotting.auto_color_scale.enabled
    if cutoff_percentile is None:
        cutoff_percentile = cast(
            Tuple[Number, Number],
            tuple(qcodes.config.plotting.auto_color_scale.cutoff_percentile))

    if not isinstance(ids, collections.Iterable):
        ids = (ids,)

    data_list = []
    keys_list = []

    # Define samplefolder
    if samplefolder==None:
        check_experiment_is_initialized()
        samplefolder = qc.DataSet.location_provider.fmt.format(counter='')


    # Load all datasets into list
    for id in ids:
        path = samplefolder + '{0:03d}'.format(id)
        data = qc.load_data(path)
        data_list.append(data)

        # find datanames to be plotted
        if do_plots:
            if useQT and len(ids) is not 1:
                raise ValueError('qcodes.QtPlot does not support multigraph plotting. Set useQT=False to plot multiple datasets.')
            if dataname is not None:
                if dataname not in [key for key in data.arrays.keys() if "_set" not in key]:
                    raise RuntimeError('Dataname not in dataset. Input dataname was: \'{}\''.format(dataname), \
                        'while dataname(s) in dataset are: \'{}\'.'.format('\', \''.join(data.arrays.keys())))
                keys = [dataname]
            else:
                keys = [key for key in data.arrays.keys() if "_set" not in key]
            keys_list.append(keys)


    if do_plots:
        unique_keys = list(set([item for sublist in keys_list for item in sublist]))
        plots = []
        num = ''
        l = len(unique_keys)
        for j, key in enumerate(unique_keys):
            array_list = []
            xlims = [[],[]]
            ylims = [[],[]]
            clims = [[],[]]
            # Find datasets containing data with dataname == key
            for data, keys in zip(data_list,keys_list):
                if key in keys:
                    arrays = getattr(data, key)
                    if transpose and len(arrays.set_arrays)==2:
                        if useQT:
                            raise AttributeError('Transpose only works for qc.MatPlot.')
                        if dataname is None and l != 1:
                            raise ValueError('Dataname has to be provided to plot data transposed for dataset with more '
                                    'than 1 measurement. Datanames in dataset are: \'{}\'.'.format('\', \''.join(unique_keys)))
                        arrays.ndarray = arrays.ndarray.T
                        set0_temp = arrays.set_arrays[0]
                        set1_temp = arrays.set_arrays[1]
                        set0_temp.ndarray = set0_temp.ndarray.T
                        set1_temp.ndarray = set1_temp.ndarray.T
                        arrays.set_arrays = (set1_temp,set0_temp,)
                    if avg_sub == 'row':
                        for i in range(np.shape(arrays.ndarray)[0]):
                            arrays.ndarray[i,:] -= np.nanmean(arrays.ndarray[i,:])
                    if avg_sub == 'col':
                        for i in range(np.shape(arrays.ndarray)[1]):
                            arrays.ndarray[:,i] -= np.nanmean(arrays.ndarray[:,i])
                    array_list.append(arrays)

                    # Find axis limits for dataset
                    if len(arrays.set_arrays)==2:
                        xlims[0].append(np.nanmin(arrays.set_arrays[1]))
                        xlims[1].append(np.nanmax(arrays.set_arrays[1]))
                        ylims[0].append(np.nanmin(arrays.set_arrays[0]))
                        ylims[1].append(np.nanmax(arrays.set_arrays[0]))
                        if auto_color_scale:
                            vlims = auto_range_iqr(arrays.ndarray)
                        else:
                            vlims = (np.nanmin(arrays.ndarray),
                                     np.nanmax(arrays.ndarray))
                        clims[0].append(vlims[0])
                        clims[1].append(vlims[1])
                    else:
                        xlims[0].append(np.nanmin(arrays.set_arrays[0]))
                        xlims[1].append(np.nanmax(arrays.set_arrays[0]))
                        ylims[0].append(np.nanmin(arrays.ndarray))
                        ylims[1].append(np.nanmax(arrays.ndarray))

            if useQT:
                plot = QtPlot(array_list[0],
                    fig_x_position=CURRENT_EXPERIMENT['plot_x_position'],
                    **kwargs)
                title = "{} #{}".format(CURRENT_EXPERIMENT["sample_name"],
                                        '{}'.format(ids[0]))
                plot.subplots[0].setTitle(title)
                plot.subplots[0].showGrid(True, True)
                if savepng:
                    print('Save plot only working for matplotlib figure.', \
                        'Set useQT=False to save png.')
            else:
                plot = MatPlot(array_list, **kwargs)
                plot.rescale_axis()
                plot.fig.tight_layout(pad=3)
                plot.fig.set_size_inches(fig_size)
                # Set axis limits
                if xlim is None:
                    plot[0].axes.set_xlim([np.nanmin(xlims[0]),np.nanmax(xlims[1])])
                else:
                    plot[0].axes.set_xlim(xlim)
                if ylim is None:
                    plot[0].axes.set_ylim([np.nanmin(ylims[0]),np.nanmax(ylims[1])])
                else:
                    plot[0].axes.set_ylim(ylim)
                if len(arrays.set_arrays)==2:
                    for i in range(len(array_list)):
                        # TODO(DV): get colorbar from plot children (should be ax.qcodes_colorbar)
                        if clim is None:
                            clim = np.nanmin(clims[0]), np.nanmax(clims[1])
                        colorbar = plot[0].get_children()[i].colorbar
                        apply_color_scale_limits(colorbar, new_lim=clim)

                # Set figure titles
                plot.fig.suptitle(samplefolder)
                if len(ids)<6:
                    plot.subplots[0].set_title(', '.join(map(str,ids)))
                else:
                    plot.subplots[0].set_title(' - '.join(map(str,[ids[0],ids[-1]])))
                plt.draw()

                # Save figure
                if savepng:
                    if len(ids) == 1:
                        title_png = samplefolder+CURRENT_EXPERIMENT['png_subfolder']+sep+'{}'.format(ids[0])
                    else:
                        title_png = samplefolder+CURRENT_EXPERIMENT['png_subfolder']+sep+'{}-{}'.format(ids[0],ids[-1])
                    if l>1:
                        num = '{}'.format(j+1)
                    plt.savefig(title_png+'_{}_{}.png'.format(num,avg_sub),dpi=500)
            plots.append(plot)
    else:
        plots = None
    return data_list, plots


def show_meta(id,instruments,samplefolder=None,key_word=''):
    '''
    Print meta data in command line for datafile id.
    id (int): 
    instruments (list): List of strings with instruments names for which metadata is printed.
    key_word (string): Optional - String in label of metadata if printed.
    '''
    str_id = '{0:03d}'.format(id)
    if samplefolder==None:
        check_experiment_is_initialized()

        path = qc.DataSet.location_provider.fmt.format(counter=str_id)
        data = qc.load_data(path)
    else:
        path = '{}{}{}'.format(samplefolder,sep,str_id)
        data = qc.load_data(path)


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
                    if 'value' in p.keys():
                        if ((not (not p['value']) and not np.shape(p['value'])) or p['value']==0) and key_word in p['label']:
                            if 'division_value' in dictionary['parameters'][p_name].keys():
                                print('{}: {} = {} {}. Divider = {}'.format(p['instrument_name'],p['label'],p['value'],p['unit'],p['division_value']))
                            else:
                                print('{}: {} = {} {}'.format(p['instrument_name'],p['label'],p['value'],p['unit']))
            if isinstance(dictionary[name], dict):
                new_dic_list.append(dictionary[name])
    return new_dic_list
