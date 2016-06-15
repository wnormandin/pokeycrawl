##pokeycrawl examples
###basic usage examples :
---
####default invocation
Invoking with no arguments will execute with the following defaults
  - max processes   : 4 (5*cpu_count suggested max)
  - max time        : 20s (approximate execution time)
  - crawl speed     : 0.25s between requests
  - reporting       : No reporting by default
  - indexing        : No indexing by default
  - user-agent      : PokeyBot/1.0 (+https://pokeybill.us/bots/)
```
$ python pokeycrawl.py systempoetry.com
- Worker +9637 :: crawling  http://systempoetry.com
- Worker +9636 :: crawling  http://systempoetry.com
- Worker +9639 :: crawling  http://systempoetry.com
- Worker +9638 :: crawling  http://systempoetry.com
...
- Worker +9638 :: crawling  http://systempoetry.com/posts#content
- Worker +9639 :: crawling  http://systempoetry.com/posts#content
- Worker +9637 :: crawling  http://systempoetry.com/posts#content
[*] Time's up!
[*] Crawl completed successfully
```
---
####varying user-agent
The user-agent string can be varied to simulate more typical usage by multiple clients
  - specify user-agents in docs/ua.txt
  - one ua string per line
```
$ python pokeycrawl.py -v --maxtime 1 pokeybill.us
- Worker +10093 :: crawling  http://pokeybill.us
- Worker +10095 :: crawling  http://pokeybill.us
- Worker +10094 :: crawling  http://pokeybill.us
- Worker +10092 :: crawling  http://pokeybill.us
[*] Time's up!
[*] Crawl completed successfully
```
---
####reporting/indexing
Executing with the `-r|--report` and `-i|--index` arguments
  - The maximum execution time is set to 2s in this example
  - the index file is stored in the tests/ directory in the format :
    - **URL_EPOCH**.idx
```
$ python pokeycrawl.py -r -i --maxtime 2 systempoetry.com
[*] Index file : /home/pokeybill/python/pokeycrawl/tests/systempoetry.com_1465741359.idx
- Worker +9765 :: crawling  http://systempoetry.com
- Worker +9764 :: crawling  http://systempoetry.com
...
- Worker +9762 :: crawling  http://systempoetry.com/
- Worker +9764 :: crawling  http://systempoetry.com/
[*] Time's up!
[*] Crawl completed successfully

=============================
Links crawled    : 8
Avg load time    : 0.01011
	Max time : 0.01299
	Min time : 0.00740
	Total    : 0.08088

Avg URLs/page    : 26.00000
URLs skipped      : 0

URLs with Errors  : 0
Errors returned   : 0
=============================
```
  - report breakdown
    - links crawled : the number of links visited (URLs/page is calculated with 'unvisited' URLs included)
    - avg load time : the average time (in seconds) spent waiting for HTTP reponses
    - min/max times : the minimum and maximum HTTP reponse wait time
    - total         : the total time spent waiting for HTTP reponses
    - avg urls/page : the average count of URLs (internal and external) detected per page
    - URLs skipped  : count of external URLs skipped in the crawl
    - URLs with Err : count of URLs which returned errors
    - errors returned : the total number of errors encountered in the crawl worker subprocesses
    - *IF* errors are present, the user is prompted and the top 5 errors can be displayed with counts
    
---
####load testing
To load test, increase the process count and reduce the speed timing
  - it is recommended to use the `--silent` argument to supress crawl notifications
  - using `--silent` **without** `-d|--debug` and `--verbose` will enable a status bar
  - this example demonstrates the prompt when procs exceeds the recommended max
```
$ python pokeycrawl.py -p 8 --silent -s 0.1 systempoetry.com
[!] Proc count over max (5, cpu count x 5) - use this limit? > y
@ > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > [*] Time's up!
[*] Crawl completed successfully
```
---
####verbose
Verbose output will include program and HTTP debugging information, HTTP headers, and additional connection details.
```
$ python pokeycrawl.py -p 1 --maxtime 1 --verbose systempoetry.com
- Worker +10158 :: crawling  http://systempoetry.com
send: 'GET / HTTP/1.1\r\nAccept-Encoding: identity\r\nAccept-Language: en-us,en;q=0.5\r\nConnection: close\r\nKeep-Alive: 1\r\nAccept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8\r\nUser-Agent: PokeyBot/1.0 (+https://pokeybill.us/bots/)\r\nAccept-Charset: ISO-8859-1,utf-8;q=0.7,*;q=0.7\r\nHost: systempoetry.com\r\nCache-Control: max-age=0\r\n\r\n'
reply: 'HTTP/1.1 200 OK\r\n'
header: Date: Sun, 12 Jun 2016 14:55:08 GMT
header: Server: Apache/2.4.6 (CentOS) OpenSSL/1.0.1e-fips PHP/5.4.16
header: Last-Modified: Sun, 12 Jun 2016 14:13:24 GMT
header: ETag: "2e5c-535155fff0c68"
header: Accept-Ranges: bytes
header: Content-Length: 11868
header: Vary: Accept-Encoding,Cookie
header: Cache-Control: max-age=1095, public, public
header: Expires: Sun, 12 Jun 2016 15:13:24 GMT
header: X-Powered-By: W3 Total Cache/0.9.4.1
header: Pragma: public
header: Connection: close
header: Content-Type: text/html; charset=UTF-8
[*] Time's up!
[*] Crawl completed successfully
```
---
####debug
Debugging output can be useful if execution is failing for bug reports
  - report any issues to bill@pokeybill.us with this output
```
$ python pokeycrawl.py -p 1 --maxtime 2 -d systempoetry.com
- Crawler 10185 :: starting worker processes
[*] Spider spawned - PID 10186
- Worker +10186 :: crawl commencing
- Worker +10186 :: crawling  http://systempoetry.com
- Worker +10186 :: found 26 links on http://systempoetry.com
- Worker +10186 :: crawling  http://systempoetry.com/
- Worker +10186 :: found 26 links on http://systempoetry.com/
[*] Time's up!
[*] Crawl completed successfully
- Crawler 10185 :: beginning cleanup
- Worker +10186 :: poison pill received
- Worker +10186 :: crawl completed in 0.036977s
- Crawler 10185 :: received from queue : {'err': [], 'url_counts': [26, 26], 'ip': '45.55.150.186', 'times': [0.005215000000000001, 0.007323999999999997], 'links_skipped': 0, 'urls': ['http://systempoetry.com', 'http://systempoetry.com/'], 'visited': 1}
- Crawler 10185 :: sending term signals
- Crawler 10185 :: joining jobs
- Crawler 10185 :: cleaning up jobs
- Crawler 10185 :: kill routine completed
- Crawler 10185 :: killing me
```
---
####utilities
There are a couple of utility scripts included
```
pokeycrawl/utils$ ls
cleanup_tests.sh  strace_crawl.sh
```
  - strace_crawl.sh waits for a pokeycrawl process to appear, then saves strace output to a file in tests/
  - cleanup_tests.sh clears .idx files from the tests/ directory
