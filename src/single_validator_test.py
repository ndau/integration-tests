
import subprocess
from random import choices
from string import ascii_lowercase, digits

import pytest
from src.subp import subp


@pytest.fixture
def random_string(len=16):
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
    # `chaostool` can connect to `chaos-go` and get status
    chaos('info')


def test_create_id(chaos, random_string):
    # first line is always a header
    known_ids = chaos('id list').splitlines()[1:]
    assert not any(random_string in id_line for id_line in known_ids)
    chaos(f'id new {random_string}')
    new_ids = chaos('id list').splitlines()[1:]
    assert any(random_string in id_line for id_line in new_ids)


def test_set_get(chaos, random_string):
    # `chaostool` can set a value and get it back later
    chaos(f'id new {random_string}')
    chaos(f'set {random_string} -k key -v value')
    v = chaos(f'get {random_string} -k key -s')
    assert v == 'value'

# - [ ] `chaostool` can remove a value
# - [ ] `chaostool` can list all namespaces
# - [ ] `chaostool` can dump all k-v pairs from a given namespace
# - [ ] `chaostool` can set a value, and a different instance of `chaostool` can retrieve it
# - [ ] `chaostool` can set a value, and a different instance of `chaostool` cannot overwrite it (i.e. namespaces work)
# - [ ] `chaostool` can list the history of a value
# - [ ] `chaostool` can send a non-whitelisted SCP but it it not accepted
# - [ ] `ndwhitelist` can whitelist a SCP
# - [ ] `chaostool` can send a whitelisted SCP and it is accepted
