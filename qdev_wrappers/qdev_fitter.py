import qcodes as qc
import numpy as np
import types
from os.path import sep
import matplotlib.pyplot as plt
import scipy.fftpack as fftpack
from scipy.optimize import curve_fit

from qdev_wrappers.file_setup import CURRENT_EXPERIMENT




def qdev_fitter(id, fitfunciton_in, samplefolder=None, dataname=None, p0=None,**kwargs):


    # Load data from active samplefolder or input samplefolder.
    if samplefolder==None:
        check_experiment_is_initialized()
        str_id = '{0:03d}'.format(id)

        path = qc.DataSet.location_provider.fmt.format(counter=str_id)
        data = qc.load_data(path)
    else:
        path = '{}{0:03d}'.format(samplefolder,id)
        data = qc.load_data(path)

    # Get handle for fitting function
    if isinstance(fitfunciton_in,str):
        if fitfunciton_in not in list(globals().keys()):
            print('Fitfunction not defined.')
            break
        if (p0==None and '{}_guess'.format(fitfunciton_in) in list(globals().keys())):
            p0 = globals()['{}_guess'.format(fitfunciton_in)](x,y)
        fitfunciton = globals()['{}'.format(fitfunciton_in)]
    elif isinstance(fitfunciton_in,types.FunctionType):
        fitfunciton = fitfunciton_in
    else:
        print('Invalid input. Only takes strings of predefined fucntions or function input.')


    # Get dataname to be fitted
    if dataname==None:
        # Function only made for a single dataname. Check there isnt more datanames in the dataset.
        key_data = [key for key in data.arrays.keys() if "_set" not in key[-4:]]
        if len(key_data) != 1:
            print('Dataset has more than one dataname. Choose dataname to be fitted from:')
            for i in key_data:
                print(i)
            break
    else:
        # Check input dataname is in dataset.
        if dataname not in [key for key in data.arrays.keys() if "_set" not in key[-4:]]
            print('Dataname not in dataset. Input dataname was: \'{}\' while dataname(s) in dataset are:'.format(dataname))
            for i in [key for key in data.arrays.keys() if "_set" not in key[-4:]]:
                print(i)
            break
        key_data = [dataname]


    # Do fits separately for 1D and 2D datasets
    keys_set = [key for key in data.arrays.keys() if "_set" in key[-4:]]
    if len(keys_set) == 1:
        xdata = getattr(getattr(data, keys_set), 'ndarray')
        ydata = getattr(getattr(data, key_data), 'ndarray')
        popt, pcov = popt, pcov = curve_fit(globals()[fitfunciton], x, y, p0=p0, **kwargs)
        plot = plot_1D(data,fitfunction,popt)
        title_list = plot.get_default_title().split(sep)
        title_list.insert(-1, CURRENT_EXPERIMENT['analysis'])
        title_png = sep.join(title_list_png)
        plt.savefig("{}_{}.png".format(title_png,fitfunciton.__name__),dpi=500)
        return popt, pcov, plot


    if len(keys_set) == 2:
        if xname==None:
            print('Need fitting dimension for 2D datasets. Choose fit dimension from:')
            for i in keys_set:
                print(i)
            break
        for i in
            print('Fitting not ready for 2D datasets.')
            break


def check_experiment_is_initialized():
    if not getattr(CURRENT_EXPERIMENT, "init", True): 
        raise RuntimeError("Experiment not initalized. "
                           "use qc.Init(mainfolder, samplename) "
                           "or provide path to sample folder.")

def plot_1D(data,fitfunction,popt):
    plot = qc.MatPlot(data)
    keys_set = [key for key in data.arrays.keys() if "_set" in key[-4:]]
    xdata = getattr(getattr(data, keys_set), 'ndarray')
    x = np.linspace(xdata.min(),xdata.max(),len(xdata)*10)
    plot[0].axes.plot(x,fitfunciton(x,*popt),
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

def T1_guess(x,y)
    l = len(y)
    val_init = y[0:round(l/20)].mean()
    val_fin = y[-round(l/20):].mean()
    a = val_init - val_fin
    c = val_fin
    # guess T1 as point where data has falen to 1/e of init value
    idx = (np.abs(y-a/np.e-c)).argmin()
    T = x[idx]
    return [a,T,c]

def T2(x,a,T,w,p,c)
    val = a*np.exp(-x/T)*np.sin(w*x+p)+c
    return val

def T2_guess(x,y)
    l = len(data)
    val_init = data[0:round(l/20)].mean()
    val_fin = data[-round(l/20):].mean()
    a = (val_init - val_fin)
    c = val_fin
    # guess T2 as point half way point in data
    T = x[round(l/2)]
    # Get initial guess for frequency from a fourier transform
    yhat = fftpack.rfft(y)
    idx = (yhat**2).argmax()
    freqs = fftpack.rfftfreq(N, d = (x[1]-x[0])/(2*pi))
    w = freqs[idx]
    p = 0
    return [a,T,w,p,c]










