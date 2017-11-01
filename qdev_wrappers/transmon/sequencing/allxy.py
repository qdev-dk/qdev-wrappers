from . import make_sequence_from_gate_lists

# TODO: pulse_mod

################################################################
# ALLXY
################################################################


allxy_gates = [['I', 'I'],
               ['X', 'X'],
               ['Y', 'Y'],
               ['X', 'Y'],
               ['Y', 'X'],
               ['X/2', 'I'],
               ['Y/2', 'I'],
               ['X/2', 'Y/2'],
               ['Y/2', 'X/2'],
               ['X/2', 'Y'],
               ['Y/2', 'X'],
               ['X', 'Y/2'],
               ['Y', 'X/2'],
               ['X/2', 'X'],
               ['X', 'X/2'],
               ['Y/2', 'Y'],
               ['Y', 'Y/2'],
               ['X', 'I'],
               ['Y', 'I'],
               ['X/2', 'X/2'],
               ['Y/2', 'Y/2']]


def make_allxy_sequence(SSBfreq=None, drag=False, channels=[1, 2, 3, 4],
                        spacing=None, gaussian=True):
    seq = make_sequence_from_gate_lists(
        allxy_gates, SSBfreq=SSBfreq, drag=drag, gaussian=gaussian,
        variable_label=None, spacing=spacing, name='allxy_seq')
    seq.labels = {'seq_type': 'allxy', 'pulse_mod': False}
    return seq
