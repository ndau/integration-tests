"""
Define pytest fixtures.

These fixtures configure and run the chaos chain tools.
"""
import os
import os.path
import subprocess
import time
import tempfile
from tempfile import NamedTemporaryFile, TemporaryDirectory
import pdb
import shutil

import pytest
from src.conf import load
from src.repo import go_repo, within
from src.subp import subp
from pathlib import Path

def pytest_addoption(parser):
    """See https://docs.pytest.org/en/latest/example/simple.html."""
    parser.addoption("--chaos-go-label", action="store", default="master",
                     help="Label to use for chaos-go")
    parser.addoption("--chaostool-label", action="store", default="master",
                     help="Label to use for chaostool")
    parser.addoption("--whitelist-label", action="store", default="master",
                     help="Label to use for whitelist")
    parser.addoption("--ndau-go-label", action="store", default="master",
                     help="Label to use for ndau-go")
    parser.addoption("--ndautool-label", action="store", default="master",
                     help="Label to use for ndautool")
    parser.addoption("--runslow", action="store_true",
                     default=False, help="run slow tests")
    parser.addoption("--skipmeta", action="store_true",
                     default=False, help="skip meta tests")
# JSG add option to keep temp files and dirs if debugging failures
    parser.addoption("--keeptemp", action="store_true",
                     default=False, help="keep temporary files for debugging")
    parser.addoption("--run_kub", action="store_true",
                     default=False, help="keep temporary files for debugging")

@pytest.fixture(scope='session')
def keeptemp(request):
    return request.config.getoption("--keeptemp")

@pytest.fixture(scope='session')
def run_kub(request):
    return request.config.getoption("--run_kub")
    
def pytest_collection_modifyitems(config, items):
    """Pytest func to adjust which tests are run."""
    if not config.getoption("--runslow"):
        skip_slow = pytest.mark.skip(reason="need --runslow option to run")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)
    if config.getoption("--skipmeta"):
        skip_meta = pytest.mark.skip(
            reason="skipped due to --skipmeta option")
        for item in items:
            if "meta" in item.keywords:
                item.add_marker(skip_meta)


@pytest.fixture(scope='session')
def get_ndauhome_dir(keeptemp):
    ndauhome_dir = tempfile.mkdtemp(prefix='ndauhome-', dir='/tmp')
    yield ndauhome_dir
    if not keeptemp:
        shutil.rmtree(ndauhome_dir, True)



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
#    pdb.set_trace()
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
def ndau_go_repo(request):
    """Return the path at which ndau-go is available."""
    label = request.config.getoption('--ndau-go-label')
    conf = load(ndau_go_label=label)['ndau-go']
    with go_repo(conf['repo'], conf['logical'], conf['label']) as path:
        yield path


@pytest.fixture(scope='session')
def ndautool_repo(request):
    """Return the path at which ndautool is available."""
#    pdb.set_trace()
    label = request.config.getoption('--ndautool-label')
    conf = load(ndautool_label=label)['ndautool']
    with go_repo(conf['repo'], conf['logical'], conf['label']) as path:
        yield path


@pytest.fixture(scope='session')
def chaos_node_build(run_kub, chaos_go_repo, get_ndauhome_dir):
    """
    Build a single chaos node.

    Because chaos nodes are stateful, we need to init/run/reset them for
    every test to ensure that the tests each have clean slates. However,
    we only need to actually build the project once per test session.

    That's what this fixture does.
    """
    build_script = os.path.join(chaos_go_repo, 'bin', 'build.sh')
    try:
        # JSG Dont use TemporaryDirectroy as it will always get deleted, mkdtemp will create temp directory but not delete, this will get
        # cleaned up in reset.sh if --keeptemp option is not set
        # with TemporaryDirectory(prefix='ndauhome-', dir='/tmp') as ndauhome, TemporaryDirectory(prefix='tmhome-', dir='/tmp') as tmhome, within(chaos_go_repo):  # noqa: E501
        ndauhome = get_ndauhome_dir
        tmhome = tempfile.mkdtemp(prefix='tmhome-', dir='/tmp')
        print(f'build ndauhome: {ndauhome}')
        print(f'build tmhome: {tmhome}')
        with within(chaos_go_repo):            
            try:
                if not run_kub:
                    subp(
                        build_script,
                        env={'NDAUHOME': ndauhome, 'TMHOME': tmhome, 'PATH': os.environ['PATH']},
                        stderr=subprocess.STDOUT,
                    )
            except Exception as e:
                print(e)
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
def chaos_node_exists(keeptemp):
    """
    Check if we can communicate with chaos node.

    Because chaos nodes are stateful, we need to init/run/reset them for
    every test. This fixture accomplishes that.
    """
    def run_cmd(cmd, **kwargs):
        print(f'cmd: {cmd}')
        try:
