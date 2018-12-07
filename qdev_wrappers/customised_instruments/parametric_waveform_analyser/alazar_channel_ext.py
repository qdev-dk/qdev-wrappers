from qdev_wrappers.customised_instruments.alazar_tech.alazar_channel import AlazarChannel
from typing import Dict, Union


class AlazarChannel_ext(AlazarChannel):
    """
    An extension to the Alazar channel which has added
    convenience function for updating records, buffers
    and setpoints from dictionary
    """

    def __init__(self, parent, name: str,
                 demod: bool=False,
                 alazar_channel: str='A',
                 average_buffers: bool=True,
                 average_records: bool=True,
                 integrate_samples: bool=True):
        super().__init__(parent, name, demod=demod,
                         alazar_channel=alazar_channel,
                         average_buffers=average_buffers,
                         average_records=average_records,
                         integrate_samples=integrate_samples)

    def update(self,
               settings: Dict[str, Union[int, float, str, bool]]):
        """
        Updates the setpoints, setpoint names and setpoint labels and
        the num_averages/num_reps of the channel.

        NB Fails if the new settings require a change in averaging
            settings such as changing the state of 'average_records'
        """
        fail = False
        if settings['average_records'] != self._average_records:
            fail = True
        elif settings['average_buffers'] != self._average_buffers:
            fail = True
        if fail:
            raise RuntimeError(
                'alazar channel cannot be updated to change averaging '
                'settings, run clear_channels before changing settings')
        self.records_per_buffer._save_val(settings['records'])
        self.buffers_per_acquisition._save_val(settings['buffers'])
        if self.dimensions == 1 and self._integrate_samples:
            self.prepare_channel(
                setpoints=settings['record_setpoints'],
                setpoint_name=settings['record_setpoint_name'],
                setpoint_label=settings['record_setpoint_label'],
                setpoint_unit=settings['record_setpoint_unit'])
        else:
            self.prepare_channel(**settings)
