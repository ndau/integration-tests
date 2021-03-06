#  ----- ---- --- -- -
#  Copyright 2020 The Axiom Foundation. All Rights Reserved.
# 
#  Licensed under the Apache License 2.0 (the "License").  You may not use
#  this file except in compliance with the License.  You can obtain a copy
#  in the file LICENSE in the source distribution or at
#  https://www.apache.org/licenses/LICENSE-2.0.txt
#  - -- --- ---- -----

"""Define a subprocess shortcut."""

import os
import subprocess


def ndenv(*extras):
    """
    Copy certain environment variables from the surrounding environment to pass
    into the subcommand.

    By default, it copies "PATH", "HOME", "TMHOME", and "NDAUHOME".
    If any more are desired, just pass in their names as string arguments.
    """
    env = {}
    for var in ("PATH", "HOME", "TMHOME", "NDAUHOME") + extras:
        if os.environ.get(var) is not None:
            env[var] = os.environ[var]
    return env


def subp(
    cmd,
    *,
    stdout=subprocess.PIPE,
    stderr=subprocess.DEVNULL,
    timeout=None,
    env={},
    **kwargs,
):
    """
    Run a command, ensure its return code was 0, and return its output.

    `stderr` is passed through to the subprocess.run command.
    `timeout` is passed through to the subprocess.run command.

    This uses `shell=True` to simplify inputs, but this means that this
    _must not_ be used with user input; that's just not safe.
    """
    subr = subprocess.run(
        cmd,
        shell=True,
        stdout=stdout,
        stderr=stderr,
        timeout=timeout,
        encoding="utf8",
        env=env,
        **kwargs,
    )
    subr.check_returncode()
    if stdout == subprocess.PIPE:
        return subr.stdout.strip()


def subpv(cmd, **kwargs):
    try:
        return subp(cmd, stderr=subprocess.STDOUT, **kwargs)
    except subprocess.CalledProcessError as e:
        print("--CMD--")
        print(cmd)
        print("--RETURN CODE--")
        print(e.returncode)
        print("--STDOUT--")
        print(e.stdout)
        print("--STDERR--")
        print(e.stderr)

        raise
