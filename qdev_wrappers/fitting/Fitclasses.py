
import qcodes as qc
import numpy as np
import scipy.fftpack as fftpack


class LeastSquaresFit:
    def __init__(self):
        self.name = 'NoName'
        self.fun_str = 'None'
        self.p_names = ['none']
        self.p_units = ['none']

    def fun(self, x, a, T, c):
        raise NotImplementedError('This is not implemented in the base class.')

    def guess(self, x, y):
        raise NotImplementedError('This is not implemented in the base class.')


class T1(LeastSquaresFit):
    
    def __init__(self):
        self.name = 'T1fit'
        self.fun_str = r'$f(x) = a \exp(-x/T) + c$'
        self.fun_np = 'a*np.exp(-x/T)+c'
        self.fun_vars = ['x']
        self.fun_output = ['y']
        self.p_names = ['$a$', '$T$', '$c$']
        self.p_labels= ['a', 'T', 'c']
        self.p_units = ['y', 'x', 'y']                                        
                                                    
    def fun(self, x, a, T, c):
        val = a*np.exp(-x/T)+c
        return val

    def guess(self, x, y):
        l = len(y)
        val_init = y[0:round(l/20)].mean()
        val_fin = y[-round(l/20):].mean()
        a = val_init - val_fin
        c = val_fin
        # guess T1 as point where data has fallen to 1/e of init value
        idx = (np.abs(y-a/np.e-c)).argmin()
        T = x[idx]
        return [a, T, c]


class T2(LeastSquaresFit):
    
    def __init__(self):
        self.name = 'T2fit'
        self.fun_str = r'$f(x) = a \sin(\omega x +\phi)\exp(-x/T) + c$'
        self.fun_np = 'a*np.exp(-x/T)*np.sin(w*x+p)+c'
        self.fun_vars = ['x']
        self.fun_output = ['y']
        self.p_names = ['$a$', '$T$', '$\omega$', '$\phi$', '$c$']
        self.p_labels = ['a', 'T', 'w', 'p', 'c']
        self.p_units = ['y', 'x', '1/x', '', 'y']                 

    def fun(self, x, a, T, w, p, c):
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
