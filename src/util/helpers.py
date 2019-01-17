"""
Helper functions for common tasks that don't need to be pytest fixures.
"""

from random import choices
from string import ascii_lowercase, digits


def random_string(len=16):
    return ''.join(choices(ascii_lowercase+digits, k=len))


def set_up_account(ndau, rfe, account):
    """
    Helper function for creating a new account, rfe'ing to it, claiming it.
    """
    ensure_rfe_account_has_ndau(ndau, ndau_node_exists)
    ndau(f'account new {account}')
    rfe(10, account)
    ndau(f'account claim {account}')


def set_up_namespace(chaos, ns):
    """
    Helper function for creating it as an identity for use as a namespace for key-value pairs.
    """
    res = chaos(f'id new {ns}')
    ns_b64 = res.split()[4]
    chaos(f'id copy-keys-from {ns}')
    return ns_b64
