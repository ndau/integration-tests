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

from src.subp import subp
from pathlib import Path


@pytest.fixture
def _random_string(len=16):
    return ''.join(choices(ascii_lowercase+digits, k=len))


@pytest.fixture
def ndau(ndau_node_and_tool):
    """
    Fixture providing a ndau function.

    This function calls the ndau command in a configured environment.
    """
    def rf(cmd, **kwargs):
        try:
            return subp(
                f'{ndau_node_and_tool["tool"]["bin"]} {cmd}',
                env=ndau_node_and_tool["env"],
                stderr=subprocess.STDOUT,
                **kwargs,
            )
        except subprocess.CalledProcessError as e:
            print(e.stdout)
            raise
    return rf

def test_get_status(ndau):
    """`ndautool` can connect to `ndau node` and get status."""
    info = json.loads(ndau('info'))
    assert info['node_info']['moniker'] == 'devnet-0'

def test_create_account(ndau, _random_string):
    """Create account and check attributes"""
#    pdb.set_trace()
    conf_path = ndau('conf-path')
    f = open(conf_path, "a")
    # write RFE address and keys into ndautool.toml file
    f.write("[rfe]\n")
    f.write("address = \"ndnd8tjeg4n9jb8m9zcepksqjkiegrmewmajchjbi28v8c4p\"\n")
    f.write("keys = [\"npvtayjadtcbicwwxjh2v4m75gjk22isu2gydqufu3yiyyifb9rittexcyaeczphffzit96bc8fytjf2qssqefp6czwivh4bt7rs26v8fx78n5rjpts868fn4src\", \"npvtayjadtcbica87enrkc8wjxzm4xiszietb4ktb5i3s98ezttsftastntbuvq4pwc5szgufwajx6kiqvsw87hbf635234u3zmmhqe6yjtqgsbqath3ewe8dg8j\"]")
    f.close()
    f = open(conf_path, "r")
    conf_lines = f.readlines()
    f.close()
    # make sure RFE address exists in ndautool.toml file
    assert any("ndnd8tjeg4n9jb8m9zcepksqjkiegrmewmajchjbi28v8c4p" in line for line in conf_lines)
    known_ids = ndau('account list').splitlines()
    assert not any(_random_string in id_line for id_line in known_ids)
    ndau(f'account new {_random_string}')
    new_ids = ndau('account list').splitlines()
    assert any(_random_string in id_line for id_line in new_ids)
    id_line = [s for s in new_ids if _random_string in s]
    assert '(0 tr keys)' in id_line[0]
    account_data = json.loads(ndau(f'account query {_random_string}'))
    assert account_data['validationKeys'] == None
    ndau(f'rfe 10 {_random_string}')
    account_data = json.loads(ndau(f'account query {_random_string}'))
    assert account_data['balance'] == 1000000000
    ndau(f'account claim {_random_string}')
    account_data = json.loads(ndau(f'account query {_random_string}'))
    assert account_data['validationKeys'] != None
    assert account_data['balance'] == 999999999



# def test_set_get(ndau, _random_string):
#     """`ndautool` can set a value and get it back later."""
#     ndau(f'id new {_random_string}')
#     ndau(f'set {_random_string} -k key -v value')
#     v = ndau(f'get {_random_string} -k key -s')
#     assert v == 'value'


# # @pytest.mark.slow
# def test_set_delay_get(ndau, _random_string):
#     """Getting a value doesn't depend on it remaining in memory."""
#     ndau(f'id new {_random_string}')
#     ndau(f'set {_random_string} -k key -v value')
#     sleep(2)
#     v = ndau(f'get {_random_string} -k key -s')
#     assert v == 'value'


# def test_remove(ndau, _random_string):
#     """`ndautool` can remove a value."""
#     ndau(f'id new {_random_string}')
#     ndau(f'set {_random_string} -k key -v value')
#     ndau(f"set {_random_string} -k key -v ''")
#     v = ndau(f'get {_random_string} -k key -s')
#     assert v == ''


# def test_get_ns(ndau):
#     """`ndautool` can list all namespaces."""
#     # set up some namespaces with some data in each
#     num_ns = len(ndau('get-ns').splitlines())
#     nss = ('one', 'two', 'three')
#     for ns in nss:
#         ndau(f'id new {ns}')
#         ndau(f'set {ns} -k key -v value')
#     # wait to ensure that the blockchain is updated
#     sleep(2)

#     # delete a namespace from the local config so we know that we're
#     # reading from the chain, not just echoing local data somehow
#     cp = ndau('conf-path')
#     with open(cp, 'rt') as fp:
#         conf = toml.load(fp)
#     to_remove = nss.index(choice(nss))
#     del conf['identities'][to_remove]
#     with open(cp, 'wt') as fp:
#         toml.dump(conf, fp)

#     # get the namespaces
#     namespaces = ndau('get-ns').splitlines()
#     print(f'namespaces = {namespaces}')
#     assert len(namespaces) == num_ns + len(nss)


