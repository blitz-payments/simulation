import numpy as np
import pandas as pd
CHANNELS_CSV_IN = 'channels_pubkey.csv'
CHANNELS_CSV_OUT = 'channels.csv'
NODES_CSV = 'nodes.csv'

def main():
    channels = pd.read_csv(CHANNELS_CSV_IN)
    nodes = pd.read_csv(NODES_CSV)
    nodes['nid'] = np.arange(len(nodes))
    for i in range(0,len(channels)):
        pkA = channels['nodeA'][i]
        pkB = channels['nodeB'][i]
        indexA = nodes.loc[nodes['pubkey']== pkA]['nid'].values[0]
        indexB = nodes.loc[nodes['pubkey']== pkB]['nid'].values[0]
        channels.iat[i,2] = indexA # nodeA is in column 2
        channels.iat[i,3] = indexB # nodeB is in column 3
    print(channels)
    channels.to_csv(CHANNELS_CSV_OUT, columns=['satoshis','nodeA','nodeB','base_fee_millisatoshi','fee_per_millionth','update_time'])

if __name__ == "__main__":
    main()
