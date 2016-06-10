#!/bin/bash

# Base the output path on this utility's source directory
# so that straces are in /tests/
fname="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && cd ../tests && pwd )/pokeycrawl_strace_$(date +%s)"

# Loop until a process spawns for the crawler
while true; do 
    pid=$(pgrep -f 'python.pokeycrawl' | head -1)
    # strace that process and save output
    [[ -n "$pid" ]] && strace -o $fname -p "$pid" && break
done
