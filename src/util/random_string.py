#  ----- ---- --- -- -
#  Copyright 2020 The Axiom Foundation. All Rights Reserved.
# 
#  Licensed under the Apache License 2.0 (the "License").  You may not use
#  this file except in compliance with the License.  You can obtain a copy
#  in the file LICENSE in the source distribution or at
#  https://www.apache.org/licenses/LICENSE-2.0.txt
#  - -- --- ---- -----

from random import choices
from string import ascii_lowercase, digits


def random_string(prefix="", length=16, **kwargs):
    if len(prefix) > 0:
        # Put a delimiter between the human-readable prefix and the random part.
        prefix += "-"
    return prefix + "".join(choices(ascii_lowercase + digits, k=length))
