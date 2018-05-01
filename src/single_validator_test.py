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


def test_get_status(chaos):
    """`chaostool` can connect to `chaos-go` and get status."""
    chaos('info')


def test_create_id(chaos, random_string):
    """First line is always a header."""
    known_ids = chaos('id list').splitlines()[1:]
    assert not any(random_string in id_line for id_line in known_ids)
    chaos(f'id new {random_string}')
    new_ids = chaos('id list').splitlines()[1:]
    assert any(random_string in id_line for id_line in new_ids)


def test_set_get(chaos, random_string):
    """`chaostool` can set a value and get it back later."""
    chaos(f'id new {random_string}')
    chaos(f'set {random_string} -k key -v value')
    v = chaos(f'get {random_string} -k key -s')
    assert v == 'value'


@pytest.mark.slow
def test_set_delay_get(chaos, random_string):
    """Getting a value doesn't depend on it remaining in memory."""
    chaos(f'id new {random_string}')
    chaos(f'set {random_string} -k key -v value')
    sleep(15)
    v = chaos(f'get {random_string} -k key -s')
    assert v == 'value'


def test_remove(chaos, random_string):
    """`chaostool` can remove a value."""
    chaos(f'id new {random_string}')
    chaos(f'set {random_string} -k key -v value')
    chaos(f"set {random_string} -k key -v ''")
    v = chaos(f'get {random_string} -k key -s')
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


# - [ ] `chaostool` can list the history of a value
# - [ ] `chaostool` can send a non-whitelisted SCP but it it not accepted
# - [ ] `ndwhitelist` can whitelist a SCP
# - [ ] `chaostool` can send a whitelisted SCP and it is accepted
