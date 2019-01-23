"""Tests that single validator nodes operate as expected."""

import base64
import json
import pytest
import src.util.constants
import src.util.helpers
from src.util.subp import subp
from time import sleep


def test_get_ndau_status(node_net, ndau):
    """`ndautool` can connect to `ndau node` and get status."""
    info = json.loads(ndau('info'))
    moniker = info['node_info']['moniker']
    assert moniker == f'{node_net}-0'


def test_genesis(perform_genesis):
    """Simulate genesis operations, even if they've happened already."""
    perform_genesis()


def test_create_account(chaos, ndau, rfe, ensure_post_genesis_tx_fees):
    """Create account, RFE to it, and check attributes"""
    _random_string = src.util.helpers.random_string()
    known_ids = ndau('account list').splitlines()
    # make sure account does not already exist
    assert not any(_random_string in id_line for id_line in known_ids)
    # create new randomly named account
    ndau(f'account new {_random_string}')
    new_ids = ndau('account list').splitlines()
    # check that account now exists
    assert any(_random_string in id_line for id_line in new_ids)
    id_line = [s for s in new_ids if _random_string in s]
    # check that account is not claimed (has 0 tx keys)
    assert '(0 tr keys)' in id_line[0]
    account_data = json.loads(ndau(f'account query {_random_string}'))
    assert account_data['validationKeys'] == None
    # RFE to account 10 ndau
    orig_ndau = 10
    orig_napu = orig_ndau * 1e8
    rfe(orig_ndau, _random_string)
    account_data = json.loads(ndau(f'account query {_random_string}'))
    # check that account balance is 10 ndau
    assert account_data['balance'] == orig_napu
    # We want to test non-zero transaction fees.
    ensure_post_genesis_tx_fees()
    # claim account, and check that account now has validation keys
    ndau(f'account claim {_random_string}')
    account_data = json.loads(ndau(f'account query {_random_string}'))
    assert account_data['validationKeys'] != None
    # check that 1 napu tx fee was deducted from account
    assert account_data['balance'] == orig_napu - src.util.constants.ONE_NAPU_FEE


def test_transfer(chaos, ndau, rfe, ensure_post_genesis_tx_fees):
    """Test Transfer transaction"""

    # We want to test non-zero transaction fees.
    ensure_post_genesis_tx_fees()

    # Set up accounts to transfer between.
    account1 = src.util.helpers.random_string()
    src.util.helpers.set_up_account(ndau, rfe, account1)
    account2 = src.util.helpers.random_string()
    src.util.helpers.set_up_account(ndau, rfe, account2)

    orig_ndau = 10 # from set_up_account()
    orig_napu = orig_ndau * 1e8
    xfer_ndau = 1 # We'll transfer this amount
    xfer_napu = xfer_ndau * 1e8

    # One napu for the claim transaction.
    account_data1 = json.loads(ndau(f'account query {account1}'))
    assert account_data1['balance'] == orig_napu - src.util.constants.ONE_NAPU_FEE

    # Transfer
    ndau(f'transfer {xfer_ndau} {account1} {account2}')
    account_data1 = json.loads(ndau(f'account query {account1}'))
    account_data2 = json.loads(ndau(f'account query {account2}'))
    # Subtract one napu for the claim transaction, one for the transfer.
    assert account_data1['balance'] == orig_napu - xfer_napu - 2 * src.util.constants.ONE_NAPU_FEE
    assert account_data1['lock'] == None
    # Subtract one napu for the claim transaction.
    assert account_data2['balance'] == orig_napu + xfer_napu - src.util.constants.ONE_NAPU_FEE
    assert account_data2['lock'] == None


def test_transfer_lock(chaos, ndau, rfe, ensure_post_genesis_tx_fees):
    """Test TransferLock transaction"""

    # We want to test non-zero transaction fees.
    ensure_post_genesis_tx_fees()

    # Set up source claimed account with funds.
    account1 = src.util.helpers.random_string()
    src.util.helpers.set_up_account(ndau, rfe, account1)

    # Create destination account, but don't claim or rfe to it (otherwise transfer-lock fails).
    account2 = src.util.helpers.random_string()
    ndau(f'account new {account2}')

    orig_ndau = 10 # from set_up_account()
    orig_napu = orig_ndau * 1e8
    xfer_ndau = 1 # We'll transfer this amount
    xfer_napu = xfer_ndau * 1e8

    # One napu for the claim transaction.
    account_data1 = json.loads(ndau(f'account query {account1}'))
    assert account_data1['balance'] == orig_napu - src.util.constants.ONE_NAPU_FEE

    # TransferLock
    lock_months = 3
    ndau(f'transfer-lock {xfer_ndau} {account1} {account2} {lock_months}m')
    account_data1 = json.loads(ndau(f'account query {account1}'))
    account_data2 = json.loads(ndau(f'account query {account2}'))
    # Subtract one napu for the claim transaction, one for the transfer-lock.
    assert account_data1['balance'] == orig_napu - xfer_napu - 2 * src.util.constants.ONE_NAPU_FEE
    assert account_data1['lock'] == None
    # No claim transaction, no fee.  Just gain the amount transferred.
    assert account_data2['balance'] == xfer_napu
    assert account_data2['lock'] != None
    assert account_data2['lock']['unlocksOn'] == None


