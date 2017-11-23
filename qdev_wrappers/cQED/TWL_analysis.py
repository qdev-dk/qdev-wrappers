import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit



def Lorentzian(x,a,x0,gamma,c):
    values = a*gamma**2/((x-x0)**2+gamma**2) + c
    return values


def Qfit_mag(number):
    data, plot = show_num(number)
    keys = data.arrays.keys()
    for i in keys:
        if i != 'VNA_S21_magnitude':
            if i != 'VNA_S21_phase':
                if i != 'frequency_set':
                    ykey = i
            
    ykey
    Xdata = data.arrays['frequency_set'][0,:]
    Ydata = data.arrays[ykey]
    Zdata = data.arrays['VNA_S21_magnitude']
    Q = np.zeros(len(Ydata))
    for i in range(len(Ydata)):
        pguess = np.array([Zdata[i,:].max(), Xdata[Zdata[i,:].argmax()], 200E3,0.2])
        popt, pcov = curve_fit(Lorentzian,Xdata,Zdata[i,:],p0 = pguess)
        Q[i] = popt[1]/(2*popt[2])
        
    fig1, ax1 = plt.subplots(figsize=(12,8))
    plt.plot(Ydata,Q,'b-',lw=2)
    plt.ylabel('Q factor')
    plt.xlabel(data.metadata['arrays'][ykey]['label'] + ' (' + data.metadata['arrays'][ykey]['unit'] + ')' )
    plt.show()
    
    
    
    
do1d(deca.lplg,0,0.01,1001,0.001,vna.single_S21_mag)
do1d(deca.jj,-1.5,-1.2,601,0.01,vna.single_S21_mag)
do1d(deca.lplg,0,0.01,1001,0.001,vna.single_S21_mag)