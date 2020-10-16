import networkx as nx
import random
from networkx.algorithms import shortest_path
from networkx.algorithms.shortest_paths.generic import has_path
import constants as cons
import pandas as pd
import sys
import json
from typing import List
from joblib import Parallel, delayed
from tqdm import tqdm
from datetime import datetime


def create_payments(graph, num_paths):
    num_channels = len(graph.edges)
    # num_nodes = len(graph.nodes)
    # select random payments
    senders = random.choices(list(graph), k=num_paths)
    receivers = random.choices(list(graph), k=num_paths)
    # amounts = [random.randrange(cons.PAY_MIN,cons.PAY_MAX) for i in range(0,len(senders))]
    # paths = [None] * num_paths
    paths = Parallel(n_jobs=8)(
        delayed(get_path)(graph, senders[i], receivers[i])
        for i in tqdm(range(0, len(senders)))
    )
    #for i in tqdm(range(0,len(senders))):
    #    paths[i] = get_path(graph, senders[i], receivers[i])
    #path = nx.dijkstra_path(graph, source=senders[0], target=receivers[0], weight=weight_fun)
    return paths

def get_path(graph, sender, receiver) -> List[int]:
    while not (receiver != sender and has_path(graph, source=sender, target=receiver)):
        if receiver == sender:
            receiver = random.choice(list(graph))
        if not has_path(graph, source=sender, target=receiver):
            sender = random.choice(list(graph))
            receiver = random.choice(list(graph))
    return shortest_path(graph, source=sender, target=receiver, weight='base_fee')

def weight_fun(u,v,d):
    return d['base_fee'] + d['relative_fee'] * (cons.PAY_MIN+cons.PAY_MAX/2)

def main():
    """
    Use this to generate random payment paths in the given PCN dump located in cons.CHANNELS_CSV.
    If no (integer) argument is given, creates 100000 payments and stores them in pathsRand.json.
    For random.seed(1), 100000 paths are stored in paths.json.
    """
    num_paths = 600000
    if len(sys.argv) > 1:
        num_paths = int(sys.argv[1])
    channels = pd.read_csv(cons.CHANNELS_CSV)
    # generate graph
    graph = nx.from_pandas_edgelist(channels,'nodeA','nodeB',['satoshis','base_fee','relative_fee'])
    paths = create_payments(graph, num_paths)
    with open(f'pathsRand-{datetime.now().strftime("%d-%m-%Y_%H-%M-%S")}.json', 'w') as f:
        f.write(json.dumps(paths))


if __name__ == "__main__":
    main()
