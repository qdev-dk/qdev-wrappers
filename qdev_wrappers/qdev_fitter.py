import qcodes as qc
import numpy as np
import types
from os.path import sep
import matplotlib.pyplot as plt
import scipy.fftpack as fftpack
from scipy.optimize import curve_fit

from qdev_wrappers.file_setup import CURRENT_EXPERIMENT




def qdev_fitter(id, fitfunction_in, do_plots=True, dataname=None, samplefolder=None, p0=None,**kwargs):


    # Load data from active samplefolder or input samplefolder.
    if samplefolder==None:
        check_experiment_is_initialized()
        str_id = '{0:03d}'.format(id)

        path = qc.DataSet.location_provider.fmt.format(counter=str_id)
        data = qc.load_data(path)
    else:
        path = '{}{0:03d}'.format(samplefolder,id)
        data = qc.load_data(path)

    # Get dataname to be fitted
    if dataname==None:
        # Function only made for a single dataname. Check there isnt more datanames in the dataset.
        key_data = [key for key in data.arrays.keys() if "_set" not in key[-4:]]
        if len(key_data) != 1:
            raise RuntimeError('Dataset has more than one dataname. Choose dataname to be fitted from: {}.'.format(', '.join(key_data)))
    else:
        # Check input dataname is in dataset.
        if dataname not in [key for key in data.arrays.keys() if "_set" not in key[-4:]]:
            raise RuntimeError('Dataname not in dataset. Input dataname was: \'{}\' while dataname(s) in dataset are: {}.'.format(dataname,', '.join(key_data)))
        key_data = [dataname]

    # Get handle for fitting function
    if isinstance(fitfunction_in,str):
        if fitfunction_in not in list(globals().keys()):
            raise RuntimeError('Fitfunction not defined.')
        fitfunction = globals()['{}'.format(fitfunction_in)]
    elif isinstance(fitfunction_in,types.FunctionType):
        fitfunction = fitfunction_in
    else:
        print('Invalid input. Only takes strings of predefined fucntions or function input.')

    # Do fits separately for 1D and 2D datasets
    keys_set = [key for key in data.arrays.keys() if "_set" in key[-4:]]
    if len(keys_set) == 1:
        xdata = getattr(getattr(data, keys_set[0]), 'ndarray')
        ydata = getattr(getattr(data, key_data[0]), 'ndarray')
        if (p0==None and '{}_guess'.format(fitfunction_in) in list(globals().keys())):
            p0 = globals()['{}_guess'.format(fitfunction_in)](xdata,ydata)
        popt, pcov = popt, pcov = curve_fit(fitfunction, xdata, ydata, p0=p0, **kwargs)
        if do_plots:
            plot = plot_1D(getattr(data, keys_set[0]),getattr(data, key_data[0]),fitfunction,popt)
            title_list = plot.get_default_title().split(sep)
            title_list.insert(-1, 'analysis')
            title = sep.join(title_list)
            plt.savefig("{}_{}.png".format(title,fitfunction.__name__),dpi=500)
            return popt, pcov, plot
        else:
            return popt, pcov

    if len(keys_set) == 2:
        if xname==None:
            raise RuntimeError('Need fitting dimension for 2D datasets. Choose fit dimension from: {}.'.format(', '.join(keys_set)))
        raise RuntimeError('Fitting not ready for 2D datasets.')


def check_experiment_is_initialized():
    if not getattr(CURRENT_EXPERIMENT, "init", True): 
        raise RuntimeError("Experiment not initalized. "
                           "use qc.Init(mainfolder, samplename) "
                           "or provide path to sample folder.")

def plot_1D(qcxdata,qcydata,fitfunction,popt):
    plot = qc.MatPlot(qcydata,marker='.',markersize=10,linestyle='')
    xdata = getattr(qcxdata, 'ndarray')
    x = np.linspace(xdata.min(),xdata.max(),len(xdata)*10)
    plot[0].axes.plot(x,fitfunction(x,*popt),
        label='\n'.join(['p{} = {:.3g}'.format(n,m) for n, m in enumerate(popt)]))
    plot.rescale_axis()
    ax.set_title(title)
    plot[0].axes.legend(loc='upper right', fontsize=10)
    plot.draw()
    return plot



#  Predefined fucntions


def T1(x,a,T,c):
    val = a*np.exp(-x/T)+c
    return val

def T1_guess(x,y):
    l = len(y)
    val_init = y[0:round(l/20)].mean()
    val_fin = y[-round(l/20):].mean()
    a = val_init - val_fin
    c = val_fin
    # guess T1 as point where data has falen to 1/e of init value
    idx = (np.abs(y-a/np.e-c)).argmin()
    T = x[idx]
    return [a,T,c]

def T2(x,a,T,w,p,c):
    val = a*np.exp(-x/T)*np.sin(w*x+p)+c
    return val

def T2_guess(x,y):
    a = y.max() - y.min()
    c = y.mean()
    # guess T2 as point half way point in data
    T = x[round(len(x)/2)]
    # Get initial guess for frequency from a fourier transform
    yhat = fftpack.rfft(y)
    idx = (yhat**2).argmax()
    freqs = fftpack.rfftfreq(len(x), d = (x[1]-x[0])/(2*np.pi))
    w = freqs[idx]
    p = 0
    return [a,T,w,p,c]