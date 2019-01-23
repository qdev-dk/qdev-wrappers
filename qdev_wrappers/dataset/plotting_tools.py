
from collections import OrderedDict
from typing import (Optional, List, Sequence, Union, Tuple, Dict,
                    Any, Set)

import time
import os
import numpy as np
import matplotlib
import matplotlib.pyplot as plot
from matplotlib.collections import QuadMesh

import qcodes as qc
from qcodes.dataset.data_set import load_by_id
from qcodes.dataset.plotting import plot_by_id
from qcodes.dataset.data_export import (get_data_by_id, flatten_1D_data_for_plot,
                          get_1D_plottype, get_2D_plottype, reshape_2D_data,
                          _strings_as_ints)
from qcodes import config

AxesTuple = Tuple[matplotlib.axes.Axes, matplotlib.colorbar.Colorbar]
AxesTupleList = Tuple[List[matplotlib.axes.Axes],
                      List[Optional[matplotlib.colorbar.Colorbar]]]
Number = Union[float, int]

def plot_id(dataid, transform_name=None,*args,**kwargs):
    plots = plot_by_id(dataid,**kwargs)
    if transform_name is not None:
        transform_plot(plots,transform_name,*args)
    return plots

def save_image(dataid, transform_name=None, filename=None,**kwargs) -> AxesTupleList:
    """
    Save the plots from dataid as pdf and png

    Args:
        datasaver: a measurement datasaver that contains a dataset to be saved
            as plot.
        filename: String added to the filename of saved images
        kwargs: Arguments passed to plot_by_id

    """

    start = time.time()
    dataset = load_by_id(dataid)
    plots = plot_id(dataid,transform_name=transform_name,**kwargs)
    stop = time.time()
    print(f"plot by id took {stop-start}")

    mainfolder = config.user.mainfolder
    experiment_name = dataset.exp_name
    sample_name = dataset.sample_name

    storage_dir = os.path.join(mainfolder, experiment_name, sample_name)
    os.makedirs(storage_dir, exist_ok=True)

    png_dir = os.path.join(storage_dir, 'png')
    pdf_dif = os.path.join(storage_dir, 'pdf')

    os.makedirs(png_dir, exist_ok=True)
    os.makedirs(pdf_dif, exist_ok=True)

    save_pdf = True
    save_png = True

    if filename is not None:
        f_name = f'{dataid}_{filename}'
    elif transform_name is not None:
        f_name = f'{dataid}_{transform_name}'
    else:
        f_name = f'{dataid}'

    for i, ax in enumerate(plots[0]):
        if save_pdf:
            full_path = os.path.join(pdf_dif, f'{f_name}_{i}.pdf')
            ax.figure.tight_layout(pad=3)
            ax.figure.savefig(full_path, dpi=500)
        if save_png:
            full_path = os.path.join(png_dir, f'{f_name}_{i}.png')
            ax.figure.tight_layout(pad=3)
            ax.figure.savefig(full_path, dpi=500)
    return plots

# Transform plot with user-defined functions
def transform_plot(axs_and_cbaxs: AxesTupleList, transform_name: str, *args):

    defined_functions = ['avg_row', 'avg_column', 'sub_avg_row' , 'sub_avg_column',
                        'xcut', 'ycut']
    name_string = ', '.join(defined_functions)

    modified_axs = []
    modified_cbaxs = []
    for ax, cbax in zip(*axs_and_cbaxs):
        if transform_name == 'avg_row':
            mod_ax, mod_cbax = avg_heatmap(ax, cbax,'row')
        elif transform_name == 'avg_column':
            mod_ax, mod_cbax = avg_heatmap(ax, cbax,'column')
        elif transform_name == 'sub_avg_row':
            mod_ax, mod_cbax = sub_avg_heatmap(ax, cbax,'row')
        elif transform_name == 'sub_avg_column':
            mod_ax, mod_cbax = sub_avg_heatmap(ax, cbax,'column')
        elif transform_name == 'xcut':
            mod_ax, mod_cbax = linecut(ax, cbax,'x',*args)
        elif transform_name == 'ycut':
            mod_ax, mod_cbax = linecut(ax, cbax,'y',*args)
        else:
            raise ValueError('Transform name not defined. '
                    f'Allowed names are: {name_string}.')
        mod_ax.figure.tight_layout()
        modified_axs.append(mod_ax)
        modified_cbaxs.append(mod_cbax)

    return modified_axs, modified_cbaxs

def get_axisdata(mesh: QuadMesh):
    """
    Helper function for analysis functions to get the datapoints of
    the x-, y-, and z-axis from a meshgrid's coordinates
    """
    # Extract datapoints
    coords = mesh._coordinates
    bins_x = coords[0][:, 0]
    delta = np.mean(np.diff(bins_x))
    xdata = bins_x[:-1] + delta/2

    bins_y = coords[:, 0][:, 1]
    delta = np.mean(np.diff(bins_y))
    ydata = bins_y[:-1] + delta/2

    flat_data = mesh.get_array()
    zdata = flat_data.reshape(len(ydata), len(xdata)).copy()

    return xdata, ydata, zdata.data.T

