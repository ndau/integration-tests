"""Tests that single validator nodes operate as expected."""
import os
import subprocess
from time import sleep

import pytest
import pdb
import json

from src.util.subp import subp
import src.util.helpers


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


def test_get_chaos_status(use_kub, chaos):
    """`chaostool` can connect to `chaos-go` and get status."""
    info = json.loads(chaos('info'))
    moniker = info['node_info']['moniker']
    if use_kub:
        assert moniker == 'devnet-0'
    else:
        assert moniker == subp('hostname')


def test_create_id(chaos, ndau):
    """First line is always a header."""
    _random_string = src.util.helpers.random_string()
    known_ids = chaos('id list').splitlines()[1:]
    assert not any(_random_string in id_line for id_line in known_ids)
    src.util.helpers.set_up_account(ndau, _random_string)
    src.util.helpers.set_up_namespace(chaos, _random_string)
    new_ids = chaos('id list').splitlines()[1:]
    assert any(_random_string in id_line for id_line in new_ids)


def test_set_get(chaos, ndau):
    """`chaostool` can set a value and get it back later."""
    _random_string = src.util.helpers.random_string()
    conf_path = ndau('conf-path')
    f = open(conf_path, "r")
    conf_lines = f.readlines()
    f.close()
    print(conf_lines)
    src.util.helpers.set_up_account(ndau, _random_string)
    src.util.helpers.set_up_namespace(chaos, _random_string)
    chaos(f'set {_random_string} -k key -v value')
    v = chaos(f'get {_random_string} -k key -s')
    assert v == 'value'


# @pytest.mark.slow
def test_set_delay_get(chaos, ndau):
    """Getting a value doesn't depend on it remaining in memory."""
    _random_string = src.util.helpers.random_string()
    src.util.helpers.set_up_account(ndau, _random_string)
    src.util.helpers.set_up_namespace(chaos, _random_string)
    chaos(f'set {_random_string} -k key -v value')
    sleep(2)
    v = chaos(f'get {_random_string} -k key -s')
    assert v == 'value'


def test_remove(chaos, ndau):
    """`chaostool` can remove a value."""
    _random_string = src.util.helpers.random_string()
    src.util.helpers.set_up_account(ndau, _random_string)
    src.util.helpers.set_up_namespace(chaos, _random_string)
    chaos(f'set {_random_string} -k key -v value')
    chaos(f"set {_random_string} -k key -v ''")
    v = chaos(f'get {_random_string} -k key -s')
    assert v == ''


def test_get_ns(chaos, ndau, chaos_namespace_query, ndau_account_query):
    """`chaostool` can list all namespaces."""
    # set up some namespaces with some data in each
    num_ns = len(chaos('get-ns').splitlines())
    nss = ('one', 'two', 'three')
    for ns in nss:
        if ndau_account_query(ns) == 'No such named account':
            src.util.helpers.set_up_account(ndau, ns)
        if chaos_namespace_query(ns) == f'getting namespace: no such identity: {ns}':
            src.util.helpers.set_up_namespace(chaos, ns)
        else:
            num_ns -= 1
        chaos(f'set {ns} -k key -v value')
    # wait to ensure that the blockchain is updated
    sleep(2)

    # get the namespaces
    namespaces = chaos('get-ns').splitlines()
    print(f'namespaces = {namespaces}')
    assert len(namespaces) == num_ns + len(nss)


def test_dump(chaos, ndau, chaos_namespace_query, ndau_account_query):
    """`chaostool` can dump all k-v pairs from a given namespace."""
    # set up a second namespace to ensure we filter out others
    nss = ('one', 'two')
    for ns in nss:
        if ndau_account_query(ns) == 'No such named account':
            src.util.helpers.set_up_account(ndau, ns)
        if chaos_namespace_query(ns) == f'getting namespace: no such identity: {ns}':
            src.util.helpers.set_up_namespace(chaos, ns)
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


