##pokeycrawl
###A python web crawler for load-testing and indexing purposes

Pokeycrawl is a Python 2.7 Linux tool allowing the crawling of websites
in order to load test (with multiprocessing) or store a site index.

---
####Installation

```
# pip install pokeycrawl
```
or

```
# git clone https://github.com/wnormandin/pokeycrawl.git
# cd pokeycrawl
# python setup.py install
```
---
####Usage

```
$ python pokeycrawl.py --help
usage: pokeycrawl.py [-h] [-s SPEED] [-v] [-d] [-p PROCS] [-r] [-i] [--ua UA]
                     [--gz] [--robots] [--maxtime MAXTIME] [--verbose]
                     [--silent]
                     url

positional arguments:
  url                   The URL to crawl

optional arguments:
  -h, --help            show this help message and exit
  -s SPEED, --speed SPEED
                        set the crawl speed (defaults to 0.25s)
  -v, --vary            vary the user-agent
  -d, --debug           enable debug (verbose) messages
  -p PROCS, --procs PROCS
                        concurrent processes (~=simulated visitors)
  -r, --report          display post-execution summary
  -i, --index           stores an index in tests/ in the format URL_EPOCH
  --ua UA               specify a user-agent (overrides -v)
  --gz                  accept gzip compression (experimental)
  --robots              honor robots.txt directives
  --maxtime MAXTIME     max run time in seconds
  --verbose             displays all header and http debug info
  --silent              silences URL crawl notifications
```
---
Usage [examples](./EXAMPLES.md)
