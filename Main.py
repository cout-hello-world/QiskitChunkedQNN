import argparse
import math

import qiskit

import Qconfig


time_chunks = 4
time_interval = 1.580 / (8.0 * math.pi)

def get_weights():
    tunneling_a = [2.4886, 2.4730, 2.4852, 2.4949]
    tunneling_b = [2.4886, 2.4730, 2.4852, 2.4949]
    bias_a = [0.092889, 0.11577, 0.095443, 0.083292]
    bias_b = [0.092889, 0.11577, 0.095443, 0.083292]
    coupling = [0.03820, 0.12759, 0.11692, 0.038180]

    weights = [[0.0 for x in range(5)] for y in range(time_chunks)]
    for i in range(0, time_chunks):
        time_scale = time_chunks * time_interval * math.pi
        normal_factor_a = math.sqrt(math.pow(tunneling_a[i], 2) + math.pow(bias_b[i], 2))
        normal_factor_b = math.sqrt(math.pow(tunneling_b[i], 2) + math.pow(bias_b[i], 2))

        weights[i][0] = time_scale * coupling[i]
        weights[i][1] = math.asin(tunneling_a[i] / normal_factor_a)
        weights[i][2] = math.asin(tunneling_b[i] / normal_factor_b)
        weights[i][3] = time_scale * normal_factor_a
        weights[i][4] = time_scale * normal_factor_b

    return weights

def generate_circuit(begin_state, weights):
    q = qiskit.QuantumRegister(2)
    c = qiskit.ClassicalRegister(2)
    qc = qiskit.QuantumCircuit(q, c)
    if begin_state == 0:
        # Bell state
        qc.h(q[0])
        qc.cx(q[0], q[1])
    elif begin_state == 1:
        # Flat state
        qc.h(q[0])
        qc.h(q[1])
    elif begin_state == 2:
        # C state
        qc.x(q[0])
        qc.ry(2.0 * math.acos(1.0 / math.sqrt(5.0)), q[1])
    elif begin_state == 3:
        # P state
        raise Exception("NYI")

    for j in range(0, time_chunks):
        qc.cx(q[0], q[1])
        qc.rz(weights[j][0], q[1])
        qc.cx(q[0], q[1])

        qc.ry(-weights[j][1], q[0])
        qc.ry(-weights[j][2], q[1])

        qc.rz(weights[j][3], q[0])
        qc.rz(weights[j][4], q[1])

        qc.ry(weights[j][1], q[0])
        qc.ry(weights[j][2], q[1])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-test', help='run on real hardware',
                        action='store_true')
    args = parser.parse_args()

    if args.no_test:
        test = False
    else:
        test = True

    params = {'local': test, 'simulator': test}
    if not test:
        qiskit.register(Qconfig.APItoken, Qconfig.config['url'])
    backend = qiskit.least_busy(qiskit.available_backends(params))
    print('backend:', backend)

    weights = get_weights()
    qc = generate_circuit(0, weights)
