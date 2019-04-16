"""
Constants applicable to running integration tests against local nodes.
"""


# These must match constants from the commands/bin/env.sh file for localnet node 0 and 1.
LOCALNET0_RPC = 26670
LOCALNET1_RPC = 26671

# Sysvar keys.
ACCOUNT_ATTRIBUTES_KEY = "AccountAttributes"
EAI_FEE_TABLE_KEY = "EAIFeeTable"
TRANSACTION_FEE_SCRIPT_KEY = "TransactionFeeScript"

# For use when changing tx fees throughout the integration tests.
ZERO_FEE_SCRIPT = '"oAAgiA=="'
ONE_NAPU_FEE_SCRIPT = '"oAAaiA=="'
ONE_NAPU_FEE = 1

# defaults used by netconf
# overriden by environment variables: "NODE_ADDRESS", "NODE_0_RPC", "NODE_1_RPC"
DEFAULT_REMOTE_ADDRESS = "https://api.ndau.tech"
DEFAULT_REMOTE_RPC_PORT_0 = "30100"
DEFAULT_REMOTE_RPC_PORT_1 = "30101"
