import random
import numpy as np
from . import make_sequence_from_gate_lists

# TODO: pulse_mod
# TODO: use or delete decompose matrix

clifford_rotations = [
    ['I'],
    ['X'],
    ['Y'],
    ['X/2'],
    ['-X/2'],
    ['Y/2'],
    ['-Y/2'],
    ['Y', 'X'],
    ['X/2', 'Y/2'],
    ['X/2', '-Y/2'],
    ['-X/2', 'Y/2'],
    ['-X/2', '-Y/2'],
    ['Y/2', 'X/2'],
    ['Y/2', '-X/2'],
    ['-Y/2', 'X/2'],
    ['-Y/2', '-X/2'],
    ['X', 'Y/2'],
    ['X', '-Y/2'],
    ['Y', 'X/2'],
    ['Y', '-X/2'],
    ['-X/2', 'Y/2', 'X/2'],
    ['-X/2', '-Y/2', 'X/2'],
    ['X/2', 'Y/2', 'X/2'],
    ['-X/2', 'Y/2', '-X/2']]

gate_mat_dict = {
    'I': np.matrix([[1, 0], [0, 1]]),
    'X': np.matrix([[0, -1j], [-1j, 0]]),
    'X/2': np.matrix([[1, -1j], [-1j, 1]]) / np.sqrt(2),
    '-X/2': np.matrix([[1, 1j], [1j, 1]]) / np.sqrt(2),
    'Y': np.matrix([[0, -1], [1, 0]]),
    'Y/2': np.matrix([[1, -1], [1, 1]]) / np.sqrt(2),
    '-Y/2': np.matrix([[1, 1], [-1, 1]]) / np.sqrt(2)
}


def choose_random_gate():
    i = random.randint(0, 23)
    return clifford_rotations[i]


def make_random_gate_list(length):
    gate_list = []
    for i in range(length):
        gate_list.extend(choose_random_gate())
    return gate_list


def gates_to_mat(gate_list):
    current_mat = np.matrix([[1, 0], [0, 1]])
    for gate in gate_list:
        gate_mat = gate_mat_dict[gate]
        current_mat = gate_mat * current_mat
    return current_mat


def invert_mat(mat):
    return np.linalg.inv(mat)


def mat_to_gates(mat):
    for clif_rot in clifford_rotations:
        clif_mat = gates_to_mat(clif_rot)
        clif_mat_i = 1j * clif_mat
        if np.allclose(mat, clif_mat):
            return clif_rot
        elif np.allclose(mat, clif_mat_i):
            return clif_rot
        elif np.allclose(mat, -1 * clif_mat):
            return clif_rot
        elif np.allclose(mat, -1 * clif_mat_i):
            return clif_rot
    raise Exception('Could not find inversion for mat {}'.format(mat))


def make_benchmarking_sequence(
        length, num_of_sequences, SSBfreq=None, drag=False,
        channels=[1, 2, 3, 4], spacing=None, gaussian=True):
    gate_lists = []
    for n in range(num_of_sequences):
        gate_list = make_random_gate_list(length)
        mat = gates_to_mat(gate_list)
        inverting_mat = invert_mat(mat)
        inverting_gates = mat_to_gates(inverting_mat)
        gate_list.extend(inverting_gates)
        gate_lists.append(gate_list)
    seq = make_sequence_from_gate_lists(
        gate_lists, SSBfreq=SSBfreq, drag=drag, gaussian=gaussian,
        variable_label=None, spacing=spacing,
        name='benchmarking_length_{}'.format(length))
    seq.labels = {'seq_type': 'benchmarking', 'pulse_mod': False}
    return seq


# def decompose_mat_into_gates(mat):
#     a = mat[0, 0]
#     b = mat[0, 1]
#     c = mat[1, 0]
#     d = mat[1, 1]
#     a0 = (a + d) / 2
#     a1 = (b + c) / 2
#     a2 = (c - b) / (2 * 1j)
#     a3 = (a - d) / 2
#     theta = 2 * np.arccos(np.absolte(a0))
#     alpha = np.phase(a0 / np.cos(theta / 2))
#     nx = a1 / (-1j * np.exp(1j * alpha) * np.sin(theta / 2))
#     ny = a2 / (-1j * np.exp(1j * alpha) * np.sin(theta / 2))
#     nz = a3 / (-1j * np.exp(1j * alpha) * np.sin(theta / 2))
#     return theta, alpha, nx, ny, nz
