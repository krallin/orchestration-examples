#!/bin/bash
set -o errexit
set -o nounset

# All Scalr Global Variables are passed as Environment Variables.
# Built-in Global Variables have a "SCALR_" prefix.
# We'll display those here
PREFIX="SCALR_"

# This will go to stdout, and will be reported back in the Scalr
# Scripting Logs
printenv | grep --extended-regexp "^${PREFIX}"
