'''This module plots measurement runs in real time.

To start the plotting daemon, run this module on a stand-alone Python terminal.
It will not work on a Spyder console because of multiprocessing voodoo.'''


import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
import matplotlib.animation as animation
from qcodes.dataset.plotting import plot_by_id
from qcodes.dataset.data_set import load_by_id
from qcodes.dataset.experiment_container import (load_last_experiment,
                                                 load_experiment)
from multiprocessing import Process, Pool
import time
from qcodes.config.config import Config
import os.path
import os


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
    

def make_filename(run_id):
    extension = 'pdf'
    db_path = Config()['core']['db_location']
    db_folder = os.path.dirname(db_path)
    plot_folder_name = 'plots'
    plot_folder = os.path.join(db_folder, plot_folder_name)
    os.makedirs(plot_folder, exist_ok=True)
    filename = '{}.{}'.format(run_id, extension)
    plot_path = os.path.join(plot_folder, filename)
    return plot_path
    

def is_completed(run_id):
    '''Check if the run from run_id has already finished.
    
    TODO: this function should check for dataset.completed instead of a new
    run, but dataset.completed is currently broken.'''
    
    return is_there_new_run(run_id)


def save_figure(filename):
    '''Save the current figure at filename.'''
    try:
        plt.savefig(filename, bbox_inches='tight')
        print('Saved plot at {}.'.format(filename))
    except PermissionError:
        print('File {} already exists, did not save plot.'.format(filename))


def run_animation(run_id, interval=1., save=True):
    '''Run an animation from run_id.'''
    plt.ioff()
    plt.rcParams.update({'figure.max_open_warning': 0})
    print('Started plotting run_id {}.'.format(run_id))
    fig, axes, cbars = prepare_figure(run_id)
    if save:
        if type(save) is str:
            filename = save
        else:
            filename = make_filename(run_id)
    
    def get_frame():
        '''Keep iterating the animation as long as there isn't a new run.'''
        
        while not is_completed(run_id):
            yield 'active'
        print('Stopped plotting run_id {}.'.format(run_id))
        if save:
            save_figure(filename)
    
    anim = animation.FuncAnimation(fig, refresh, get_frame,
                                   interval=interval * 1000,
                                   repeat=False,
                                   fargs=(run_id, fig, axes, cbars))
    plt.show()
    print('Closed plot for run_id {}.'.format(run_id))
    
    
def listen(interval=1., save=True, current=True):
    '''Listen for a new run, then spawn an animation and a new listener.
    
    The current parameter is a workaround for dataset.completed not working.
    If current == True, the last run_id will be plotted even if it was run
    before the daemon started. It will be replaced with a check whether the
    last run_id is still running or not.'''
    
    last_run_id = get_last_run_id()
    print('Listening for new run...')
    while not is_there_new_run(last_run_id) and not current:
        time.sleep(interval)
    new_run_id = get_last_run_id()
    p_animate = Process(target=run_animation, args=(new_run_id, interval,
                                                    save))
    p_listen = Process(target=listen, args=(interval, save, False))
    p_animate.start()   
    p_listen.start()
    p_animate.join()
    p_listen.join()        


if __name__ == '__main__':
    listen()
