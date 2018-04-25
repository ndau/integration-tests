import subprocess


def subp(cmd, *, stderr=subprocess.DEVNULL, timeout=None):
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
        stdout=subprocess.PIPE,
        stderr=stderr,
        timeout=timeout,
        encoding='utf8',
    )
    subr.check_returncode()
    return subr.stdout.strip()
