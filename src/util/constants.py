"""
Constants applicable to running integration tests against local nodes.
"""


# These must match constants from the commands/bin/env.sh file for localnet node 0 and 1.
LOCALNET0_CHAOS_RPC = 26670
LOCALNET0_NDAU_RPC  = 26671
LOCALNET1_CHAOS_RPC = 26672
LOCALNET1_NDAU_RPC  = 26673

# The identity that the chaos tool uses to map to the system namespace for gets and sets.
SYSVAR_IDENTITY = 'sysvar'

# Sysvar keys.
EAI_FEE_TABLE_KEY          = 'EAIFeeTable'
TRANSACTION_FEE_SCRIPT_KEY = 'TransactionFeeScript'

# For use when changing tx fees throughout the integration tests.
ZERO_FEE_SCRIPT            = '"oAAgiA=="'
ONE_NAPU_FEE_SCRIPT        = '"oAAaiA=="'
ONE_NAPU_FEE               = 1

# These must match the genesis files.  Localnet, devnet and testnet all use the same values.
RFE_ADDRESS = 'ndmfgnz9qby6nyi35aadjt9nasjqxqyd4vrswucwfmceqs3y'
RFE_KEY = 'npvtayjadtcbictc27a55zyz66yb53ygn4cc9qgxm3m2x3wmnhfyrwkwipwupxeijsmazxir586bfpeuqncud6z72veb3zn5kd62myri589uit6ta4kas5def9ii'
NNR_ADDRESS = 'ndnf9ffbzhyf8mk7z5vvqc4quzz5i2exp5zgsmhyhc9cuwr4'
NNR_KEY = 'npvtayjadtcbiavi5k4g6jxwmnpt5cky7xpbkhsrt5ev757wssnb8u3d5wyw38ykgz2v4uwhug954qq6wv38jkrwdpp2pndia4hqif72ezv4wcinaiyhaiaapzaj'
CVC_ADDRESS = 'ndnf9ffbzhyf8mk7z5vvqc4quzz5i2exp5zgsmhyhc9cuwr4'
CVC_KEY = 'npvtayjadtcbiavi5k4g6jxwmnpt5cky7xpbkhsrt5ev757wssnb8u3d5wyw38ykgz2v4uwhug954qq6wv38jkrwdpp2pndia4hqif72ezv4wcinaiyhaiaapzaj'
