import multiprocessing
from functools import partial
from itertools import combinations
import pickle
import os.path


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


pool = None
testing = False
precalced_weights = []
current_weights = None


def testing():
    global M, S
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


def D(S, i=None):
    """Distance function"""
    if i is None:
        weights = list(pool.imap(partial(D_, S), range(len(M))))
        precalced_weights.append((S, weights))
        return weights
    else:
        D_(S, i)


def D_(S, i):
    if not current_weights:
        mindist = sum([1 for a in bin(M[i]) if a == '1'])
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
    w = [sum([1 for a in bin(m) if a == '1']) - 1 for m in M]
    precalced_weights.append((S.copy(), w))
    return w


def find_next_base(minsum):
    options = []
    for (rowa, rowb) in combinations(S, 2):
        newrow = rowa ^ rowb
        if newrow in S or newrow in map(lambda x: x[0], options):
            continue
        if newrow in M:
            return newrow

        option = S + [newrow]
        weights = D(option)
        weightsum = sum(weights)
        if weightsum < minsum:
            minsum = weightsum
            options = [(newrow, weights)]
        elif weightsum == minsum:
            options.append((newrow, weights))

    if len(options) == 1:
        return options[0][0]
    else:
        print("Tie! Available options: {}".format(list(map(lambda x: bin(x[0]),
                                                           options))))
        return max(options, key=lambda k: norm(k[1]))[0]


def save_state(filename):
    with open(filename, 'wb') as f:
        pickle.dump((S, precalced_weights), f)


def load_state(filename):
    global S, precalced_weights
    if not os.path.exists(filename):
        return
    with open(filename, 'rb') as f:
        S, precalced_weights = pickle.load(f)


if __name__ == "__main__":
    import sys

    filename = "state.pickle"

    if len(sys.argv) == 2:
        print("Testing mode!")
        filename = "testing.pickle"
        testing()

    pool = multiprocessing.Pool()

    load_state(filename)
    if not precalced_weights:
        hamming_weight_distances()

    current_weights = D(S)
    save_state(filename)
    while not sum(current_weights) == 0:
        print("Weights: {}".format(current_weights))
        print("S:\n{}".format(list(map(bin, S))))
        print("Calculating next S…")
        newbase = find_next_base(sum(current_weights))
        print("Found new base {}".format(bin(newbase)))
        S += [newbase]
        save_state(filename)
        current_weights = D(S)

    print("Final S:")
    print(list(map(bin, S)))
