"""
Define pytest fixtures
"""
import os
from tempfile import TemporaryDirectory

import pytest
import toml
from src.conf import load
from src.repo import go_repo, within
from src.subp import subp


def pytest_addoption(parser):
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
    with TemporaryDirectory(prefix='ndauhome') as ndauhome, TemporaryDirectory(prefix='tmhome') as tmhome:
        subp(build_script, env={'NDAUHOME': ndauhome, 'TMHOME': tmhome})
        yield {
            'repo': chaos_go_repo,
            'ndauhome': ndauhome,
            'tmhome': tmhome,
        }


@pytest.fixture
def chaos_node(chaos_node_build):
    """
    Initialize and run a chaos node for this test.

    Because chaos nodes are stateful, we need to init/run/reset them for
    every test. This fixture accomplishes that.
    """
    init_script = os.path.join(chaos_node_build['repo'], 'bin', 'init.sh')
    run_script = os.path.join(chaos_node_build['repo'], 'bin', 'run.sh')
    reset_script = os.path.join(chaos_node_build['repo'], 'bin', 'reset.sh')

    ndauhome = chaos_node_build['ndauhome']
    tmhome = chaos_node_build['tmhome']

    subp(init_script, env={'NDAUHOME': ndauhome, 'TMHOME': tmhome})

    tm_config_path = os.path.join(tmhome, 'config', 'config.toml')
    with open(tm_config_path, 'rt') as fp:
        rpc_addr = toml.load(fp)['rpc']['laddr']
    _, _, rpc_addr_port = rpc_addr.rpartition(':')
    assert rpc_addr_port != rpc_addr  # we have a port number
    rpc_addr = f'localhost:{rpc_addr_port}'

    subp(run_script, env={'NDAUHOME': ndauhome, 'TMHOME': tmhome})

    yield {
        **chaos_node_build,
        'rpc_address': rpc_addr,
    }

    subp(reset_script, env={'NDAUHOME': ndauhome, 'TMHOME': tmhome})
