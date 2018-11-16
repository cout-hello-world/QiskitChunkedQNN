#!/usr/bin/env python3
import argparse
import math
import time
import csv
import sys

import qiskit
import qiskit.backends.ibmq as ibmq
from qiskit.backends.jobstatus import JobStatus
from qiskit import IBMQ, Aer

qx_url = 'https://quantumexperience.ng.bluemix.net/api'

time_chunks = 4

def get_weights(noise=False, decoherence=False):
    time_interval = 1.580 / (8.0 * math.pi)
    if not noise and not decoherence:
        tunneling_a = [2.4886, 2.4730, 2.4852, 2.4949]
        tunneling_b = [2.4886, 2.4730, 2.4852, 2.4949]
        bias_a = [0.092889, 0.11577, 0.095443, 0.083292]
        bias_b = [0.092889, 0.11577, 0.095443, 0.083292]
        coupling = [0.03820, 0.12759, 0.11692, 0.038180]
    elif not noise and decoherence:
        tunneling_a = [2.2659839774063, 2.35693757391734, 2.53169447569211, 2.76968791602036]
        tunneling_b = [2.27906181795579, 2.37066713524698, 2.55043045448358, 2.79886639941257]
        bias_a = [0.096030498257791, 0.12198502658194, 0.091295987621283, 0.046825320333615]
        bias_b = [0.09495851100657, 0.123706597274963, 0.091733070147231, 0.047366327441214]
        coupling = [0.0650289956994, 0.114261449042702, 0.110980332537371, 0.067624857565807]
    elif noise and not decoherence:
        tunneling_a = [1.84855122259435, 3.44850982618433, 3.46420436257955, 0.675914471058636]
        tunneling_b = [2.047355773728, 3.5919549082169, 3.70939783548255, 1.08055210178105]
        bias_a = [0.067040715210162, 0.150436749829005, 0.111915721202186, 0.087130534547371]
        bias_b = [0.01959892037637, 0.167558036292694, 0.11151189326291, 0.065784621542093]
        coupling = [0.017689035038624, 0.142287609964454, 0.127910134864668, 0.016442994853455]
    elif noise and decoherence:
        tunneling_a = [1.8522947273507, 3.54218806945153, 3.36289364455586, 0.682010111436336]
        tunneling_b = [2.04041622838001, 3.66507780707179, 3.59752800505758, 1.12687688355898]
        bias_a = [0.081934919522767, 0.127162576694709, 0.0792340439726, 0.038734867039432]
        bias_b = [0.051739078875095, 0.149134634167826, 0.083249923691573, 0.007052541979843]
        coupling = [0.016661336670829, 0.136061520564601, 0.130071100478697, 0.013526207733738]

    weights = [[0.0 for x in range(5)] for y in range(time_chunks)]
    for i in range(0, time_chunks):
        time_scale = time_chunks * time_interval * math.pi
        normal_factor_a = math.sqrt(math.pow(tunneling_a[i], 2) +
          math.pow(bias_a[i], 2))
        normal_factor_b = math.sqrt(math.pow(tunneling_b[i], 2) +
          math.pow(bias_b[i], 2))

        weights[i][0] = time_scale * coupling[i]
        weights[i][1] = math.asin(tunneling_a[i] / normal_factor_a)
        weights[i][2] = math.asin(tunneling_b[i] / normal_factor_b)
        weights[i][3] = time_scale * normal_factor_a
        weights[i][4] = time_scale * normal_factor_b

    return weights