def avg_heatmap(
    ax: matplotlib.axes.Axes,
    cbax: Optional[matplotlib.colorbar.Colorbar],
    avg_dim: str) -> Tuple[matplotlib.axes.Axes,
                           Optional[matplotlib.colorbar.Colorbar]]:
    """
    Take a pair of Axes, Colorbar and average along one dimension if the axis
    holds a heatmap. Else just return the arguments unchanged.
    """
    # If we receive anything we can't recognize as a heatmap on a grid,
    # then we make no attempt of averaging, but just let the arguments
    # slip through
    if ax.collections == []:
        return ax, cbax

    if len(ax.collections) > 1:
        return ax, cbax

    mesh = ax.collections[0]
    if not isinstance(mesh, QuadMesh):
        return ax, cbax


    xlabel = ax.get_xlabel()
    ylabel = ax.get_ylabel()
    zlabel = cbax._label
    title = ax.get_title()

    data = get_axisdata(mesh)

    ax.clear()
    avg_dim_int = {'column': 0, 'row': 1}[avg_dim]
    ax.plot(data[avg_dim_int], np.mean(data[2].T, avg_dim_int))

    new_xlabel = {'column': xlabel, 'row': ylabel}[avg_dim]
    ax.set_xlabel(new_xlabel)

    ax.set_ylabel(zlabel)
    new_title = f"{title}\nAveraged by {avg_dim}"
    ax.set_title(new_title)
    cbax.remove()
    cbax = None

    return ax, cbax

def linecut(
    ax: matplotlib.axes.Axes,
    cbax: Optional[matplotlib.colorbar.Colorbar],
    cutdim: str,
    value: float) -> Tuple[matplotlib.axes.Axes,
                           Optional[matplotlib.colorbar.Colorbar]]:
    """
    Create linecut of from a heatmap
    """
    # If we receive anything we can't recognize as a heatmap on a grid,
    # then we make no attempt of averaging, but just let the arguments
    # slip through
    if ax.collections == []:
        return ax, cbax

    if len(ax.collections) > 1:
        return ax, cbax

    mesh = ax.collections[0]
    if not isinstance(mesh, QuadMesh):
        return ax, cbax


    xlabel = ax.get_xlabel()
    ylabel = ax.get_ylabel()
    zlabel = cbax._label
    title = ax.get_title()

    data = get_axisdata(mesh)

    # Find cut index based on nearest point to given value
    if cutdim not in ['x', 'y']:
        raise ValueError(f'Cutdim has to be row or column but was given {cutdim}')
    cut_dim_int = {'x': 0, 'y': 1}[cutdim]
    idx = (np.abs(data[cut_dim_int] - value)).argmin()
    
    ax.clear()
    if cutdim == 'x':
        zdata = data[2][idx,:]
    else:
        zdata = data[2][:,idx]

    ax.plot(data[np.mod(cut_dim_int+1,2)], zdata)

    new_xlabel = {'y': xlabel, 'x': ylabel}[cutdim]
    ax.set_xlabel(new_xlabel)

    ax.set_ylabel(zlabel)
    fixed_label = {'x': xlabel, 'y': ylabel}[cutdim]
    new_title = f"{title}\nLine cut at: {fixed_label} = {data[cut_dim_int][idx]}"
    ax.set_title(new_title)
    cbax.remove()
    cbax = None
    return ax, cbax

def sub_avg_heatmap(
    ax: matplotlib.axes.Axes,
    cbax: Optional[matplotlib.colorbar.Colorbar],
    avg_dim: str) -> Tuple[matplotlib.axes.Axes,
                           Optional[matplotlib.colorbar.Colorbar]]:
    """
    Take a pair of Axes, Colorbar and subtract average along one dimension if the
    axis holds a heatmap. Else just return the arguments unchanged.
    """
    # If we receive anything we can't recognize as a heatmap on a grid,
    # then we make no attempt of averaging, but just let the arguments
    # slip through
    if ax.collections == []:
        return ax, cbax

    if len(ax.collections) > 1:
        return ax, cbax

    mesh = ax.collections[0]
    if not isinstance(mesh, QuadMesh):
        return ax, cbax


    zlabel = cbax._label

    data = get_axisdata(mesh)
    
    avg_dim_int = {'column': 0, 'row': 1}[avg_dim]
    if avg_dim_int == 0:
        for i in range(np.shape(data[2])[0]):
            data[2][i,:] -= np.nanmean(data[2][i,:])
    if avg_dim_int == 1:
        for i in range(np.shape(data[2])[1]):
            data[2][:,i] -= np.nanmean(data[2][:,i])
    mesh.set_array(np.transpose(data[2]).ravel())
    mesh.autoscale()
    
    new_cblabel = f"{zlabel}\n - {avg_dim}-average"
    cbax.set_label(new_cblabel)

    return ax, cbax
