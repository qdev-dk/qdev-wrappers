from qdev_wrappers.customised_instruments import VNA_cQED


class my_very_local_VNA(VNA_cQED):
    def __init__(self, name, visa_address, S21=True, spec_mode=False,
                 gen_address=None, timeout=40):
        super().__init__(name, visa_address, init_s_params=False,
                         timeout=timeout)
        self.call('*RST')