def generate_circuit(begin_state, weights, setup_only=False):
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
        qc.cu3(parameters[1], 0, 0, q[0], q[1])
        qc.ry(-parameters[1], q[1])

        qc.swap(q[0], q[1])
        qc.cu3(-parameters[2], 0, 0, q[0], q[1])
        qc.ry(parameters[2], q[1])

    if not setup_only:
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
    max_runs_per_api_call = 8000
    return_val = [0, 0, 0, 0]
    while runs > 0:
        if runs <= max_runs_per_api_call:
            sh = runs
            runs = 0
        else:
            sh = max_runs_per_api_call
            runs -= max_runs_per_api_call
        job = qiskit.execute(qc, backend, shots=sh)
        res = job.result()
        idx = 0
        for bits in ['00', '10', '01', '11']:
            res_count = res.get_counts().get(bits)
            if res_count != None:
                return_val[idx] += res_count
            idx += 1

    return return_val

def run_epoch(backend, circuits, count):
    results = {'Bell': [], 'Flat': [], 'C': [], 'P': []}
    idx = 0
    for state in ['Bell', 'Flat', 'C', 'P']:
        results[state] = execute(circuits[idx], backend, count)
        idx += 1

    return results

if __name__ == '__main__':
    default_count = 1000
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-test', help='run on real hardware',
                        action='store_true')
    parser.add_argument('--delta',
      help=('change in runs between epochs (default ' +
        str(default_count) + ')'), default=default_count)
    parser.add_argument('--end',
      help='number times delta to end with (default 1)',
      default=1)
    default_out_file = 'out.csv'
    parser.add_argument('--filename',
      help='name of output file (default ' + default_out_file + ')',
      default=default_out_file)
    parser.add_argument('--start',
      help='number of times delta to start with (default 1)',
      default=1)
    parser.add_argument('--setup-only',
      help="Only set up states. (Don't run chunks)", action='store_true')
    parser.add_argument('--list-backends', help="Only list backends",
      action='store_true')
    parser.add_argument('--backend', help='Use this backend')
    default_api_token_path = 'APItoken.txt'
    parser.add_argument('--token-file',
      help=('Path to file containing API token (default ' +
        default_api_token_path + ')'), default=default_api_token_path)
    parser.add_argument('--noise', help='Use weights trained with noise',
      action='store_true')
    parser.add_argument('--decoherence', help='Use wieghts trained with decoherence',
      action='store_true')

    args = parser.parse_args()
    if args.noise:
        noise = True
    else:
        noise = False
    if args.decoherence:
        decoherence = True
    else:
        decoherence = False
    if args.no_test:
        test = False
    else:
        test = True
    api_token_path = args.token_file
    delta = int(args.delta)
    end = int(args.end)
    start = int(args.start)
    filename = args.filename
    if args.setup_only:
        setup_only = True
    else:
        setup_only = False
    if args.list_backends:
        list_backends = True
    else:
        list_backends = False
    backend_name = args.backend
    if (not backend_name) and (not list_backends):
        print('Must pass one of --backend or --list-backends')
        sys.exit(1)


    if not test:
        with open(api_token_path, 'r') as f:
            APItoken = f.readlines()[0].rstrip('\n')
        IBMQ.enable_account(APItoken, qx_url)

    if list_backends:
        if test:
            backends = Aer.backends()
        else:
            backends = IBMQ.backends()
        for b in backends:
            print(b)
        sys.exit(0)

    if test:
        backend = Aer.get_backend(backend_name)
    else:
        backend = IBMQ.get_backend(backend_name)


    weights = get_weights(noise=noise, decoherence=decoherence)
    circuits = [generate_circuit(n, weights, setup_only=setup_only)
                for n in range(0, 4)]

    with open(filename, 'w', newline='', buffering=1) as outfile:
        fields = ['backend', 'noise', 'decoherence', 'shots', 'state', '00', '10', '01', '11']
        writer = csv.writer(outfile)
        writer.writerow(fields)
        for count in range(delta * start, (end + 1) * delta, delta):
            eres = run_epoch(backend, circuits, count)
            for state in ['Bell', 'Flat', 'C', 'P']:
                writer.writerow([backend, int(noise), int(decoherence),
                  count, state, eres[state][0],
                  eres[state][1], eres[state][2], eres[state][3]])
