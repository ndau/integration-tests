"""
Constants applicable to running integration tests against local nodes.
"""


# These must match constants from the commands/bin/env.sh file for localnet node 0 and 1.
LOCALNET0_CHAOS_RPC = 26670
LOCALNET0_NDAU_RPC  = 26671
LOCALNET1_CHAOS_RPC = 26672
LOCALNET1_NDAU_RPC  = 26673

# These must match the genesis files.  All networks use (nearly) the same genesis files.
# Some of these we could conceivably get using ndau/chaos tool commands, but some are not exposed.
SYSTEM_NAMESPACE = 'OHCPYCsIi3VtEKrLsrqGdcglqlvNci3bbrYVr/09sWc='
RFE_ADDRESS = 'ndmfgnz9qby6nyi35aadjt9nasjqxqyd4vrswucwfmceqs3y'
RFE_KEY = 'npvtayjadtcbictc27a55zyz66yb53ygn4cc9qgxm3m2x3wmnhfyrwkwipwupxeijsmazxir586bfpeuqncud6z72veb3zn5kd62myri589uit6ta4kas5def9ii'
NNR_ADDRESS = 'ndnf9ffbzhyf8mk7z5vvqc4quzz5i2exp5zgsmhyhc9cuwr4'
NNR_KEY = 'npvtayjadtcbiavi5k4g6jxwmnpt5cky7xpbkhsrt5ev757wssnb8u3d5wyw38ykgz2v4uwhug954qq6wv38jkrwdpp2pndia4hqif72ezv4wcinaiyhaiaapzaj'
CVC_ADDRESS = 'ndnf9ffbzhyf8mk7z5vvqc4quzz5i2exp5zgsmhyhc9cuwr4'
CVC_KEY = 'npvtayjadtcbiavi5k4g6jxwmnpt5cky7xpbkhsrt5ev757wssnb8u3d5wyw38ykgz2v4uwhug954qq6wv38jkrwdpp2pndia4hqif72ezv4wcinaiyhaiaapzaj'
EAI_FEE_TABLE = [
    '4000000:ndaea8w9gz84ncxrytepzxgkg9ymi4k7c9p427i6b57xw3r4',
    '1000000:ndmmw2cwhhgcgk9edp5tiieqab3pq7uxdic2wabzx49twwxh',
    '100000:ndbmgby86qw9bds9f8wrzut5zrbxuehum5kvgz9sns9hgknh',
    '100000:ndnf9ffbzhyf8mk7z5vvqc4quzz5i2exp5zgsmhyhc9cuwr4',
    '9800000:',
]
