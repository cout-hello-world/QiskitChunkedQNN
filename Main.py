#!/usr/bin/env python3
import argparse
import math
import time
import csv

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
        parameters = [4.511031, 2.300524, 5.355890]
        qc.cu3(parameters[0], 0, 0, q[0], q[1]) # cu3 for controlled ry
        qc.ry(-parameters[0], q[1])

        qc.swap(q[0], q[1])
        qc.cu3(-parameters[1], 0, 0, q[0], q[1])
        qc.ry(parameters[1], q[1])

        qc.swap(q[0], q[1])
        qc.cu3(-parameters[2], 0, 0, q[0], q[1])
        qc.ry(parameters[2], q[1])

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

    qc.measure(q, c)
    return qc

def execute(qc, backend, runs):
    job = qiskit.execute(qc, backend=backend, shots=runs)
    while not job.done:
        time.sleep(10)
    return job.result()

def run_epoch(backcend, circuits, count):
    results = {'Bell': [], 'Flat': [], 'C': [], 'P': []}
    for n in range(0, 4):
        if n == 0:
            res = results['Bell']
        elif n == 1:
            res = results['Flat']
        elif n == 2:
            res = results['C']
        elif n == 3:
            res = results['P']
        result = execute(circuits[n], backend, count)
        for bits in ['00', '01', '10', '11']:
            res_count = result.get_counts().get(bits)
            if res_count == None:
                res.append(0)
            else:
                res.append(res_count)
    return results

if __name__ == '__main__':
    default_count = 1000
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-test', help='run on real hardware',
                        action='store_true')
    parser.add_argument('--delta',
      help=('change in runs between epochs (default ' + str(default_count) + ')'),
      default=default_count)
    parser.add_argument('--epochs',
      help='number of epochs in increments of delta runs (default 1)',
      default=1)
    parser.add_argument('--filename',
      help='name of output file',
      default='out.csv')
    args = parser.parse_args()
    if args.no_test:
        test = False
    else:
        test = True
    delta = int(args.delta)
    epochs = int(args.epochs)
    filename = args.filename

    params = {'local': test, 'simulator': test}
    if not test:
        qiskit.register(Qconfig.APItoken, Qconfig.config['url'])
    backend = qiskit.least_busy(qiskit.available_backends(params))

    weights = get_weights()
    circuits = [generate_circuit(n, weights) for n in range(0, 4)]

    with open(filename, 'w', newline='') as outfile:
        fields = ['backend', 'shots', 'state', '00', '01', '10', '11']
        writer = csv.writer(outfile)
        writer.writerow(fields)
        for count in range(delta, (epochs + 1) * delta, delta):
            eres = run_epoch(backend, circuits, count)
            for state in ['Bell', 'Flat', 'C', 'P']:
                writer.writerow([backend, count, state, eres[state][0],
                                eres[state][1], eres[state][2], eres[state][3]])
