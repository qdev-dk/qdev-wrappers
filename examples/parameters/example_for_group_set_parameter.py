from qdev_wrappers.parameters import GroupSetParameter
from qcodes.instrument_drivers.QDev.QDac_channels import QDac

qdac = QDac('qdac', address='ASRL4::INSTR', update_currents=False)

p = GroupSetParameter('bound_channels', qdac.ch01.v, qdac.ch02.v)