# def test_dump(ndau):
#     """`ndautool` can dump all k-v pairs from a given namespace."""
#     # set up a second namespace to ensure we filter out others
#     nss = ('one', 'two')
#     for ns in nss:
#         ndau(f'id new {ns}')
#         ndau(f'set {ns} -k key -v "value {ns}"')
#     ndau('set one -k "another key" -v "another value"')
#     ndau('set one -k "the key" -v "let go"')

#     expected_lines = set((
#         '"key"="value one"',
#         '"another key"="another value"',
#         '"the key"="let go"',
#     ))

#     found_lines = set(ndau('dump one -s').splitlines())

#     assert expected_lines == found_lines


# def test_can_retrieve_values_using_namespace(ndau):
#     """Values can be retrieved given only the namespace and key."""
#     res = ndau('id new temp')
# #    pdb.set_trace()
#     namespace_b64 = res.split()[4]
#     ndau('set temp -k "this key is durable" -v "really"')

#     # get the namespace from the local config, and also delete that key,
#     # so if we want that value back, we _need_ to use the namespace.
#     cp = ndau('conf-path')
#     with open(cp, 'rt') as fp:
#         conf = toml.load(fp)
# #    pdb.set_trace()
# #    t_name = conf['identities'][0]['name']
#     del conf['identities'][0]
#     with open(cp, 'wt') as fp:
#         toml.dump(conf, fp)

# #    val = ndau(f'get --ns="{t_name}" -k "this key is durable" -s')
#     val = ndau(f'get --ns={namespace_b64} -k "this key is durable" -s')
#     assert val == "really"


# def test_cannot_overwrite_others_namespace(ndau):
#     """Users cannot overwrite each others' values."""
#     nss = ('one', 'two')
#     for ns in nss:
#         ndau(f'id new {ns}')
#         ndau(f'set {ns} -k key -v "value {ns}"')
#     for ns in nss:
#         v = ndau(f'get {ns} -k key -s')
#         assert v == f'value {ns}'


# # @pytest.mark.slow
# def test_get_history(ndau):
#     """`ndautool` can list the history of a value."""
#     ndau('id new historic')
#     for i in range(5):
#         ndau(f'set historic -k counter -v {i}')
#         # wait for a few blocks to pass before setting next value
#         sleep(2)
#     history = [
#         line.strip()
#         for line in ndau('history historic -k counter -s').splitlines()
#         if len(line.strip()) > 0 and 'Height' not in line
#     ]
#     assert history == [str(i) for i in reversed(range(5))]


# def test_reject_non_whitelisted_scps(ndau_and_whitelist):
#     """`ndautool` can send a non-whitelisted SCP but it it not accepted."""
#     ndau = ndau_and_whitelist['ndau']
#     whitelist = ndau_and_whitelist['whitelist']

#     key = _random_string()
#     value = _random_string()

#     assert whitelist(f'check {key} -v {value}') == 'false'
#     with pytest.raises(subprocess.CalledProcessError):
#         ndau(f'scp -k {key} -v {value}')

#     sys_val = ndau(f'get --sys -k {key} -s')
#     assert len(sys_val.strip()) == 0


# def test_whitelist_tool_can_whitelist(ndau_and_whitelist):
#     """`ndwhitelist` can whitelist a SCP."""
#     whitelist = ndau_and_whitelist['whitelist']

#     key = _random_string()
#     value = _random_string()

#     print("whitelist path:")
#     path = whitelist('path')
#     print(path)
#     assert whitelist(f'check {key} -v {value}') == 'false'

#     print("adding a k-v pair to whitelist")
#     print(whitelist(f'add {key} -v {value}'))

#     print(f"whitelist exists: {os.path.exists(path)}")

#     with open(path, 'rb') as fp:
#         wl_data = fp.read()
#     print(f"len(wl_data): {len(wl_data)}")
#     wl_data_hex = ''.join(f'{b:02x} ' for b in wl_data)
#     print(f"whitelist as hex: {wl_data_hex}")

#     print(whitelist('list -v'))
#     assert whitelist(f'check {key} -v {value}') == 'true'


# def test_whitelisted_scps_are_accepted(run_kub, ndau_and_whitelist):
#     """`ndautool` can send a whitelisted SCP and it is accepted."""
#     ndau = ndau_and_whitelist['ndau']
#     whitelist = ndau_and_whitelist['whitelist']

#     key = _random_string()
#     value = _random_string()

#     print("adding key and value to whitelist")
#     wl_command = f'add {key} -v {value}'
#     print(f'wl command = {wl_command}')
#     wl_res = whitelist(wl_command)
#     print(f'wl res = {wl_res}')
#     # JSG if run on Kub, just check if the wl command ran successfully
#     # SCP will currently fail with remote nodes
#     if run_kub:
#         wl_res_word = wl_res.split()[0]
#         assert wl_res_word == "Successfully"
#         return

#     print("sending as scp")
#     scp_command = f'scp -k {key} -v {value}'
#     print(f'scp command = {scp_command}')
#     ndau(scp_command)

#     # allow block to finalize
#     sleep(3)

#     print('verifying sys value')
#     actual_val = ndau(f'get --sys -k {key} -s')
#     assert actual_val == value
