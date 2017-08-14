# Copyright (C) 2015  Thom Wiggers <thom@thomwiggers.nl>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import multiprocessing
from functools import partial
from itertools import combinations
import pickle
import os.path
import logging

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
fh = logging.FileHandler('heuristic.log')
fh.setLevel(logging.INFO)
fh.setFormatter(formatter)
ch = logging.StreamHandler()
ch.setFormatter(formatter)
ch.setLevel(logging.DEBUG)

logger.addHandler(ch)
logger.addHandler(fh)

M = [0b1000100100101011,
     0b0100100000011001,
     0b0010010011001000,
     0b0001001001100100,
     0b1001100010110010,
     0b1000010010010001,
     0b0100001010001100,
     0b0010000101000110,
     0b0010101110001001,
     0b0001100101001000,
     0b1100100000100100,
     0b0110010000010010,
     0b1011001010011000,
     0b1001000110000100,
     0b1000110001000010,
     0b0100011000100001]

S = [0b1000000000000000,
     0b0100000000000000,
     0b0010000000000000,
     0b0001000000000000,
     0b0000100000000000,
     0b0000010000000000,
     0b0000001000000000,
     0b0000000100000000,
     0b0000000010000000,
     0b0000000001000000,
     0b0000000000100000,
     0b0000000000010000,
     0b0000000000001000,
     0b0000000000000100,
     0b0000000000000010,
     0b0000000000000001]

program = [('x{}'.format(i), '') for i in range(S[0].bit_length())]


pool = None
testing = False
precalced_weights = []
current_weights = None


def testing():
    global M, S, program
    M = [0b11100,
         0b01011,
         0b10111,
         0b01110,
         0b11010,
         0b01111]

    S = [0b10000,
         0b01000,
         0b00100,
         0b00010,
         0b00001]

    program = [('x{}'.format(i), '') for i in range(S[0].bit_length())]


def D(S, i=None):
    """Distance function"""
    if i is None:
        weights = list(map(partial(D_, S), range(len(M))))
        precalced_weights.append((S.copy(), weights))
        logger.debug("Found weight %s for S: %s", weights, S)
        return weights
    else:
        D_(S, i)


def D_(S, i):
    if not current_weights:
        mindist = bin(M[i]).count('1')
    else:
        mindist = current_weights[i]

    def d(s, distance):
        nonlocal mindist

        if distance > mindist:
            return 100
        else:
            candidates = []
            for row in s:
                candidate = [row ^ a for a in S]
                if M[i] in candidate:
                    if distance < mindist:
                        logger.debug(
                            "Updating mindist for M[%d] with S=%s to %d",
                            i, S, distance)
                        mindist = distance
                    return distance
                candidates.append(candidate)
            return min(map(lambda c: d(c, distance+1), candidates))

    if M[i] in S:
        return 0
    for (s, w) in precalced_weights:
        if s == S:
            return w[i]
    else:
        return d(S, 1)


def norm(weights):
    return sum(map(lambda x: x**2, weights))


def hamming_weight_distances():
    w = [bin(m).count('1') - 1 for m in M]
    precalced_weights.append((S.copy(), w))
    return w


def evaluate_row(S, newrow):
    option = S + [newrow[0]]
    weights = D(option)
    return (newrow, weights)


def find_next_base(minsum):
    rows = set()
    for (rowai, rowbi) in combinations(range(len(S)), 2):
        newrow = S[rowai] ^ S[rowbi]
        if newrow in S:
            continue
        elif newrow in M:
            logging.info("Short-circuited because we found a result: %s",
                         newrow)
            program.append(('y{}'.format(M.index(newrow)), '{} ^ {}'.format(program[rowai][0], program[rowbi][0])))
            return newrow
        else:
            rows.add((newrow, rowai, rowbi))

    results = pool.map(partial(evaluate_row, S), rows)
    logger.debug("find_next_base inbetween results: {}".format(results))

    options = []
    for newrow, weights in results:
        weightsum = sum(weights)
        if weightsum < minsum:
            minsum = weightsum
            options = [(newrow, weights)]
        elif weightsum == minsum:
            options.append((newrow, weights))

    if len(options) == 1:
        program.append(('t{}'.format(len(program)), '{} ^ {}'.format(program[options[0][0][1]][0], program[options[0][0][2]][0])))
        return options[0][0][0]
    else:
        logger.debug("Tie! Available options: {}".format(
            list(map(lambda x: bin(x[0][0]), options))))
        maxvalue = max(options, key=lambda k: norm(k[1]))[0]
        program.append(('t{}'.format(len(program)), '{} ^ {}'.format(program[maxvalue[1]][0], program[maxvalue[2]][0])))
        return maxvalue[0]


def save_state(filename):
    with open(filename, 'wb') as f:
        pickle.dump((S, precalced_weights, program), f)


def load_state(filename):
    global S, precalced_weights, program
    if not os.path.exists(filename):
        return
    with open(filename, 'rb') as f:
        S, precalced_weights, program = pickle.load(f)



if __name__ == "__main__":
    import sys

    filename = "state.pickle"

    if len(sys.argv) == 2:
        logger.info("Testing mode!")
        filename = "testing.pickle"
        testing()

    pool = multiprocessing.Pool()

    load_state(filename)
    if not precalced_weights:
        hamming_weight_distances()

    current_weights = D(S)
    save_state(filename)
    while not sum(current_weights) == 0:
        logger.info("Weights: {}".format(current_weights))
        logger.info("S: {}".format(list(map(bin, S))))
        print("Calculating next S…")
        newbase = find_next_base(sum(current_weights))
        logger.info("Found new base {}".format(bin(newbase)))
        S += [newbase]
        save_state(filename)
        current_weights = D(S)

    print("Final S:")
    print(list(map(bin, S)))
    print('As program:')
    for result, computation in program[S[0].bit_length():]:
        print(result, '=', computation)
