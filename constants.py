CHANNELS_CSV = 'channels.csv'
NODES_CSV = 'nodes.csv'
FAULTY_PCT = 0.05 # nodes that fail/grief in the first round; payment is successful
FAULTY2_PCT = 0.05 # nodes that fail/grief in the second round; payment is unsuccessful 
PAY_PCT = 0.5
#average channel capacity of the provided snapshot is 3288455
PAY_MIN = 1000
PAY_MAX = 3000000
NUM_ROUNDS = 100
DELAY_ROUNDS = 1
CONSTANT = 0
LINEAR = 1
BASELINE = 2
CLB = [CONSTANT, LINEAR, BASELINE]
###### COLUMN NAMES ######
NODE_A = 'nodeA'
NODE_B = 'nodeB'
SATOSHIS = 'satoshis'
BF = 'base_fee'
FR = 'relative_fee'
###### PAYMENT OUTCOMES ######
SUCCESS = 0
FAIL1 = 1 # Fail in round 2
FAIL2 = 2 # Fail in round 1
INSUF_BAL = 3