def test_lock_notify(ndau, rfe):
    """Test Lock and Notify transactions"""

    # Set up account to lock.
    account = src.util.helpers.random_string()
    src.util.helpers.set_up_account(ndau, rfe, account)

    # Lock
    lock_months = 3
    ndau(f'account lock {account} {lock_months}m')
    account_data = json.loads(ndau(f'account query {account}'))
    assert account_data['lock'] != None
    assert account_data['lock']['unlocksOn'] == None

    # Notify
    ndau(f'account notify {account}')
    account_data = json.loads(ndau(f'account query {account}'))
    assert account_data['lock'] != None
    assert account_data['lock']['unlocksOn'] != None


def test_change_settlement_period(ndau, rfe):
    """Test ChangeSettlementPeriod transaction"""

    # Set up an account.
    account = src.util.helpers.random_string()
    src.util.helpers.set_up_account(ndau, rfe, account)
    account_data = json.loads(ndau(f'account query {account}'))
    assert account_data['settlementSettings'] != None
    assert account_data['settlementSettings']['Period'] == 't0s'

    # ChangeSettlementPeriod
    period_months = 3
    ndau(f'account change-settlement-period {account} {period_months}m')
    account_data = json.loads(ndau(f'account query {account}'))
    assert account_data['settlementSettings'] != None
    assert account_data['settlementSettings']['Period'] == 't3m'


def test_change_validation(ndau, rfe):
    """Test ChangeValidation transaction"""

    # Set up an account.
    account = src.util.helpers.random_string()
    src.util.helpers.set_up_account(ndau, rfe, account)
    account_data = json.loads(ndau(f'account query {account}'))
    assert account_data['validationKeys'] != None
    assert len(account_data['validationKeys']) == 1
    key1 = account_data['validationKeys'][0]
    assert account_data['validationScript'] == None

    # Add
    ndau(f'account validation {account} add')
    account_data = json.loads(ndau(f'account query {account}'))
    assert account_data['validationKeys'] != None
    assert len(account_data['validationKeys']) == 2
    assert account_data['validationKeys'][0] == key1
    assert account_data['validationKeys'][1] != key1
    assert account_data['validationScript'] == None

    # Reset
    ndau(f'account validation {account} reset')
    account_data = json.loads(ndau(f'account query {account}'))
    assert account_data['validationKeys'] != None
    assert len(account_data['validationKeys']) == 1
    assert account_data['validationKeys'][0] != key1
    assert account_data['validationScript'] == None

    # SetScript
    ndau(f'account validation {account} set-script oAAgiA')
    account_data = json.loads(ndau(f'account query {account}'))
    assert account_data['validationScript'] == 'oAAgiA=='


def test_command_validator_change(ndau):
    """Test CommandValidatorChange transaction"""

    # Get info about the validator we want to change.
    info = json.loads(ndau('info'))
    assert info['validator_info'] != None
    assert info['validator_info']['pub_key'] != None

    assert len(info['validator_info']['pub_key']) > 0
    pubkey_bytes = bytes(info['validator_info']['pub_key'])

    assert info['validator_info']['voting_power'] != None
    old_power = info['validator_info']['voting_power']

    # Get non-padded base64 encoding.
    pubkey = base64.b64encode(pubkey_bytes).decode('utf-8').rstrip('=')

    # Cycle over a power range of 5, starting at the default power of 10.
    new_power = 10 + (old_power + 6) % 5

    # CVC
    ndau(f'cvc {pubkey} {new_power}')

    # Wait up to 10 seconds for the change in power to propagate.
    new_voting_power_was_set = False
    for i in range(10):
        sleep(1)
        info = json.loads(ndau('info'))
        assert info['validator_info'] != None
        voting_power = info['validator_info']['voting_power']
        if voting_power == new_power:
            new_voting_power_was_set = True
            break
        assert voting_power == old_power
    assert new_voting_power_was_set
