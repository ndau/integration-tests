#  ----- ---- --- -- -
#  Copyright 2020 The Axiom Foundation. All Rights Reserved.
# 
#  Licensed under the Apache License 2.0 (the "License").  You may not use
#  this file except in compliance with the License.  You can obtain a copy
#  in the file LICENSE in the source distribution or at
#  https://www.apache.org/licenses/LICENSE-2.0.txt
#  - -- --- ---- -----

"""
Constants applicable to running integration tests against local nodes.
"""


# These must match constants from the commands/bin/env.sh file for localnet node 0 and 1.
LOCALNET0_RPC = 26670
LOCALNET0_NDAUAPI = 3030
LOCALNET0_MONIKER = "localnet-0"

# Sysvar keys.
ACCOUNT_ATTRIBUTES_KEY = "AccountAttributes"
EAI_FEE_TABLE_KEY = "EAIFeeTable"
TRANSACTION_FEE_SCRIPT_KEY = "TransactionFeeScript"

# For use when changing tx fees throughout the integration tests.
ZERO_FEE_SCRIPT = '"oAAgiA=="'
ONE_NAPU_FEE_SCRIPT = '"oAAaiA=="'
ONE_NAPU_FEE = 1
