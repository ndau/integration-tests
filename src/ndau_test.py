"""Tests that single validator nodes operate as expected."""
import json

import pytest
import pdb

from src.util.subp import subp
import src.util.helpers


def test_get_ndau_status(use_kub, node_net, ndau):
    """`ndautool` can connect to `ndau node` and get status."""
    info = json.loads(ndau('info'))
    moniker = info['node_info']['moniker']
    if use_kub:
        assert moniker == f'{node_net}-0'
    else:
        assert moniker == subp('hostname')


def test_create_account_pre_genesis(ndau, set_rfe_address):
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
    assert account_data['balance'] == 1000000000
