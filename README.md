# Blitz simulation

A simulation to showcase the advantages of Blitz over Lightning payments.
Specifically, the reduced (staggered to consant) collateral and wormhole resistance.

## Usage:

- Install Python >= 3.7.3
- Install dependencies (check requirements.txt)
-----------------------------------------------
- OPTIONAL STEPS:
- Use either the provided LN dump by extracting lnchannels.zip to lnchannels.dump, or download a fresh dump from https://ln.bigsun.xyz/
- Use query_channels.sql and query_nodes.sql to select the important data of the dump
- Use convert.py to change the columns to correct format and change the pubkey identifier to a numeric id and save to channel.csv and nodes.csv
- Use payments.py to create random payment paths in the graph described by the two aforementioned csv files
- Change the experiment parameters in main.py
-----------------------------------------------
- Execute main.py to carry out a simulation using the provided parameters
- The results are saved to exp-DD-MM-YYYY_HH-MM-SS.csv
- Inspect results.csv to view our pre-computed results for the given parameters and random seed