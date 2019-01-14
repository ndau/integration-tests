"""Tests that single validator nodes operate as expected."""
import json

import pytest
import pdb

from src.util.subp import subp
import src.util.helpers


def test_get_ndau_status(node_net, ndau):
    """`ndautool` can connect to `ndau node` and get status."""
    info = json.loads(ndau('info'))
    moniker = info['node_info']['moniker']
    assert moniker == f'{node_net}-0'


def test_create_account_pre_genesis(ndau):
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
    ndau(f'rfe 10 {_random_string}')
    account_data = json.loads(ndau(f'account query {_random_string}'))
    # check that account balance is 10 ndau
    assert account_data['balance'] == 1000000000
    # claim account, and check that account now has validation keys
    ndau(f'account claim {_random_string}')
    account_data = json.loads(ndau(f'account query {_random_string}'))
    assert account_data['validationKeys'] != None
    # check that 0 napu tx fee was deducted from account, there are no tx fees pre-genesis
    expected_balance = 1000000000
    assert account_data['balance'] == expected_balance


def test_transfer(ndau):
    """Test Transfer transation"""

    # Set up accounts to transfer between.
    account1 = src.util.helpers.random_string()
    src.util.helpers.set_up_account(ndau, account1)
    account2 = src.util.helpers.random_string()
    src.util.helpers.set_up_account(ndau, account2)

    # Transfer
    ndau(f'transfer 1 {account1} {account2}')
    account_data1 = json.loads(ndau(f'account query {account1}'))
    account_data2 = json.loads(ndau(f'account query {account2}'))
    assert account_data1['balance'] == 900000000
    assert account_data1['lock'] == None
    assert account_data2['balance'] == 1100000000
    assert account_data2['lock'] == None


def test_transfer_lock(ndau):
    """Test TransferLock transation"""

    # Set up source claimed account with funds.
    account1 = src.util.helpers.random_string()
    src.util.helpers.set_up_account(ndau, account1)

    # Create destination account.
    account2 = src.util.helpers.random_string()
    ndau(f'account new {account2}')

    # TransferLock
    lock_months = 3
    ndau(f'transfer-lock 1 {account1} {account2} {lock_months}m')
    account_data1 = json.loads(ndau(f'account query {account1}'))
    account_data2 = json.loads(ndau(f'account query {account2}'))
    assert account_data1['balance'] == 900000000
    assert account_data1['lock'] == None
    assert account_data2['balance'] == 100000000
    assert account_data2['lock'] != None
    assert account_data2['lock']['unlocksOn'] == None


def test_transfer_lock_notify(ndau):
    """Test Lock and Notify transations"""

    # Set up account to lock.
    account = src.util.helpers.random_string()
    src.util.helpers.set_up_account(ndau, account)

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
