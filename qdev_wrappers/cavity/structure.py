## Parameters / default values
# config.parameter style

##--Pulse-&-MW--------------
channel_mapping = {} # dictionary for functional channel name and instrument channel name
# goes into StationConfig
# integrate into broadbean
def apply_channel_mapping(mapping, sequence)->sequence:
    pass

def create_pulse():
    # does the full pulse
    # driving and readout pulse
def create_readout_pulse():
    pass

def create_drive_pulse():
    pass


##--Analysis-----------------
def calc_integration_delay(trace:nparray) -> float:
    pass

def calc_resonator_frequency(trace:nparray) -> float:
    pass

def calc_readout_detuning() -> float:
    return 15e6

##--control-----------------
def run_experiment(instruments, pulse, microwave_settings, acquisition_settings, sweep)
    # pulse (+MW)
    # Readout (Alazar-sequencing mode)
    # sweep

def run_integration_time_measurement():
    # does the actual experiment
    # sets up instruments
    run_experiment()
