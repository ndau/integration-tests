"""Tests that single validator nodes operate as expected."""
import os
import subprocess
from random import choice, choices
from string import ascii_lowercase, digits
from time import sleep
import json

import pytest
import toml
import pdb

from src.util.subp import subp
from pathlib import Path


@pytest.fixture
def _random_string(len=16):
    return ''.join(choices(ascii_lowercase+digits, k=len))


def test_get_status(use_kub, ndau):
    """`ndautool` can connect to `ndau node` and get status."""
    info = json.loads(ndau('info'))
    moniker = info['node_info']['moniker']
    if use_kub:
        assert moniker == 'devnet-0'
    else:
        assert moniker == subp('hostname')


def test_create_account(ndau, set_rfe_address, _random_string):
    """Create account, RFE to it, and check attributes"""
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
    # check that 1 napu tx fee was deducted from account
    assert account_data['balance'] == 999999999
