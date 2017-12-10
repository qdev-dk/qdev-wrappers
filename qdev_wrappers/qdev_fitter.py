import qcodes as qc
import numpy as np
import types
from os.path import sep
import matplotlib.pyplot as plt
import scipy.fftpack as fftpack
from scipy.optimize import curve_fit

from qdev_wrappers.show_num import check_experiment_is_initialized

class qdev_fitter():
    def __init__(self):
        self.T1 = T1()
        self.T2 = T2()

    def fit(self, id, fitclass, do_plots=True, dataname=None, samplefolder=None, p0=None,**kwargs):

        str_id = '{0:03d}'.format(id)
        if samplefolder==None:
            check_experiment_is_initialized()

            path = qc.DataSet.location_provider.fmt.format(counter=str_id)
            data = qc.load_data(path)
        else:
            path = '{}{}{}'.format(samplefolder,sep,str_id)
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

        # Do fits separately for 1D and 2D datasets
        keys_set = [key for key in data.arrays.keys() if "_set" in key[-4:]]

        # Do fit and plot for 1D data
        if len(keys_set) == 1:
            qcxdata = getattr(data, keys_set[0])
            qcydata = getattr(data, key_data[0])
            # Get initial guess on parameter is guess function is defined
            if (p0==None and hasattr(fitclass,'guess')):
                p0 = getattr(fitclass,'guess')(qcxdata.ndarray,qcydata.ndarray)
            popt, pcov = popt, pcov = curve_fit(fitclass.fun, qcxdata.ndarray, qcydata.ndarray, p0=p0, **kwargs)

            if do_plots:
                plot = self.plot_1D(qcxdata,qcydata,fitclass,popt)
                title_list = plot.get_default_title().split(sep)
                title_list.insert(-1, 'analysis')
                title = sep.join(title_list)
                plt.savefig("{}_{}.png".format(title,fitclass.name),dpi=500)
                return popt, pcov, plot
            else:
                return popt, pcov
        if len(keys_set) == 2:
            print('Fitting for 2D datasets not implemented.')


    def plot_1D(self,qcxdata,qcydata,fitclass,popt):
        plot = qc.MatPlot(qcydata,marker='.',markersize=5,linestyle='',color='C0',figsize=(6.5,4))
        plot.fig.tight_layout(pad=3)
        plot.rescale_axis()
        xdata = qcxdata.ndarray
        p_label_list = []
        for i in range(len(fitclass.p_names)):
            ax_letter = fitclass.p_units[i]
            if ax_letter in ['x','y']:
                unit = getattr(plot.subplots[0], 'get_{}label'.format(ax_letter))().split('(')[1].split(')')[0]
                scaled = float(getattr(plot.subplots[0], '{}axis'.format(ax_letter)).get_major_formatter()(popt[i]))
            elif ax_letter in ['1/x','1/y']:
                unit = '/{}'.format(getattr(plot.subplots[0], 'get_{}label'.format(ax_letter[2]))().split('(')[1].split(')')[0])
                scaled = 1/float(getattr(plot.subplots[0], '{}axis'.format(ax_letter[2])).get_major_formatter()(1/popt[i]))
            else:
                unit = ax_letter
                scaled = popt[i]
            p_label_list.append('{} = {:.3g} {}'.format(fitclass.p_names[i],scaled,unit))
        x = np.linspace(xdata.min(),xdata.max(),len(xdata)*10)
        plot[0].axes.plot(x,fitclass.fun(x,*popt),color='C0')
        plot[0].figure.text(0.8, 0.45, '\n'.join(p_label_list),bbox={'ec':'k','fc':'w'})
        plot.subplots[0].set_title(fitclass.fun_str)
        plt.subplots_adjust(right=0.78)
        plt.draw()
        return plot


#  Predefined fucntions
class T1():
    def __init__(self):
        self.name = 'T1fit'
        self.fun_str = r'$f(x) = a \exp(-x/T) + c$'
        self.p_names = [r'$a$',r'$T$',r'$c$']
        self.p_units = ['y','x','y']

    def fun(self,x,a,T,c):
        val = a*np.exp(-x/T)+c
        return val

    def guess(self,x,y):
        l = len(y)
        val_init = y[0:round(l/20)].mean()
        val_fin = y[-round(l/20):].mean()
        a = val_init - val_fin
        c = val_fin
        # guess T1 as point where data has falen to 1/e of init value
        idx = (np.abs(y-a/np.e-c)).argmin()
        T = x[idx]
        return [a,T,c]


class T2():
    def __init__(self):
        self.name = 'T2fit'
        self.fun_str = r'$f(x) = a \sin(\omega x +\phi)\exp(-x/T) + c$'
        self.p_names = [r'$a$',r'$T$',r'$\omega$',r'$\phi$',r'$c$']
        self.p_units = ['y','x','1/x','','y']

    def fun(self,x,a,T,w,p,c):
        val = a*np.exp(-x/T)*np.sin(w*x+p)+c
        return val

    def guess(self,x,y):
        a = y.max() - y.min()
        c = y.mean()
        # guess T2 as point half way point in data
        T = x[round(len(x)/2)]
        # Get initial guess for frequency from a fourier transform
        yhat = fftpack.rfft(y-y.mean())
        idx = (yhat**2).argmax()
        freqs = fftpack.rfftfreq(len(x), d = (x[1]-x[0])/(2*np.pi))
        w = freqs[idx]
        p = 0
        return [a,T,w,p,c]