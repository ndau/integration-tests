"""Tests that single validator nodes operate as expected."""
import os
import subprocess
from random import choice, choices
from string import ascii_lowercase, digits
from time import sleep

import pytest
import toml
import pdb
import json

from src.util.subp import subp


@pytest.fixture
def _random_string(len=16):
    return ''.join(choices(ascii_lowercase+digits, k=len))


@pytest.fixture
def chaos_and_whitelist(chaos_node_and_tool, whitelist_build):
    """
    Fixture providing a chaos function and a whitelist function.

    The chaos function calls the chaos command in a configured environment.
    The whitelist function calls the ndwhitelist command in a configured
    environment.
    """
    def ch_f(cmd, **kwargs):
        try:
            return subp(
                f'{chaos_node_and_tool["tool"]["bin"]} {cmd}',
                env=chaos_node_and_tool["env"],
                stderr=subprocess.STDOUT,
                **kwargs,
            )
        except subprocess.CalledProcessError as e:
            print(e.stdout)
            raise

    def wl_f(cmd, **kwargs):
        try:
            return subp(
                f'{whitelist_build["bin"]} chaos {cmd}',
                env=chaos_node_and_tool["env"],
                stderr=subprocess.STDOUT,
                **kwargs,
            )
        except subprocess.CalledProcessError as e:
            print(e.stdout)
            raise
    return {'chaos': ch_f, 'whitelist': wl_f}


def test_get_status(chaos):
    """`chaostool` can connect to `chaos-go` and get status."""
    chaos('info')

def test_get_status(ndau):
    """`ndautool` can connect to `ndau node` and get status."""
#    pdb.set_trace()
    info = json.loads(ndau('info'))
    assert info['node_info']['moniker'] == 'devnet-0'

def test_create_account(ndau, _random_string):
    """Create account, RFE to it, and check attributes"""
#    pdb.set_trace()
    conf_path = ndau('conf-path')
    f = open(conf_path, "a")
    # write RFE address and keys into ndautool.toml file
    f.write("[rfe]\n")
    f.write("address = \"ndmfgnz9qby6nyi35aadjt9nasjqxqyd4vrswucwfmceqs3y\"\n")
    f.write("keys = [\"npvtayjadtcbid6g7nm4xey8ff2vd5vs3fxaev6gdhhjsmv8zvp997rm69miahnxms7fi5k6rkkrecp7br3rwdd8frxdiexjvcdcf9itqaz578mqu6fk82cgce3s\"]")
    f.close()
    f = open(conf_path, "r")
    conf_lines = f.readlines()
    f.close()
    # make sure RFE address exists in ndautool.toml file
    assert any("ndmfgnz9qby6nyi35aadjt9nasjqxqyd4vrswucwfmceqs3y" in line for line in conf_lines)
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


def test_create_id(chaos, _random_string):
    """First line is always a header."""
    known_ids = chaos('id list').splitlines()[1:]
    assert not any(_random_string in id_line for id_line in known_ids)
    chaos(f'id new {_random_string}')
    new_ids = chaos('id list').splitlines()[1:]
    assert any(_random_string in id_line for id_line in new_ids)


def test_set_get(chaos, ndau, _random_string):
    """`chaostool` can set a value and get it back later."""
#    pdb.set_trace()
    conf_path = ndau('conf-path')
    f = open(conf_path, "r")
    conf_lines = f.readlines()
    f.close()
    print(conf_lines)
    ndau(f'account new {_random_string}')
    ndau(f'rfe 10 {_random_string}')
    ndau(f'account claim {_random_string}')
    chaos(f'id new {_random_string}')
    chaos(f'id copy-keys-from {_random_string}')
    chaos(f'set {_random_string} -k key -v value')
    v = chaos(f'get {_random_string} -k key -s')
    assert v == 'value'


# @pytest.mark.slow
def test_set_delay_get(chaos, _random_string):
    """Getting a value doesn't depend on it remaining in memory."""
    chaos(f'id new {_random_string}')
    chaos(f'set {_random_string} -k key -v value')
    sleep(2)
    v = chaos(f'get {_random_string} -k key -s')
    assert v == 'value'


def test_remove(chaos, _random_string):
    """`chaostool` can remove a value."""
    chaos(f'id new {_random_string}')
    chaos(f'set {_random_string} -k key -v value')
    chaos(f"set {_random_string} -k key -v ''")
    v = chaos(f'get {_random_string} -k key -s')
    assert v == ''


def test_get_ns(chaos):
    """`chaostool` can list all namespaces."""
    # set up some namespaces with some data in each
    num_ns = len(chaos('get-ns').splitlines())
    nss = ('one', 'two', 'three')
    for ns in nss:
        chaos(f'id new {ns}')
        chaos(f'set {ns} -k key -v value')
    # wait to ensure that the blockchain is updated
    sleep(2)

    # delete a namespace from the local config so we know that we're
    # reading from the chain, not just echoing local data somehow
    cp = chaos('conf-path')
    with open(cp, 'rt') as fp:
        conf = toml.load(fp)
    to_remove = nss.index(choice(nss))
    del conf['identities'][to_remove]
    with open(cp, 'wt') as fp:
        toml.dump(conf, fp)

    # get the namespaces
    namespaces = chaos('get-ns').splitlines()
    print(f'namespaces = {namespaces}')
    assert len(namespaces) == num_ns + len(nss)


