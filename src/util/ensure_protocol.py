#  ----- ---- --- -- -
#  Copyright 2020 The Axiom Foundation. All Rights Reserved.
# 
#  Licensed under the Apache License 2.0 (the "License").  You may not use
#  this file except in compliance with the License.  You can obtain a copy
#  in the file LICENSE in the source distribution or at
#  https://www.apache.org/licenses/LICENSE-2.0.txt
#  - -- --- ---- -----

def ensure_protocol(url, suggestion="http"):
    if "http://" in url and suggestion is "https":
        return f"https://{url.strip('http://')}"
    if suggestion not in url:
        return f"{suggestion}://{url}"
    return url