def test_can_retrieve_values_using_namespace(chaos, ndau):
    """Values can be retrieved given only the namespace and key."""
    temp = src.util.helpers.random_string()
    src.util.helpers.set_up_account(ndau, temp)
    namespace_b64 = src.util.helpers.set_up_namespace(chaos, temp)
    chaos(f'set {temp} -k "this key is durable" -v "really"')

    val = chaos(f'get --ns={namespace_b64} -k "this key is durable" -s')
    assert val == "really"


def test_cannot_overwrite_others_namespace(chaos, ndau, chaos_namespace_query, ndau_account_query):
    """Users cannot overwrite each others' values."""
    nss = ('one', 'two')
    for ns in nss:
        if ndau_account_query(ns) == 'No such named account':
            src.util.helpers.set_up_account(ndau, ns)
        if chaos_namespace_query(ns) == f'getting namespace: no such identity: {ns}':
            src.util.helpers.set_up_namespace(chaos, ns)
        chaos(f'set {ns} -k key -v "value {ns}"')
    for ns in nss:
        v = chaos(f'get {ns} -k key -s')
        assert v == f'value {ns}'


# @pytest.mark.slow
def test_get_history(chaos, ndau):
    """`chaostool` can list the history of a value."""
    historic = src.util.helpers.random_string()
    src.util.helpers.set_up_account(ndau, historic)
    src.util.helpers.set_up_namespace(chaos, historic)
    for i in range(5):
        chaos(f'set {historic} -k counter -v {i}')
        # wait for a few blocks to pass before setting next value
        sleep(2)
    history = [
        line.strip()
        for line in chaos(f'history {historic} -k counter -s').splitlines()
        if len(line.strip()) > 0 and 'Height' not in line
    ]
    assert history == [str(i) for i in range(5)]


def test_reject_non_whitelisted_scps(chaos_and_whitelist):
    """`chaostool` can send a non-whitelisted SCP but it it not accepted."""
    chaos = chaos_and_whitelist['chaos']
    whitelist = chaos_and_whitelist['whitelist']

    key = src.util.helpers.random_string()
    value = src.util.helpers.random_string()

    assert whitelist(f'check {key} -v {value}') == 'false'
    with pytest.raises(subprocess.CalledProcessError):
        chaos(f'scp -k {key} -v {value}')

    # TODO: Refactor this for the new way we handle system namespaces.
    # --sys is no longer supported.
    #sys_val = chaos(f'get --sys -k {key} -s')
    #assert len(sys_val.strip()) == 0


def test_whitelist_tool_can_whitelist(chaos_and_whitelist):
    """`ndwhitelist` can whitelist a SCP."""
    whitelist = chaos_and_whitelist['whitelist']

    key = src.util.helpers.random_string()
    value = src.util.helpers.random_string()

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


def test_whitelisted_scps_are_accepted(use_kub, chaos_and_whitelist):
    """`chaostool` can send a whitelisted SCP and it is accepted."""
    chaos = chaos_and_whitelist['chaos']
    whitelist = chaos_and_whitelist['whitelist']

    key = src.util.helpers.random_string()
    value = src.util.helpers.random_string()

    print("adding key and value to whitelist")
    wl_command = f'add {key} -v {value}'
    print(f'wl command = {wl_command}')
    wl_res = whitelist(wl_command)
    print(f'wl res = {wl_res}')
    # JSG if run on Kub, just check if the wl command ran successfully
    # SCP will currently fail with remote nodes
    if use_kub:
        wl_res_word = wl_res.split()[0]
        assert wl_res_word == "Successfully"
        return

    print("sending as scp")
    scp_command = f'scp -k {key} -v {value}'

    """
    # TODO: Refactor this for the new way we handle system namespaces.
    # --sys and scp are no longer supported.
    print(f'scp command = {scp_command}')
    chaos(scp_command)

    # allow block to finalize
    sleep(3)

    print('verifying sys value')
    actual_val = chaos(f'get --sys -k {key} -s')
    assert actual_val == value
    """
