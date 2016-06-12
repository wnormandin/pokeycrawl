#!/bin/bash

# Deletes the contents of the tests/ directory with the exception of tests.txt
cd "$( dirname "${BASH_SOURCE[0]}" )" && cd ../tests && pwd 
find . -type f -iname "*.idx" -delete -print
