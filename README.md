# Integration Tests

## Overview

Integration tests can be run against a running localnet.  They are also run automatically from a Circle CI job called `integration` when a branch lands to the `commands` repo master branch.  The Circle CI job can also be run using tagged builds from a branch.  Details on how to do that can be found inside the `./circle/config.yml` file in the `commands` repo.

## Getting Started

1. Install [python3.6 or later](https://www.python.org/downloads/)
1. Install `pipenv`: `pip3 install pipenv`
1. Install `pytest`: `pip3 install pytest`
1. Install `toml`: `pip3 install toml`
1. Install `msgpack`: `pip3 install msgpack`
1. Make sure you have your `NDAUHOME` environment variable set.  e.g. when running against localnet, you could use `export NDAUHOME=$HOME/.localnet/data/ndau-0`
1. Clone this repo into `~/go/src/github.com/ndau` so that it is next to the `ndau` repo
1. `cd` into the repo root
1. Install dependencies: `pipenv sync`
1. Load the environment: `pipenv shell`

## Running the tests

Tests are handled via the `pytest` unit-testing tool. To run the entire test suite, simply execute the `pytest -v` command from the repo root; it'll take care of everything else. If you'd like the testing to stop at failure X, run the command `pytest -v --maxfail=X`.  If you'd like to run a particular test, run the command `pytest test_mod.py::test_func`.  There are several command-line flags available:

- `--runslow` if set runs tests which have been marked as slow. None of these tests are particularly speedy due to the heavy fixtures in play, but some are particularly poky.
- `--skipmeta` if set skips metatests. Metatests are tests which verify that the fixtures in use to fetch and build the various dependencies are all working properly.
- `--keeptemp` if set keeps temp files and directories around to help debug test failures.  Normally all files and directories created during testing will be removed at the end of the tests.  Temporary files will normally be named in the form of /tmp/XXXXXX_YYYYYYYY, where X's are the tool or component name, and Y's are a randomly generated string.
- `--ip` set to the IP of the `localnet-0` node.  If omitted, it defaults to `localhost`.  This is used by the integration tests to send requests to the network.  Only one node is needed for integration tests to run against.

## Testing Strategy

Tests are written in Python using [pytest](https://docs.pytest.org/en/latest/) and [hypothesis](https://hypothesis.readthedocs.io/en/latest/).

## Supported Networks

There is no support for running integration tests against non-local networks.

Rationale:

* We can be sure to start with the latest "generated" genesis snapshot automatically
    - We don't rely on any pre-built snapshot hosted on S3
* Tests can be written to rely on a known initial state
    - Tests don't have to worry about being compatible with "whatever's on devnet" when they run
    - On localnet, this is achieved by running `bin/reset.sh` from the `commands` repo
    - On Circle CI, the `integration` job starts the test nodes with a fresh genesis snapshot
* It avoids inflating ndau issuance beyond realistic values
    - Anyone testing the wallet against devnet won't be affected
* The integration tests can be run from Circle CI before we push and deploy a build to devnet
    - If the tests fail, the push and deploy are skipped
