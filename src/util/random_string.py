from random import choices
from string import ascii_lowercase, digits


def random_string(prefix="", length=16, **kwargs):
    if len(prefix) > 0:
        # Put a delimiter between the human-readable prefix and the random part.
        prefix += "-"
    return prefix + "".join(choices(ascii_lowercase + digits, k=length))
