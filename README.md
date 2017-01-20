##pokeycrawl
###A python web crawler for load-testing and indexing purposes

Pokeycrawl is a Python 2.7 Linux tool allowing the crawling of websites
in order to load test (with multiprocessing) or store a site index.

---
####Installation

Currently unavailable via pip, clone this repo for the current development version

```
# git clone https://github.com/wnormandin/pokeycrawl.git
# cd pokeycrawl
# python setup.py install
```
---
####Usage
```
$python pokeycrawl_2.py -h
usage: pokeycrawl [options] URL

Crawl and index websites. Set default values in config.py

positional arguments:
  url                   The URL to crawl

optional arguments:
  -h, --help            show this help message and exit
  -f, --forms           enable form crawling
  -v, --vary            vary the user-agent using docs/ua.txt
  -d, --debug           enable debug messages and error raising
  -r, --report          display a post-execution summary
  -i, --index           save an index file in tests/URL_EPOCH
  --gz                  accept gzip compression (experimental)
  --robots              process robots.txt directives (experimental)
  --verbose             display verbose HTTP transfer output
  --silent              silence URL crawl notifications
  -l, --logging         enable logging output to file
  -y, --yes             assume "yes" for any prompts
  -t, --test            basic test, does not send requests
  -s SPEED, --speed SPEED
                        set the crawl speed
  --ua UA               specify a user-agent string
  -p PROCS, --procs PROCS
                        max worker threads
  --maxtime MAXTIME     maximum run time in seconds
  --logpath LOGPATH     specify a log path
  --timeout TIMEOUT     request timeout in seconds
```
---
Usage [examples](./EXAMPLES.md)