#            pdb.set_trace()
            foo = subp(
                cmd,
                env={'KUBECONFIG': os.environ['KUBECONFIG'], 'PATH': os.environ['PATH']},
                stderr=subprocess.STDOUT,
                **kwargs,
            )
            return foo
        except subprocess.CalledProcessError as e:
            print('--STDOUT--')
            print(e.stdout)
            print('--RETURN CODE--')
            print(e.returncode)

            raise

    print("chaos node exists")
    address = run_cmd('kubectl get nodes -o jsonpath=\'{.items[*].status.addresses[?(@.type=="ExternalIP")].address}\' | tr " " "\n" | head -n 1 | tr -d "[:space:]"')
    print(f'address: {address}')
    devnet0_rpc = run_cmd('kubectl get service --namespace default -o jsonpath=\'{.spec.ports[?(@.name=="rpc")].nodePort}\' devnet-0-nodegroup-chaos-tendermint-service')
    devnet1_rpc = run_cmd('kubectl get service --namespace default -o jsonpath=\'{.spec.ports[?(@.name=="rpc")].nodePort}\' devnet-1-nodegroup-chaos-tendermint-service')
    print(f'rpc: {devnet0_rpc}')
    devnet0_res = run_cmd(f'curl -s http://{address}:{devnet0_rpc}/status')
    devnet1_res = run_cmd(f'curl -s http://{address}:{devnet1_rpc}/status')
    print(f'devnet0_res: {devnet0_res}')
    print(f'devnet1_res: {devnet1_res}')
    return {
        'address': address,
        'devnet0_rpc': devnet0_rpc,
        'devnet1_rpc': devnet1_rpc
    }

@pytest.fixture
def chaos_node(keeptemp, run_kub, chaos_node_build):
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
#    pdb.set_trace()
    if not run_kub:
        print("chaos_node fixture: running init.sh")
        print(f'init.sh: {os.path.join("bin", "init.sh")}')
        print(f'cwd: {chaos_node_build["repo"]}')
        print(f'ndauhome: {chaos_node_build["ndauhome"]}')
        print(f'tmhome: {chaos_node_build["tmhome"]}')
        run_cmd(os.path.join('bin', 'init.sh'))
        print("chaos_node fixture: init.sh finished")

        print("chaos_node fixture: running run.sh")
        print(f'run.sh: {[os.path.join(chaos_node_build["repo"], "bin", "run.sh")]}')
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
        # incoming connections. Therefore, just keep delaying until it succeeds,
        # up to one minute.
        upcheck_interval = 2
        for attempt in range(0, 60, upcheck_interval):
            run_status = run_script.poll()
            if run_status is not None:
                raise Exception(
                    f"run.sh exited unexpectedly with code {run_status}"
                )
            print(f'Attempt to start chaos node @ {attempt}s:')
            try:
                # JSG change port to current default TM port: 26657
                address = run_cmd('docker-compose port tendermint 26657')
                run_cmd(f'curl -s {address}/status')
            except subprocess.CalledProcessError as e:
                pass
            else:
                break

            time.sleep(upcheck_interval)

        print("chaos_node fixture: run.sh running")

        print("chaos_node fixture: yielding")
    try:
        yield chaos_node_build
    finally:
        if not keeptemp and not run_kub:
            print("chaos_node fixture: running reset.sh")
            # JSG only run reset.sh if keeptemp is false
            run_cmd(os.path.join('bin', 'reset.sh'))
            print("chaos_node fixture: reset.sh finished")

        if not run_kub:
            if run_script.poll() is None:
                run_script.terminate()

