# Majorana
Wrappers for Majorana QCoDeS, William's refactoring

The repository contains the following files:

* Experiment_init.py: Sets up a QCoDeS station, the config object, the device annotator, and the commands.log
* sample.config: Configuration file containing settings like BNC connection numbers, IV convertion settings
* reload_settings.py: A module containing functions that perform handy tasks such as reloading instruments.
* majorana_wrappers.py: Contains T10-specific versions of do1d, i.e. do1d_M, do2d_M.
* fast_diagrams.py: Contains the `fast_charge_diagram` function. 

The refactoring is based on the following idea: there are two global objects, the station and the config. Everything else
should be a function in a module, a function potentially digging into those two global objects.
