"""Define a subprocess shortcut."""

import subprocess


def subp(
    cmd, *,
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
        encoding='utf8',
        env=env,
        **kwargs,
    )
    subr.check_returncode()
    if stdout == subprocess.PIPE:
        return subr.stdout.strip()
