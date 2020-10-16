import numpy as np
import pandas as pd
import random
import json
import constants as cons
from pcn import PCN
from datetime import datetime
from itertools import product

random.seed(0)


def main():
    max_value = [int(cons.PAY_MAX / 1000), int(cons.PAY_MAX / 500), int(cons.PAY_MAX * 3 / 1000)]
    faulty_pct_of_payments = [0.005, 0.01, 0.025]
    rounds = [3]
    base = 0
    payment_per_node_and_round = [4, 50]

    out = 'max,base,f1,f2,ppr,it,wormhole,suc0,unsuc0,suc1,unsuc1,suc2,unsuc2,pct'

    paths = []
    with open(f'paths-1.4M.json', 'r') as f:
        paths = paths + json.loads(f.read())
    # paths = list(filter(None, paths))
    channels = pd.read_csv(cons.CHANNELS_CSV)

    for i in range(0, 8):
        out += iterate(max_value, paths, faulty_pct_of_payments, rounds, payment_per_node_and_round, channels, base, i)

    with open(f'exp-{datetime.now().strftime("%d-%m-%Y_%H-%M-%S")}.csv', 'w') as file:
        file.write(out)


def iterate(max_value, paths, faulty_pct_of_payments, rounds, payment_per_node_and_round, channels, base, it):
    out = ''
    for mx in max_value:
        amounts = [random.randrange(cons.PAY_MIN, mx) for i in range(0, len(paths))]
        payments = [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]]
        for f, cr, ppr, clb in product(faulty_pct_of_payments, rounds, payment_per_node_and_round, cons.CLB):
            # random node on path malicious:
            malicious = [random.randrange(1, len(paths[i])) for i in range(0, len(paths))]
            # last node on path malicious:
            # malicious = [len(paths[i]) - 1 for i in range(0, len(paths))]
            linear_collateral = min(1, clb)
            pcn = PCN(channels, linear_collateral)
            num_payments_per_round = int(len(pcn.graph) * ppr)
            f1 = base + int(f / 2 * cr * ppr * len(pcn.graph))
            f2 = base + int(f / 2 * cr * ppr * len(pcn.graph))
            payments[clb] = [0, 0, 0, 0]
            wormhole_fees = 0
            if clb < cons.BASELINE:
                for i in range(0, f1):
                    pay_status = pcn.pay_malicious(paths[i], amounts[i], malicious[i], fault_type=cons.FAIL1)
                    payments[clb][pay_status] += 1
                for i in range(f1, f1 + f2):
                    pay_status = pcn.pay_malicious(paths[i], amounts[i], malicious[i], fault_type=cons.FAIL2)
                    payments[clb][pay_status] += 1
            for r in range(0, cr):

                for i in range(f1 + f2 + r * num_payments_per_round,
                               f1 + f2 + (r + 1) * num_payments_per_round):
                    pay_status = pcn.pay(paths[i], amounts[i])
                    payments[clb][pay_status] += 1
                    wormhole_fees += pcn.get_wormhole_potential(paths[i], amounts[i])
                pcn.set_round(r + 1)
            if clb == 2:
                s0 = payments[cons.CONSTANT][cons.SUCCESS]
                u0 = payments[cons.CONSTANT][cons.INSUF_BAL]
                s1 = payments[cons.LINEAR][cons.SUCCESS]
                u1 = payments[cons.LINEAR][cons.INSUF_BAL]
                s2 = payments[cons.BASELINE][cons.SUCCESS]
                u2 = payments[cons.BASELINE][cons.INSUF_BAL]
                pct = u0 / u1
                v = f'\n{mx},{base},{f / 2},{f / 2},{ppr},{it},{wormhole_fees},{s0},{u0},{s1},{u1},{s2},{u2},{pct}'
                out += v
                print(out)
    return out


if __name__ == "__main__":
    main()