def test_dump(chaos):
    """`chaostool` can dump all k-v pairs from a given namespace."""
    # set up a second namespace to ensure we filter out others
    nss = ('one', 'two')
    for ns in nss:
        chaos(f'id new {ns}')
        chaos(f'set {ns} -k key -v "value {ns}"')
    chaos('set one -k "another key" -v "another value"')
    chaos('set one -k "the key" -v "let go"')

    expected_lines = set((
        '"key"="value one"',
        '"another key"="another value"',
        '"the key"="let go"',
    ))

    found_lines = set(chaos('dump one -s').splitlines())

    assert expected_lines == found_lines


def test_can_retrieve_values_using_namespace(chaos):
    """Values can be retrieved given only the namespace and key."""
    res = chaos('id new temp')
#    pdb.set_trace()
    namespace_b64 = res.split()[4]
    chaos('set temp -k "this key is durable" -v "really"')

    # get the namespace from the local config, and also delete that key,
    # so if we want that value back, we _need_ to use the namespace.
    cp = chaos('conf-path')
    with open(cp, 'rt') as fp:
        conf = toml.load(fp)
#    pdb.set_trace()
#    t_name = conf['identities'][0]['name']
    del conf['identities'][0]
    with open(cp, 'wt') as fp:
        toml.dump(conf, fp)

#    val = chaos(f'get --ns="{t_name}" -k "this key is durable" -s')
    val = chaos(f'get --ns={namespace_b64} -k "this key is durable" -s')
    assert val == "really"


def test_cannot_overwrite_others_namespace(chaos):
    """Users cannot overwrite each others' values."""
    nss = ('one', 'two')
    for ns in nss:
        chaos(f'id new {ns}')
        chaos(f'set {ns} -k key -v "value {ns}"')
    for ns in nss:
        v = chaos(f'get {ns} -k key -s')
        assert v == f'value {ns}'


# @pytest.mark.slow
def test_get_history(chaos):
    """`chaostool` can list the history of a value."""
    chaos('id new historic')
    for i in range(5):
        chaos(f'set historic -k counter -v {i}')
        # wait for a few blocks to pass before setting next value
        sleep(2)
    history = [
        line.strip()
        for line in chaos('history historic -k counter -s').splitlines()
        if len(line.strip()) > 0 and 'Height' not in line
    ]
    assert history == [str(i) for i in range(5)]


def test_reject_non_whitelisted_scps(chaos_and_whitelist):
    """`chaostool` can send a non-whitelisted SCP but it it not accepted."""
    chaos = chaos_and_whitelist['chaos']
    whitelist = chaos_and_whitelist['whitelist']

    key = _random_string()
    value = _random_string()

    assert whitelist(f'check {key} -v {value}') == 'false'
    with pytest.raises(subprocess.CalledProcessError):
        chaos(f'scp -k {key} -v {value}')

    sys_val = chaos(f'get --sys -k {key} -s')
    assert len(sys_val.strip()) == 0


def test_whitelist_tool_can_whitelist(chaos_and_whitelist):
    """`ndwhitelist` can whitelist a SCP."""
    whitelist = chaos_and_whitelist['whitelist']

    key = _random_string()
    value = _random_string()

    print("whitelist path:")
    path = whitelist('path')
    print(path)
    assert whitelist(f'check {key} -v {value}') == 'false'

    print("adding a k-v pair to whitelist")
    print(whitelist(f'add {key} -v {value}'))

    print(f"whitelist exists: {os.path.exists(path)}")

    with open(path, 'rb') as fp:
        wl_data = fp.read()
    print(f"len(wl_data): {len(wl_data)}")
    wl_data_hex = ''.join(f'{b:02x} ' for b in wl_data)
    print(f"whitelist as hex: {wl_data_hex}")

    print(whitelist('list -v'))
    assert whitelist(f'check {key} -v {value}') == 'true'


def test_whitelisted_scps_are_accepted(run_kub, chaos_and_whitelist):
    """`chaostool` can send a whitelisted SCP and it is accepted."""
    chaos = chaos_and_whitelist['chaos']
    whitelist = chaos_and_whitelist['whitelist']

    key = _random_string()
    value = _random_string()

    print("adding key and value to whitelist")
    wl_command = f'add {key} -v {value}'
    print(f'wl command = {wl_command}')
    wl_res = whitelist(wl_command)
    print(f'wl res = {wl_res}')
    # JSG if run on Kub, just check if the wl command ran successfully
    # SCP will currently fail with remote nodes
    if run_kub:
        wl_res_word = wl_res.split()[0]
        assert wl_res_word == "Successfully"
        return

    print("sending as scp")
    scp_command = f'scp -k {key} -v {value}'
    print(f'scp command = {scp_command}')
    chaos(scp_command)

    # allow block to finalize
    sleep(3)

    print('verifying sys value')
    actual_val = chaos(f'get --sys -k {key} -s')
    assert actual_val == value
