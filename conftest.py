"""
Define pytest fixtures.

These fixtures configure and run the chaos chain tools.
"""
import json
import os
import re
import subprocess
import time
from tempfile import TemporaryDirectory

import pytest
import toml

from src.conf import load
from src.repo import go_repo, within
from src.subp import subp


def pytest_addoption(parser):
    """See https://docs.pytest.org/en/latest/example/simple.html."""
    parser.addoption("--chaos-go-label", action="store", default="master",
                     help="Label to use for chaos-go")
    parser.addoption("--chaostool-label", action="store", default="master",
                     help="Label to use for chaostool")
    parser.addoption("--whitelist-label", action="store", default="master",
                     help="Label to use for whitelist")


@pytest.fixture(scope='session')
def chaos_go_repo(request):
    """Return the path at which chaos-go is available."""
    label = request.config.getoption('--chaos-go-label')
    conf = load(chaos_go_label=label)['chaos-go']
    with go_repo(conf['repo'], conf['logical'], conf['label']) as path:
        yield path


@pytest.fixture(scope='session')
def chaostool_repo(request):
    """Return the path at which chaostool is available."""
    label = request.config.getoption('--chaostool-label')
    conf = load(chaostool_label=label)['chaostool']
    with go_repo(conf['repo'], conf['logical'], conf['label']) as path:
        yield path


@pytest.fixture(scope='session')
def whitelist_repo(request):
    """Return the path at which whitelist is available."""
    label = request.config.getoption('--whitelist-label')
    conf = load(whitelist_label=label)['whitelist']
    with go_repo(conf['repo'], conf['logical'], conf['label']) as path:
        yield path


@pytest.fixture(scope='session')
def chaos_node_build(chaos_go_repo):
    """
    Build a single chaos node.

    Because chaos nodes are stateful, we need to init/run/reset them for
    every test to ensure that the tests each have clean slates. However,
    we only need to actually build the project once per test session.

    That's what this fixture does.
    """
    build_script = os.path.join(chaos_go_repo, 'bin', 'build.sh')
    try:
        with TemporaryDirectory(prefix='ndauhome-', dir='/tmp') as ndauhome, TemporaryDirectory(prefix='tmhome-', dir='/tmp') as tmhome, within(chaos_go_repo):  # noqa: E501
            try:
                subp(
                    build_script,
                    env={'NDAUHOME': ndauhome, 'TMHOME': tmhome},
                    stderr=subprocess.STDOUT,
                )
            except Exception as e:
                print(e.stdout)
                raise
            yield {
                'repo': chaos_go_repo,
                'ndauhome': ndauhome,
                'tmhome': tmhome,
            }
    except FileNotFoundError:
        # we expect a FileNotFoundError here: the current behavior of reset.sh
        # is to delete $TMHOME and $NDAUHOME. That's fine, though it confuses
        # TemporaryDirectory, which expects to need to clean up after itself.
        # We therefore catch this exception and do nothing about it.
        pass


@pytest.fixture
def chaos_node(chaos_node_build):
    """
    Initialize and run a chaos node for this test.

    Because chaos nodes are stateful, we need to init/run/reset them for
    every test. This fixture accomplishes that.
    """
    def run_cmd(cmd, **kwargs):
        try:
            return subp(
                cmd,
                env=dict(
                    NDAUHOME=chaos_node_build['ndauhome'],
                    TMHOME=chaos_node_build['tmhome'],
                    PATH=os.environ['PATH']
                ),
                stderr=subprocess.STDOUT,
                cwd=chaos_node_build['repo'],
                **kwargs,
            )
        except subprocess.CalledProcessError as e:
            print('--STDOUT--')
            print(e.stdout)
            print('--RETURN CODE--')
            print(e.returncode)

            raise

    # just running init.sh wasn't working, for reasons which were hard to debug
    # we therefore replicate its most important steps here
    print("chaos_node fixture: emulating init.sh")
    run_cmd('docker-compose run --rm --no-deps tendermint init', stdout=None)

    # init: modify config.toml
    tm_config_path = os.path.join(
        chaos_node_build['tmhome'],
        'config', 'config.toml',
    )
    with open(tm_config_path, 'rt') as fp:
        config_toml = toml.load(fp)

    config_toml['proxy_app'] = re.sub(
        r"://[^:]*:",
        "://chaosnode:",
        config_toml['proxy_app'],
        count=1,
    )
    config_toml['consensus']['create_empty_blocks'] = False
    config_toml['consensus']['create_empty_blocks_interval'] = 10

    with open(tm_config_path, 'wt') as fp:
        toml.dump(config_toml, fp)

    # init: edit genesis.json
    empty_hash = run_cmd(
        "docker-compose run --rm --no-deps chaosnode --echo-empty-hash"
    ).strip()
    tm_gj_path = os.path.join(
        chaos_node_build['tmhome'],
        'config', 'genesis.json',
    )
    with open(tm_gj_path, 'rt') as fp:
        genesis_json = json.load(fp)
    genesis_json['app_hash'] = empty_hash
    with open(tm_gj_path, 'wt') as fp:
        json.dump(genesis_json, fp)

    # init: complete
    print("chaos_node fixture: init.sh emulation complete")

    rpc_addr = config_toml['rpc']['laddr']
    _, _, rpc_addr_port = rpc_addr.rpartition(':')
    assert rpc_addr_port != rpc_addr  # we have a port number
    rpc_addr = f'http://localhost:{rpc_addr_port}'

    print("chaos_node fixture: running run.sh")
    # subprocess.run always synchronously waits for the subprocess to terminate
    # that isn't acceptable here, so we fall back to a raw Popen call
    run_script = subprocess.Popen(
        [os.path.join(chaos_node_build['repo'], 'bin', 'run.sh')],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=chaos_node_build['repo'],
        encoding='utf8',
        env=dict(
            NDAUHOME=chaos_node_build['ndauhome'],
            TMHOME=chaos_node_build['tmhome'],
            PATH=os.environ['PATH']
        ),
    )
    # starting tendermint takes a few seconds before it's ready to receive
    # incoming connections
    time.sleep(5)
    run_status = run_script.poll()
    if run_status is not None:
        raise Exception(
            f"run.sh exited unexpectedly with code {run_status}"
        )
    print("chaos_node fixture: run.sh running")

    print("chaos_node fixture: yielding")
    yield {
        **chaos_node_build,
        'rpc_address': rpc_addr,
    }

    print("chaos_node fixture: running reset.sh")
    run_cmd(os.path.join('bin', 'reset.sh'))
    print("chaos_node fixture: reset.sh finished")

    if run_script.poll() is None:
        run_script.terminate()
