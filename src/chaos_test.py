"""Tests that the chaos blockchain operates as expected."""

import os
import subprocess
from time import sleep

import pytest
import json

from src.util.subp import subp


def test_get_chaos_status(node_net, chaos):
    """`chaostool` can connect to `chaos-go` and get status."""
    info = json.loads(chaos("info"))
    moniker = info["node_info"]["moniker"]
    assert moniker == f"{node_net}-0"


def test_create_id(chaos, random_string, set_up_account, set_up_namespace):
    """First line is always a header."""
    _random_string = random_string()
    known_ids = chaos("id list").splitlines()[1:]
    assert not any(_random_string in id_line for id_line in known_ids)
    set_up_account(_random_string)
    set_up_namespace(_random_string)
    new_ids = chaos("id list").splitlines()[1:]
    assert any(_random_string in id_line for id_line in new_ids)


def test_set_get(chaos, ndau, random_string, set_up_account, set_up_namespace):
    """`chaostool` can set a value and get it back later."""
    _random_string = random_string("set-get")
    conf_path = ndau("conf-path")
    f = open(conf_path, "r")
    conf_lines = f.readlines()
    f.close()
    print(conf_lines)
    set_up_account(_random_string)
    set_up_namespace(_random_string)
    chaos(f"set {_random_string} key value")
    v = chaos(f"get {_random_string} key -s")
    assert v == "value"


# @pytest.mark.slow
def test_set_delay_get(chaos, random_string, set_up_account, set_up_namespace):
    """Getting a value doesn't depend on it remaining in memory."""
    _random_string = random_string()
    set_up_account(_random_string)
    set_up_namespace(_random_string)
    chaos(f"set {_random_string} key value")
    sleep(2)
    v = chaos(f"get {_random_string} key -s")
    assert v == "value"


def test_remove(chaos, random_string, set_up_account, set_up_namespace):
    """`chaostool` can remove a value."""
    _random_string = random_string()
    set_up_account(_random_string)
    set_up_namespace(_random_string)
    chaos(f"set {_random_string} key value")
    chaos(f"set {_random_string} key --value-file=/dev/null")
    v = chaos(f"get {_random_string} key -s")
    assert v == ""


def test_get_ns(
    chaos, chaos_namespace_query, ndau_account_query, set_up_account, set_up_namespace
):
    """`chaostool` can list all namespaces."""
    # set up some namespaces with some data in each
    num_ns = len(chaos("get-ns").splitlines())
    nss = ("one", "two", "three")
    for ns in nss:
        if ndau_account_query(ns) == "No such named account":
            set_up_account(ns)
        if chaos_namespace_query(ns) == f"getting namespace: no such identity: {ns}":
            set_up_namespace(ns)
        else:
            num_ns -= 1
        chaos(f"set {ns} key value")
    # wait to ensure that the blockchain is updated
    sleep(2)

    # get the namespaces
    namespaces = chaos("get-ns").splitlines()
    print(f"namespaces = {namespaces}")
    assert len(namespaces) == num_ns + len(nss)


def test_dump(
    chaos, chaos_namespace_query, ndau_account_query, set_up_account, set_up_namespace
):
    """`chaostool` can dump all k-v pairs from a given namespace."""
    # set up a second namespace to ensure we filter out others
    nss = ("one", "two")
    for ns in nss:
        if ndau_account_query(ns) == "No such named account":
            set_up_account(ns)
        if chaos_namespace_query(ns) == f"getting namespace: no such identity: {ns}":
            set_up_namespace(ns)
        chaos(f'set {ns} key "value {ns}"')
    chaos('set one "another key" "another value"')
    chaos('set one "the key" "let go"')

    expected_lines = set(
        ('"key"="value one"', '"another key"="another value"', '"the key"="let go"')
    )

    found_lines = set(chaos("dump one -s").splitlines())

    assert expected_lines == found_lines


def test_can_retrieve_values_using_namespace(
    chaos, random_string, set_up_account, set_up_namespace
):
    """Values can be retrieved given only the namespace and key."""
    temp = random_string()
    set_up_account(temp)
    namespace_b64 = set_up_namespace(temp)
    chaos(f'set {temp} "this key is durable" "really"')

    val = chaos(f'get --ns={namespace_b64} "this key is durable" -s')
    assert val == "really"


def test_cannot_overwrite_others_namespace(
    chaos, chaos_namespace_query, ndau_account_query, set_up_account, set_up_namespace
):
    """Users cannot overwrite each others' values."""
    nss = ("one", "two")
    for ns in nss:
        if ndau_account_query(ns) == "No such named account":
            set_up_account(ns)
        if chaos_namespace_query(ns) == f"getting namespace: no such identity: {ns}":
            set_up_namespace(ns)
        chaos(f'set {ns} key "value {ns}"')
    for ns in nss:
        v = chaos(f"get {ns} key -s")
        assert v == f"value {ns}"


# @pytest.mark.slow
def test_get_history(chaos, random_string, set_up_account, set_up_namespace):
    """`chaostool` can list the history of a value."""
    historic = random_string()
    set_up_account(historic)
    set_up_namespace(historic)
    for i in range(5):
        chaos(f"set {historic} counter {i}")
        # wait for a few blocks to pass before setting next value
        sleep(2)
    history = [
        line.strip()
        for line in chaos(f"history {historic} counter -s").splitlines()
        if len(line.strip()) > 0 and "Height" not in line
    ]
    assert history == [str(i) for i in range(5)]
