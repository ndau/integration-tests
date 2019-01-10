"""
Test:
- Pre-genesis RFE
- Genesis CreditEAI
- Changing tx fees post-genesis
"""

import base64
import json
import os.path
import pytest
import toml
import src.util.constants
import src.util.helpers


class Account:
    def __init__(self, act, flg, pct, bal):
        self.account = act # Account name or address.
        self.flag    = flg # Flag to use with account string with ndau account query commands.
        self.percent = pct # EAI fee percent this account receives from CreditEAI.
        self.balance = bal # Initial balance of the account before CreditEAI.


def test_pre_genesis_rfe(ndau, chaos, set_rfe_address, ndau_node_exists):
    """
    Create a few RFE transactions to simulate initial purchasers filling the blockchain
    without tx fees present.
    """

    # Set up a purchaser account.
    purchaser_account = src.util.helpers.random_string()
    ndau(f'account new {purchaser_account}')
    ndau(f'account claim {purchaser_account}')
    # Put a lot of ndau in there so small EAI fee percentages are non-zero.
    ndau(f'rfe 1000000 {purchaser_account}')
    # Lock it for a long time to maximize EAI.
    ndau(f'account lock {purchaser_account} 3y')

    # Set up a node operator account with 1000 ndau needed to self-stake.
    node_account = src.util.helpers.random_string()
    ndau(f'account new {node_account}')
    ndau(f'account claim {node_account}')
    ndau(f'rfe 1000 {node_account}')

    # Self-stake and register the node account to the node.
    ndau(f'account stake {node_account} {node_account}')
    rpc_address = f'http://{ndau_node_exists["address"]}:{ndau_node_exists["nodenet0_rpc"]}'
    # Bytes lifted from tx_register_node_test.go.
    distribution_script_bytes = b'\xa0\x00\x88'
    distribution_script = base64.b64encode(distribution_script_bytes).decode('utf-8')
    ndau(f'account register-node {node_account} {rpc_address} {distribution_script}')

    # Delegate purchaser account to node account.
    ndau(f'account delegate {purchaser_account} {node_account}')

    # Build up an array of accounts with EAI fee percents associated with each.
    accounts = []
    scale = 1e8 # The EAIFeeTable uses percentages in units of napu.
    percent = scale # Start out at 100% and we'll dish out pieces of this over multiple accounts.
    for entry in src.util.constants.EAI_FEE_TABLE:
        pair = entry.split(':')
        pct = float(pair[0])
        acct = pair[1]
        if len(acct) == 0:
            acct = node_account
            flag = '' # node_account is an account name, no flag when querying account data.
        else:
            flag = '-a' # acct is an address, must use the -a flag when querying account data.
        account_data = json.loads(ndau(f'account query {flag} {acct}'))
        accounts.append(Account(acct, flag, pct / scale, account_data['balance']))
        percent -= pct
    # The remaining percent goes to the purchaser account.
    account_data = json.loads(ndau(f'account query {purchaser_account}'))
    accounts.append(Account(purchaser_account, '', percent / scale, account_data['balance']))

    # Submit CreditEAI transaction so that the market maker can have ndau to pay for RFE tx fees.
    # The initial CreditEAI
    ndau(f'account credit-eai {node_account}')

    # This is the napu you earn with the amount of locked ndau in play, with no time passing.
    total_eai_expect = 2853800 # 0.028538 ndau
    # Check that EAI was credited to all the right accounts.
    for account in accounts:
        account_data = json.loads(ndau(f'account query {account.flag} {account.account}'))
        new_balance = account_data['balance']
        # Node operators don't get their cut of EAI until node rewards are claimed.
        if account.account == node_account:
            eai_expect = 0
        else:
            eai_expect = int(total_eai_expect * account.percent)
        eai_actual = new_balance - account.balance
        assert eai_actual == eai_expect
