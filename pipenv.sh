#!/bin/bash

# Wrapper for pipenv that tells it where to find python3 on your system.

PYTHON=$(which python3)
if [ -z "$PYTHON" ]; then
    echo Unable to find python3 on your system
else
    COMMAND="$1"
    echo Running pipenv "$COMMAND" with "$PYTHON"
    pipenv --python="$PYTHON" "$COMMAND"
fi
