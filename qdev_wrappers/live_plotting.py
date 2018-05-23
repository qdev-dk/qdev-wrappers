'''This module plots measurement runs in real time.

To start the plotting daemon, run this module on a stand-alone Python terminal.
It will not work on a Spyder console because of multiprocessing voodoo.'''


import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from qcodes.dataset.plotting import plot_by_id
from qcodes.dataset.data_set import load_by_id
from qcodes.dataset.experiment_container import (load_last_experiment,
                                                 load_experiment)
from multiprocessing import Process, Pool
import time


def make_title_from_id(run_id):
    '''Make a descriptive title from a run_id.'''
    dataset = load_by_id(run_id)
    experiment = load_experiment(dataset.exp_id)
    title = '{} on {} (run ID {})'
    title = title.format(experiment.name, experiment.sample_name,
                         dataset.run_id)
    return title


def get_last_run_id():
    '''Get the last run_id.'''
    last_experiment = load_last_experiment()
    last_dataset = last_experiment.last_data_set()
    last_run_id = last_dataset.run_id
    return last_run_id
        
        
def is_there_new_run(run_id):
    '''Check if a new run has been started.'''
    return not run_id == get_last_run_id()
        

def safe_plot_by_id(run_id, axes=None):
    '''Catch some database access errors that randomly occur when loading.'''
    while True: 
        try:
            return plot_by_id(run_id, axes)
        except:
            pass
        

def refresh(mode, run_id, figure, axes, cbars):
    '''Call plot_by_id to plot the available data on axes.'''
    if mode == 'freeze':
        return
    for axis in axes:
        axis.clear()
    for cbar in cbars:
        if cbar is not None:
            cbar.remove()
    new_axes, new_cbars = safe_plot_by_id(run_id, axes)
    for i, _ in enumerate(cbars):
        cbars[i] = new_cbars[i]
    return axes, cbars


def prepare_figure(run_id):
    '''Prepare a figure to plot on, assuming that the X axis is shared.'''
    axes, _ = safe_plot_by_id(run_id)
    num_axes = len(axes)
    plt.close('all')
    fig, axes = plt.subplots(num_axes, 1, sharex=True)
    for axis in axes[:-1]:
        axis.get_xaxis().get_label().set_visible(False)
    axes, cbars = safe_plot_by_id(run_id, axes)
    title = make_title_from_id(run_id)
    fig.suptitle(title)
    return fig, axes, cbars
    

def run_animation(run_id, interval=1.):
    '''Run an animation from run_id.'''
    print('Started plotting run_id {}.'.format(run_id))
    fig, axes, cbars = prepare_figure(run_id)
    
    def get_frame():
        '''Keep iterating the animation as long as there isn't a new run.
        
        If there is a new run, but auto_close == False, keep iterating the
        animation without updating it ('freeze' mode).
        TODO: this function should check for dataset.completed instead of a new
        run, but dataset.completed is currently broken.'''
        
        while not is_there_new_run(run_id):
            yield 'active'
        print('Stopped plotting run_id {}.'.format(run_id))
    
    anim = animation.FuncAnimation(fig, refresh, get_frame,
                                   interval=interval * 1000,
                                   repeat=False,
                                   fargs=(run_id, fig, axes, cbars))
    plt.show()
    print('Closed plot for run_id {}.'.format(run_id))
    
    
def listen(interval=1.):
    '''Listen for a new run, then spawn an animation and a new listener.'''        
    plt.ioff()
    last_run_id = get_last_run_id()
    print('Listening for new run...')
    while not is_there_new_run(last_run_id):
        time.sleep(interval)
    new_run_id = get_last_run_id()
    p_animate = Process(target=run_animation, args=(new_run_id, interval))
    p_listen = Process(target=listen, args=(interval, ))
    p_animate.start()   
    p_listen.start()
    p_animate.join()
    p_listen.join()        


if __name__ == '__main__':
    listen()
