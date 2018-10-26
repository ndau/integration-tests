import os
import shutil
import subprocess
from contextlib import contextmanager
from tempfile import mkdtemp
import pdb

from src.subp import subp


@contextmanager
def go_repo(remote, local, label='master'):
    """
    Ensure a go repository exists in the desired branch at the local path.

    `remote` must be a repo spec that git can connect to.
    `local` must be the logical pathname that go expects, i.e. github.com/user/repo
    `label` is a branch, tag, or commit id.

    Returns the full local path to the repository.
    """
    gopath = os.path.expandvars("$GOPATH")
    if len(gopath) == 0:
        raise Exception("$GOPATH not set")
    with repo(
        remote,
        os.path.join(gopath, 'src', local),
        label
    ) as local_path:
        yield local_path


@contextmanager
def repo(remote, local=None, label='master', cleanup=True):
    """
    Ensure a repository exists in the desired branch.

    `remote` must be a repo spec that git can connect to.
    `local` is the local path of a repository. If `None` (the default),
        a temporary directory is allocated and a fresh copy is cloned.
    `label` is a branch, tag, or commit id.
    `cleanup`: if `True` and `local is None`, removes the repo clone.

    Returns the full local path to the repository.
    """
    delete_after = cleanup and local is None
    if local is None:
        local = mkdtemp()
    else:
        local = os.path.abspath(local)
#    pdb.set_trace()
    if not os.path.exists(local):
        os.makedirs(os.path.dirname(local), exist_ok=True)
        subp(f'git clone {remote} {local}')
    elif len(os.listdir(local)) == 0:
        # directory exists but is empty
        os.rmdir(local)
        subp(f'git clone {remote} {local}')
    else:
        # directory exists and is not empty
        # is it a repository?
        try:
            with within(local):
                subp('git status --porcelain')
        except subprocess.CalledProcessError:
            # we can be pretty sure this isn't a repo
            raise Exception(f"'{local}' is not empty and not a git repo")

    try:
        with within(local):
#            pdb.set_trace()
            if len(subp('git status --porcelain')) == 0:
                stashed = False
            else:
                stashed = True
#                subp('git stash push --include-untracked')

            current_branch = subp('git rev-parse --abbrev-ref HEAD')
            if label == current_branch:
                ch_branch = False
            else:
                ch_branch = True
                subp(f'git checkout {label}')

            try:
                yield local
            finally:
                if ch_branch:
                    subp(f'git checkout -f {current_branch}')
                if stashed:
                    try:
#                        pdb.set_trace()
                        stashed = False
                        # subp(
                        #     'git stash pop',
                        #     stderr=subprocess.STDOUT,
                        # )
                    except subprocess.CalledProcessError as e:
                        if 'No stash entries found' in e.stdout:
                            pass
                        else:
                            print(e.stdout)
                            raise
    finally:
        if delete_after:
            shutil.rmtree(local)


@contextmanager
def within(path):
    """Temporarily operate within another directory."""
    current = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(current)
