import argparse

import qiskit

import Qconfig


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
