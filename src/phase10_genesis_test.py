"""
Test:
- Pre-genesis RFE
- Genesis CreditEAI
- Changing tx fees post-genesis
"""

import base64
import json
import math
import os.path
import pytest
import toml
import src.util.constants
import src.util.helpers


def test_prepare(set_addresses_in_toml):
    """
    This is here as an initial step that must happen before any other tests run in this file.
    It invokes the set_addresses_in_toml fixture.
    """


class Account:
    def __init__(self, act, flg, pct, bal):
        self.account = act # Account name or address.
        self.flag    = flg # Flag to use with account string with ndau account query commands.
        self.percent = pct # EAI fee percent this account receives from CreditEAI.
        self.balance = bal # Initial balance of the account before CreditEAI.


def test_genesis_eai(ndau, ndau_no_error, ndau_node_exists):
    """
    Create a few RFE transactions to simulate initial purchasers filling the blockchain
    without tx fees present.  Then CreditEAI and NNR and make sure all accounts get their EAI.
    """

    # Set up a purchaser account.
    purchaser_account = src.util.helpers.random_string()
    ndau(f'account new {purchaser_account}')
    ndau(f'account claim {purchaser_account}')

    # Put a lot of ndau in there so small EAI fee percentages are non-zero.
    ndau_locked = 1000000
    ndau(f'rfe {ndau_locked} {purchaser_account}')

    # Lock it for a long time to maximize EAI.
    lock_years = 3
    ndau(f'account lock {purchaser_account} {lock_years}y')

    # Set up a node operator account with 1000 ndau needed to self-stake.
    node_account = src.util.helpers.random_string()
    ndau(f'account new {node_account}')
    ndau(f'account claim {node_account}')
    ndau(f'rfe 1000 {node_account}')
    node_account_percent = 0 # We'll get this from the EAIFeeTable.

    # Self-stake and register the node account to the node.
    ndau(f'account stake {node_account} {node_account}')
    rpc_address = f'http://{ndau_node_exists["address"]}:{ndau_node_exists["nodenet0_rpc"]}'
    # Bytes lifted from tx_register_node_test.go.
    distribution_script_bytes = b'\xa0\x00\x88'
    distribution_script = base64.b64encode(distribution_script_bytes).decode('utf-8')
    ndau(f'account register-node {node_account} {rpc_address} {distribution_script}')

    # Set up a reward target account.
    reward_account = src.util.helpers.random_string()
    ndau(f'account new {reward_account}')
    ndau(f'account claim {reward_account}')
    ndau(f'account set-rewards-target {node_account} {reward_account}')

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
            node_account_percent = pct / scale
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
    # It's outside the scope of this test to compute this value.  Unit tests take care of that.
    # This integration test makes sure that all the accounts in the EAIFeeTable get their cut.
    total_napu_expect = 3805100

    # Check that EAI was credited to all the right accounts.
    for account in accounts:
        account_data = json.loads(ndau(f'account query {account.flag} {account.account}'))
        new_balance = account_data['balance']
        # Node operators don't get their cut of EAI until node rewards are claimed.
        if account.account == node_account:
            eai_expect = 0
        else:
            eai_expect = int(total_napu_expect * account.percent)
        eai_actual = new_balance - account.balance
        assert eai_actual == eai_expect

    # Nominate node rewards.  Unfortunately, we can only run this integration test once per day.
    # When running against localnet, we can do a reset easily to test NNR repeatedly.
    nnr_result = ndau_no_error(f'nnr -g')
    if not nnr_result.startswith('not enough time since last NNR'):
        # Claim node rewards and see that the node operator gets his EAI in the reward account.
        # We check the reward account.  If we didn't set a reward target, then the node account
        # would receive the ndau here.  That was tested and worked, but since we can only do one
        # NNR per day, we test the more complex situation of awarding to a target reward account.
        ndau(f'account claim-node-reward {node_account}')
        account_data = json.loads(ndau(f'account query {reward_account}'))
        eai_actual = account_data['balance']
        eai_expect = int(total_napu_expect * node_account_percent)
        assert eai_actual == eai_expect
