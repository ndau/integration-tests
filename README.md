# Integration Tests

## Getting Started

1. Install [python3.6 or later](https://www.python.org/downloads/)
1. Install `pipenv`: `pip3 install pipenv`
1. Install `pytest`: `pip3 install pytest`
1. Install `toml`: `pip3 install toml`
1. Install `msgpack`: `pip3 install msgpack`
1. If you intend to run on non-localnet: set up Kubernetes tools
    1. Install `kubectl`: `brew install kubernetes-cli`
    1. Create the directory `~/.kube`
    1. Get the `deploy_security` tarball from Oneiro's 1password account
        1. Extract it into a temp directory
        1. Copy the files from `kubectl/*` into `~/.kube`
    1. Put the following line in `~/.kube/dev.yaml`, after the existing `- context` sections, and before the `users:` line:
       - `current-context: dev.cluster.ndau.tech`
    1. Add `export KUBECONFIG=~/.kube/dev.yaml` to your `.bash_profile` and restart your Terminal
    1. Test the Kubernetes tools install by running `kubectl get nodes`
1. Make sure you have your `NDAUHOME` environment variable set.  e.g. when running against localnet, you could use `export NDAUHOME=$HOME/.localnet/data/ndau-0`
1. Clone this repo into `~/go/src/github.com/oneiro-ndev` so that it is next to the `ndau` repo
1. `cd` into the repo root
1. Install dependencies: `pipenv sync`
1. Load the environment: `pipenv shell`

## Running the tests

Tests are handled via the `pytest` unit-testing tool. To run the entire test suite, simply execute the `pytest -v` command from the repo root; it'll take care of everything else. If you'd like the testing to stop at failure X, run the command `pytest -v --maxfail=X`.  If you'd like to run a particular test, run the command `pytest test_mod.py::test_func`.  There are several command-line flags available:

- `--runslow` if set runs tests which have been marked as slow. None of these tests are particularly speedy due to the heavy fixtures in play, but some are particularly poky.
- `--skipmeta` if set skips metatests. Metatests are tests which verify that the fixtures in use to fetch and build the various dependencies are all working properly.
- `--keeptemp` if set keeps temp files and directories around to help debug test failures.  Normally all files and directories created during testing will be removed at the end of the tests.  Temporary files will normally be named in the form of /tmp/XXXXXX_YYYYYYYY, where X's are the tool or component name, and Y's are a randomly generated string.
- `--net={devnet|testnet|localnet|...}` instructs the integration tests to run against a remotely running Kubernetes deploy (e.g. `--net=devnet`) vs locally running nodes (`--net=localnet`).  Kubernetes on devnet is the default.  Our integration tests never "build and run" nodes.  Rather, they run tests against already-running nodes.  See documentation in the [commands](https://github.com/oneiro-ndev/commands) repo for how to set up, build and run local nodes.  See the [automation](https://github.com/oneiro-ndev/automation) repo for information regarding Kubernetes setup and deploy.

## Testing Strategy

Tests are written in Python using [pytest](https://docs.pytest.org/en/latest/) and [hypothesis](https://hypothesis.readthedocs.io/en/latest/).
