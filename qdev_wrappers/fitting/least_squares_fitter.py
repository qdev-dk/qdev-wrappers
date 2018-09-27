from qcodes.instrument.base import Instrument
from scipy.optimize import curve_fit

class LeastSquaresFitter(Instrument):

    def __init__(self, name, model, guess):
        super().__init__(name)
        self.model = model
        self.guess = guess

        for param_name, param_kwargs in self.model.model_parameters.items():
            self.add_parameter(param_name, set_cmd=False, **param_kwargs)

    def update(self, input_data_array, output_data_array):

        # find start parameters, run curve_fit function to perform fit
        p_guess = self.guess.make_guess(input_data_array, output_data_array)
        popt, pcov = curve_fit(self.model.func,
                               input_data_array,
                               output_data_array,
                               p0=p_guess)

        # update guess and fit results in fitter parameters
        for i, param in enumerate(self.model.modelparam_names):
            self.parameters[param]._save_val(popt[i])
            self.parameters[param].start_value = p_guess[i]
            self.parameters[param].variance = pcov[i, i]
