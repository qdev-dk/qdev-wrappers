import numpy as np

from qcodes import initialise_database, new_experiment, Parameter
from qcodes.dataset.measurements import Measurement
from qcodes.dataset.plotting import plot_dataset

from slow_demodulation.down_converter import DownConverter


class DummyArray(Parameter):
    def get_raw(self):
        npoints = 1000
        return np.random.rand(npoints)


if __name__ == "__main__":

    
    initialise_database()
    new_experiment(
            name='slow demodulation test',
            sample_name="test script sample")

    source = DummyArray('source')

    d = DownConverter(
        'test_demodulator',
        source_parameter=source,
        sample_rate=1000)
    d.set_demodulation_frequencies(np.array([1, 2, 3]))
    meas = Measurement()
    meas.register_parameter(d.down_converted_signal)

    with meas.run() as datasaver:
        datasaver.add_result(
            (d.demodulation_frequencies, d.demodulation_frequencies()),
            (d.down_converted_signal, d.down_converted_signal())
        )

    plot_dataset(datasaver.dataset)
