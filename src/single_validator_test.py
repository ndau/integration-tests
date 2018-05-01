"""Tests that single validator nodes operate as expected."""
import subprocess
from random import choice, choices
from string import ascii_lowercase, digits
from time import sleep

import pytest
import toml
from src.subp import subp


@pytest.fixture
def _random_string(len=16):
    return ''.join(choices(ascii_lowercase+digits, k=len))


@pytest.fixture
def chaos(chaos_node_and_tool):
    """
    Fixture providing a chaos function.

    This function calls the chaos command in a configured environment.
    """
    def rf(cmd, **kwargs):
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
    return rf


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


def test_create_id(chaos, _random_string):
    """First line is always a header."""
    known_ids = chaos('id list').splitlines()[1:]
    assert not any(_random_string in id_line for id_line in known_ids)
    chaos(f'id new {_random_string}')
    new_ids = chaos('id list').splitlines()[1:]
    assert any(_random_string in id_line for id_line in new_ids)


def test_set_get(chaos, _random_string):
    """`chaostool` can set a value and get it back later."""
    chaos(f'id new {_random_string}')
    chaos(f'set {_random_string} -k key -v value')
    v = chaos(f'get {_random_string} -k key -s')
    assert v == 'value'


@pytest.mark.slow
def test_set_delay_get(chaos, _random_string):
    """Getting a value doesn't depend on it remaining in memory."""
    chaos(f'id new {_random_string}')
    chaos(f'set {_random_string} -k key -v value')
    sleep(15)
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
    to_remove = choice(nss)
    del conf['Identities'][to_remove]
    with open(cp, 'wt') as fp:
        toml.dump(conf, fp)

    # get the namespaces
    namespaces = chaos('get-ns').splitlines()
    assert len(namespaces) == len(nss)


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
    chaos('id new temp')
    chaos('set temp -k "this key is durable" -v "really"')

    # get the namespace from the local config, and also delete that key,
    # so if we want that value back, we _need_ to use the namespace.
    cp = chaos('conf-path')
    with open(cp, 'rt') as fp:
        conf = toml.load(fp)
    t_key = conf['Identities']['temp']['PublicKey'].rstrip('=')
    del conf['Identities']['temp']
    with open(cp, 'wt') as fp:
        toml.dump(conf, fp)

    val = chaos(f'get --ns="{t_key}" -k "this key is durable" -s')
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


@pytest.mark.slow
def test_get_history(chaos):
    """`chaostool` can list the history of a value."""
    chaos('id new historic')
    for i in range(5):
        chaos(f'set historic -k counter -v {i}')
        # wait for a few blocks to pass before setting next value
        sleep(3)
    history = [
        line.strip()
        for line in chaos('history historic -k counter -s').splitlines()
        if len(line.strip()) > 0 and 'Height' not in line
    ]
    assert history == [str(i) for i in reversed(range(5))]


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
    print(whitelist('path'))
    assert whitelist(f'check {key} -v {value}') == 'false'

    print("adding a k-v pair to whitelist")
    whitelist(f'add {key} -v {value}')

    print(whitelist('list -v'))
    assert whitelist(f'check {key} -v {value}') == 'true'


def test_whitelisted_scps_are_accepted(chaos_and_whitelist):
    """`chaostool` can send a whitelisted SCP and it is accepted."""
    chaos = chaos_and_whitelist['chaos']
    whitelist = chaos_and_whitelist['whitelist']

    key = _random_string()
    value = _random_string()

    print("adding key and value to whitelist")
    whitelist(f'add {key} -v {value}')

    print("sending as scp")
    chaos(f'scp -k {key} -v {value}')

    # allow block to finalize
    sleep(3)

    print('verifying sys value')
    actual_val = chaos(f'get --sys -k {key} -s')
    assert actual_val == value