@pytest.fixture(scope='session')
def ndau_node_build(run_kub, ndau_go_repo, get_ndauhome_dir):
    """
    Build a single ndau node.

    Because ndau nodes are stateful, we need to init/run/reset them for
    every test to ensure that the tests each have clean slates. However,
    we only need to actually build the project once per test session.

    That's what this fixture does.
    """
    build_script = os.path.join(ndau_go_repo, 'bin', 'build.sh')
    try:
        # JSG Dont use TemporaryDirectroy as it will always get deleted, mkdtemp will create temp directory but not delete, this will get
        # cleaned up in reset.sh if --keeptemp option is not set
        # with TemporaryDirectory(prefix='ndauhome-', dir='/tmp') as ndauhome, TemporaryDirectory(prefix='tmhome-', dir='/tmp') as tmhome, within(ndau_go_repo):  # noqa: E501
        ndauhome = get_ndauhome_dir
        tmhome = tempfile.mkdtemp(prefix='tmhome-', dir='/tmp')
        print(f'build ndauhome: {ndauhome}')
        print(f'build tmhome: {tmhome}')
        with within(ndau_go_repo):            
            try:
                if not run_kub:
                    subp(
                        build_script,
                        env={'NDAUHOME': ndauhome, 'TMHOME': tmhome, 'PATH': os.environ['PATH']},
                        stderr=subprocess.STDOUT,
                    )
            except Exception as e:
                print(e)
                raise
            yield {
                'repo': ndau_go_repo,
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
def ndau_node_exists(keeptemp):
    """
    Check if we can communicate with ndau node.

    Because ndau nodes are stateful, we need to init/run/reset them for
    every test. This fixture accomplishes that.
    """
    def run_cmd(cmd, **kwargs):
        print(f'cmd: {cmd}')
        try:
#            pdb.set_trace()
            foo = subp(
                cmd,
                env={'KUBECONFIG': os.environ['KUBECONFIG'], 'PATH': os.environ['PATH']},
                stderr=subprocess.STDOUT,
                **kwargs,
            )
            return foo
        except subprocess.CalledProcessError as e:
            print('--STDOUT--')
            print(e.stdout)
            print('--RETURN CODE--')
            print(e.returncode)

            raise

    print("ndau node exists")
    address = run_cmd('kubectl get nodes -o jsonpath=\'{.items[*].status.addresses[?(@.type=="ExternalIP")].address}\' | tr " " "\n" | head -n 1 | tr -d "[:space:]"')
    print(f'address: {address}')
    devnet0_rpc = run_cmd('kubectl get service --namespace default -o jsonpath=\'{.spec.ports[?(@.name=="rpc")].nodePort}\' devnet-0-nodegroup-ndau-tendermint-service')
    devnet1_rpc = run_cmd('kubectl get service --namespace default -o jsonpath=\'{.spec.ports[?(@.name=="rpc")].nodePort}\' devnet-1-nodegroup-ndau-tendermint-service')
    print(f'rpc: {devnet0_rpc}')
    devnet0_res = run_cmd(f'curl -s http://{address}:{devnet0_rpc}/status')
    devnet1_res = run_cmd(f'curl -s http://{address}:{devnet1_rpc}/status')
    print(f'devnet0_res: {devnet0_res}')
    print(f'devnet1_res: {devnet1_res}')
    return {
        'address': address,
        'devnet0_rpc': devnet0_rpc,
        'devnet1_rpc': devnet1_rpc
    }

@pytest.fixture
def ndau_node(keeptemp, run_kub, ndau_node_build):
    """
    Initialize and run a ndau node for this test.

    Because ndau nodes are stateful, we need to init/run/reset them for
    every test. This fixture accomplishes that.
    """
    def run_cmd(cmd, **kwargs):
        try:
            return subp(
                cmd,
                env=dict(
                    NDAUHOME=ndau_node_build['ndauhome'],
                    TMHOME=ndau_node_build['tmhome'],
                    PATH=os.environ['PATH']
                ),
                stderr=subprocess.STDOUT,
                cwd=ndau_node_build['repo'],
                **kwargs,
            )
        except subprocess.CalledProcessError as e:
            print('--STDOUT--')
            print(e.stdout)
            print('--RETURN CODE--')
            print(e.returncode)

            raise
#    pdb.set_trace()
    if not run_kub:
        print("ndau_node fixture: running init.sh")
        print(f'init.sh: {os.path.join("bin", "init.sh")}')
        print(f'cwd: {ndau_node_build["repo"]}')
        print(f'ndauhome: {ndau_node_build["ndauhome"]}')
        print(f'tmhome: {ndau_node_build["tmhome"]}')
        run_cmd(os.path.join('bin', 'init.sh'))
        print("ndau_node fixture: init.sh finished")

        print("ndau_node fixture: running run.sh")
        print(f'run.sh: {[os.path.join(ndau_node_build["repo"], "bin", "run.sh")]}')
        # subprocess.run always synchronously waits for the subprocess to terminate
        # that isn't acceptable here, so we fall back to a raw Popen call
        run_script = subprocess.Popen(
            [os.path.join(ndau_node_build['repo'], 'bin', 'run.sh')],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=ndau_node_build['repo'],
            encoding='utf8',
            env=dict(
                NDAUHOME=ndau_node_build['ndauhome'],
                TMHOME=ndau_node_build['tmhome'],
                PATH=os.environ['PATH']
            ),
        )
        # starting tendermint takes a few seconds before it's ready to receive
        # incoming connections. Therefore, just keep delaying until it succeeds,
        # up to one minute.
        upcheck_interval = 2
        for attempt in range(0, 60, upcheck_interval):
            run_status = run_script.poll()
            if run_status is not None:
                raise Exception(
                    f"run.sh exited unexpectedly with code {run_status}"
                )
            print(f'Attempt to start ndau node @ {attempt}s:')
            try:
                # JSG change port to current default TM port: 26657
                address = run_cmd('docker-compose port tendermint 26657')
                run_cmd(f'curl -s {address}/status')
            except subprocess.CalledProcessError as e:
                pass
            else:
                break

            time.sleep(upcheck_interval)

        print("ndau_node fixture: run.sh running")

        print("ndau_node fixture: yielding")
    try:
        yield ndau_node_build
    finally:
        if not keeptemp and not run_kub:
            print("ndau_node fixture: running reset.sh")
            # JSG only run reset.sh if keeptemp is false
            pdb.set_trace()
            run_cmd(os.path.join('bin', 'reset.sh'))
            print("ndau_node fixture: reset.sh finished")

        if not run_kub:
            if run_script.poll() is None:
                run_script.terminate()


def run_localenv(cmd):
    """Run a command in the local environment."""
    try:
        return subp(
            cmd,
            stderr=subprocess.STDOUT,
            env=os.environ,
        )
    except subprocess.CalledProcessError as e:
        print(e.stdout)
        raise


@pytest.fixture(scope='session')
def chaostool_build(keeptemp, chaostool_repo):
    """
    Build the chaos tool.

    Note that this doesn't perform any configuration;
    it just builds the binary.
    """
    with within(chaostool_repo):
        run_localenv('dep ensure')
        with NamedTemporaryFile(prefix='chaostool-', dir='/tmp', delete=not keeptemp) as bin_fp:
            run_localenv(f'go build -o {bin_fp.name} ./cmd/chaos')
            yield {
                'repo': chaostool_repo,
                'bin': bin_fp.name,
            }

@pytest.fixture(scope='session')
def whitelist_build(keeptemp, whitelist_repo):
    """
    Build the ndwhitelist binary.

    Note that this doesn't perform any configuration,
    it just builds the binary.
    """
    with within(whitelist_repo):
        run_localenv('dep ensure')
        with NamedTemporaryFile(prefix='whitelist-', dir='/tmp', delete=not keeptemp) as bin_fp:
            run_localenv(f'go build -o {bin_fp.name} ./cmd/ndwhitelist')
            yield {
                'repo': whitelist_repo,
                'bin': bin_fp.name,
            }

@pytest.fixture(scope='session')
def ndautool_build(keeptemp, ndautool_repo):
    """
    Build the ndau tool.

    Note that this doesn't perform any configuration;
    it just builds the binary.
    """
    with within(ndautool_repo):
        run_localenv('dep ensure')
        with NamedTemporaryFile(prefix='ndautool-', dir='/tmp', delete=not keeptemp) as bin_fp:
            run_localenv(f'go build -o {bin_fp.name} ./cmd/ndau')
            yield {
                'repo': ndautool_repo,
                'bin': bin_fp.name,
            }

@pytest.fixture
def chaos_node_and_tool(run_kub, chaos_node, chaostool_build, chaos_node_exists):
    """
    Run a chaos node, and configure the chaos tool to connect to it.

    This necessarily includes the chaos node; depend only on this fixture,
    not on this plus chaos_node.
    """
    env = {
        'TMHOME': chaos_node['tmhome'],
        'NDAUHOME': chaos_node['ndauhome'],
        'PATH': os.environ['PATH'],
    }

    if run_kub:
        address = 'http://' + chaos_node_exists['address'] + ':' + chaos_node_exists['devnet0_rpc']
    else:
        with within(chaos_node['repo']):
            address = subp(
                # JSG change port to current default TM port: 26657
                'docker-compose port tendermint 26657',
                env=env,
                stderr=subprocess.STDOUT,
            )

        if '://' not in address:
            address = 'http://' + address
    subp(
        f'{chaostool_build["bin"]} conf {address}',
        env=env,
    )
#    pdb.set_trace()
    return {
        'node': chaos_node,
        'tool': chaostool_build,
        'env': env,
    }

@pytest.fixture
def ndau_node_and_tool(run_kub, ndau_node, ndautool_build, ndau_node_exists):
    """
    Run a ndau node, and configure the ndau tool to connect to it.

    This necessarily includes the ndau node; depend only on this fixture,
    not on this plus ndau_node.
    """
    env = {
        'TMHOME': ndau_node['tmhome'],
        'NDAUHOME': ndau_node['ndauhome'],
        'PATH': os.environ['PATH'],
    }

    if run_kub:
        address = 'http://' + ndau_node_exists['address'] + ':' + ndau_node_exists['devnet0_rpc']
    else:
        with within(ndau_node['repo']):
            address = subp(
                # JSG change port to current default TM port: 26657
                'docker-compose port tendermint 26657',
                env=env,
                stderr=subprocess.STDOUT,
            )

        if '://' not in address:
            address = 'http://' + address
    pdb.set_trace()
    conf_path = subp(
        f'{ndautool_build["bin"]} conf-path',
        env=env)
    
    if not os.path.isfile(conf_path):     
        subp(
            f'{ndautool_build["bin"]} conf {address}',
            env=env,
        )
#    pdb.set_trace()
    return {
        'node': ndau_node,
        'tool': ndautool_build,
        'env': env,
    }


@pytest.fixture
def chaos_node_two_validator_build(chaos_go_repo):
    """
    Build a network containing two chaos nodes.

    Because chaos nodes are stateful, we need to init/run/reset them for
    every test to ensure that the tests each have clean slates. However,
    we only need to actually build the project once per test session.

    That's what this fixture does.
    """
    pypath = os.path.join(chaos_go_repo, 'py')

    def gen_nodes(cmd, **kwargs):
        try:
            return subp(
                # JSG run pipenv install to import modules needed by gen_nodes.py
                f'pipenv install; pipenv run ./gen_nodes.py {cmd}',
                stderr=subprocess.STDOUT,
                env={
                    'LC_ALL': 'en_US.UTF-8',
                    'LANG': 'en_US.UTF-8',
                    'PATH': os.environ['PATH'],
                },
                cwd=pypath,
            )
        except Exception as e:
            print(e.stdout)
            raise

    with TemporaryDirectory(prefix='multinode-', dir='/tmp') as mnhome:
        script_dir = os.path.join(mnhome, 'scripts')
        gen_nodes(f'2 --home {mnhome} --output {script_dir}')
        yield {
            'repo': chaos_go_repo,
            'multinode': mnhome,
            'scripts': script_dir,
            'gen_nodes': gen_nodes,
        }


@pytest.fixture
def chaos_node_two_validator(chaos_node_two_validator_build):
    """
    Initialize and run a two node chaos network for this test.

    Because chaos nodes are stateful, we need to init/run/reset them for
    every test. This fixture accomplishes that.
    """
    def run_cmd(cmd, **kwargs):
        try:
            return subp(
                cmd,
                stderr=subprocess.STDOUT,
                cwd=chaos_node_two_validator_build['repo'],
                **kwargs,
            )
        except subprocess.CalledProcessError as e:
            print('--STDOUT--')
            print(e.stdout)
            raise

    print("chaos_node_two_validator fixture: running run_many.sh")
    # subprocess.run always synchronously waits for the subprocess to terminate
    # that isn't acceptable here, so we fall back to a raw Popen call
    print(f'run_many command: {[os.path.join(chaos_node_two_validator_build["scripts"], "run_many.sh",)]}')
    run_script = subprocess.Popen(
        [os.path.join(
            chaos_node_two_validator_build['scripts'],
            'run_many.sh',
        )],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=chaos_node_two_validator_build['repo'],
        encoding='utf8',
    )

    # starting tendermint takes a few seconds before it's ready to receive
    # incoming connections. Therefore, just keep delaying until it succeeds,
    # up to one minute.
    address = chaos_node_two_validator_build['gen_nodes'](
        '2 --rpc-address | head -n 1'
    )
    upcheck_interval = 2
    for attempt in range(0, 60, upcheck_interval):
        run_status = run_script.poll()
        if run_status is not None:
            raise Exception(
                f"run_many.sh exited unexpectedly with code {run_status}"
            )
        print(f'Attempt to start chaos node @ {attempt}s:')
        try:
            run_cmd(f'curl -s {address}/status')
        except subprocess.CalledProcessError as e:
            pass
        else:
            break

        time.sleep(upcheck_interval)

    print("chaos_node_two_validator fixture: run_many.sh running")

    print("chaos_node_two_validator fixture: yielding")
    try:
        yield dict(
            **chaos_node_two_validator_build,
            run=run_cmd
        )
    finally:
        print("chaos_node_two_validator fixture: running stop_many.sh")
        run_cmd(os.path.join(
            chaos_node_two_validator_build['scripts'],
            'stop_many.sh',
        ))
        print("chaos_node_two_validator fixture: stop_many.sh finished")

        if run_script.poll() is None:
            run_script.terminate()


@pytest.fixture
def two_chaos_nodes_and_tool(chaos_node_two_validator, chaostool_build):
    """
    Run a pair of chaos nodes, and configure the chaos tool to connect to it.

    For simplicity, the 'chaos' function returned here is configured to connect
    only to the first node, but enough information is provided that it should
    be simple to write a subfixture connecting to a different node.
    """
    ndauhomes = chaos_node_two_validator['run'](
        f'find {chaos_node_two_validator["multinode"]}'
        ' -type d -name ndau -print'
    ).splitlines()

    env = {
        'PATH': os.environ['PATH'],
        'NDAUHOME': ndauhomes[0],
    }

    print('ndauhome:', env['NDAUHOME'])

    gen_nodes = chaos_node_two_validator['gen_nodes']
    address = gen_nodes('2 --rpc-address').splitlines()[0]

    if '://' not in address:
        address = 'http://' + address

    subp(
        f'{chaostool_build["bin"]} conf {address}',
        env=env,
    )

    def chaos(cmd, **kwargs):
        try:
            return subp(
                f'{chaostool_build["bin"]} {cmd}',
                env=env,
                stderr=subprocess.STDOUT,
                **kwargs,
            )
        except subprocess.CalledProcessError as e:
            print(e.stdout)
            raise

    return {
        'node': chaos_node_two_validator,
        'tool': chaostool_build,
        'env': env,
        'chaos': chaos,
    }

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
#    pdb.set_trace()
    return rf

