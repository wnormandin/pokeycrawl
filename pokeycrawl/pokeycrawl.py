#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

"""
This utility uses multiprocessing to crawl websites, simulating multiple users
in order to load-test website functionality or simply to index the URLs within
a site.

https://github.com/wnormandin/pokeycrawl
"""

import mechanize
import urlparse
import random
import signal
import socket
import time
import argparse
import os, sys
import operator
import logging

from  multiprocessing import Process, Queue, cpu_count
from mechanize import BrowserStateError

# Multiprocessing Queue inherits from Queue, need to import error classes
# from the stdlib Queue
from Queue import Empty

def setup_logger(args):

    def __console_logging(logger,cfmt):
        cons_handler = logging.StreamHandler(sys.stdout)
        cons_handler.setFormatter(cfmt)
        cons_handler.setLevel(logger.level)
        if args.debug and args.verbose:
            print 'cons_handler : {}'.format(cons_handler)
            print 'cons_handler.level : {}'.format(cons_handler.level)
        logger.addHandler(cons_handler)

    def __file_logging(logger,fpath='../tests/crawl.log'):
        fpath = _resolve_path(fpath)
        fmt = logging.Formatter('%(asctime)s |%(message)s')
        file_handler = logging.FileHandler(fpath,'a')
        file_handler.setFormatter(fmt)
        file_handler.setLevel(logger.level)
        if args.debug and args.verbose:
            print 'file_handler : {}'.format(file_handler)
            print 'file_handler.level : {}'.format(file_handler.level)
        logger.addHandler(file_handler)

    def _get_level():
        if args.silent and args.logging and not args.debug:
            return logging.DEBUG
        if args.debug:
            return logging.DEBUG
        if args.verbose:
            return logging.INFO
        return logging.WARNING

    def _touch(fpath):
        if not os.path.exists(fpath):
            with open(fpath, 'w+') as f:
                return True
        return False

    def _resolve_path(fpath):
        # Convert to absolute path, touch file
        fpath = os.path.realpath(fpath)
        result = _touch(fpath)
        if result:
            print('[*] Created {}'.format(fpath))
        return fpath

    # Setup console and file output based on command-line parameters
    if args.debug and args.verbose:
        cfmt = logging.StreamHandler('%(filename)s[%(process)d] > %(message)s')
    else:
        cfmt = logging.StreamHandler('%(message)s')
    
    logger = logging.getLogger('pokeycrawl')
    logger.setLevel(_get_level())
    
    # Add the console handler if not in silent mode
    if not (args.silent and args.logging and not args.debug) or not args.silent:
        __console_logging(logger,cfmt)

    if args.logging:
        if args.logpath:
            params = (logger,args.logpath,)
        else:
            params = (logger,)

        __file_logging(*params)

    if args.debug and args.verbose:
        print 'logger.handlers : {}'.format(logger.handlers)

    return logger

def parse_arguments():

    # Defines options for command-line invocation
    parser = argparse.ArgumentParser()

    parser.add_argument('url',type=str,help='The URL to crawl')
    parser.add_argument('-s','--speed',type=float,default=0.25,
                help='set the crawl speed (defaults to 0.25s)')
    parser.add_argument('-v','--vary',action='store_true',
                help='vary the user-agent (requires a list in docs/ua.txt)')
    parser.add_argument('-d','--debug',action='store_true',
                help='enable debug (verbose) messages')
    parser.add_argument('-p','--procs',type=int,default=4,
                help='concurrent processes (~=simulated visitors)')
    parser.add_argument('-r','--report',action='store_true',
                help='display post-execution summary')
    parser.add_argument('-i','--index', action='store_true',
                help='stores an index in tests/ in the format URL_EPOCH')
    parser.add_argument('--ua',type=str,
                help='specify a user-agent (overrides -v)')
    parser.add_argument('--gz',action='store_true',
                help='accept gzip compression (experimental)')
    parser.add_argument('--robots', action='store_true',
                help='honor robots.txt directives')
    parser.add_argument('--maxtime',type=int,default=20,
                help='max run time in seconds')
    parser.add_argument('--verbose',action='store_true',
                help='displays all header and http debug info')
    parser.add_argument('--silent',action='store_true',
                help='silences URL crawl notifications')
    parser.add_argument('-l','--logging', action='store_true',
                help='enable logging')
    parser.add_argument('--logpath', default=False,
                help='specify a log path (defaults to ./text/crawl.log)')
    parser.add_argument('-y','--assume-yes',action='store_true',
                help='assumes a "yes" response to any prompts')

    # The --robots and --gz arguments are experimentally supported in 
    # mechanize, check your mechanize version for details and potential
    # issues.

    return parser.parse_args()

class Stats:

    """ Stores various counters/convenience methods for reporting """

    def __init__(self):
        self.refresh()

    def refresh(self):
        # re-initialize each counter
        self.crawled_count = 0
        self.err = {
            'urls':[],
            'errors':{}
            }
        self.times = []
        self.url_counts = []
        self.external_skipped = 0
        self.unique_urls = []

    def urls(self,new):

        def __unique(visited):
            # visited must be sorted
            prev = object()
            for url in visited:
                if url == prev:
                    continue
                yield url
                prev = url

        def __requests():
            # Add total request counter

        self.unique_urls.append(new)
        self.unique_urls = list(__unique(sorted(self.unique_urls)))

    def crawled(self,count,url_counts,external_skipped):
        # increment the crawled_count
        self.crawled_count += count
        self.url_counts.extend(url_counts)
        self.external_skipped += external_skipped

    def time(self,times):
        # add times to the list for averaging
        self.times.extend(times)

    def error(self,deets):
        # increment each error encountered
        # deets['url], deets['error']
        self.err['urls'].append(deets['url'])
        try:
            self.err['errors'][deets['error']] += 1
        except:
            self.err['errors'][deets['error']] = 1

class Spider:

    """ Spider superclass, contains all essential methods """

    def __init__(self,prms):
        # Takes any argument-containing namespace
        self.q,s = prms
        self.start = time.clock()
        self.result = None
        log.debug("[*] Spider spawned - PID {}".format(os.getpid()))
        self.cached_ips = {}
        self.history = []
        self.browser = prep_browser()
        self.url = self.prep_url(args.url)
        self.ip = self.dig(urlparse.urlparse(self.url).hostname)
        self.exclude = []

        # Each process aggregates site visit statistics
        # which are passed back via the stats Queue (r)
        self.stats = {
                'times':[],
                'visited':0,
                'err':[],
                'url_counts':[],
                'links_skipped':0,
                'ip':self.ip,
                'urls':[self.url]
                }

        # Grab the current worker process id
        self.name = 'Worker +{}'.format(
                    os.getpid()
                    )

        log.debug(' - {} :: crawl commencing'.format(self.name))
        # Start the crawl
        try:
            if self.ip is not None:
               self.get_links(self.url)
               self.stats['visited'] = len(self.history)
        except Exception as e:
            if args.debug: raise
            log.error(' - {} :: error encountered : {}'.format(self.name,e))
            sys.exit(0)

        log.info(' - {} :: crawl completed in {}s'.format(
                                                        self.name,
                                                        time.clock()-self.start
                                                        ))

        self.stats['visited'] = len(self.history)
        self.stats['urls'].extend(self.history)
        self.q.put(self.stats,1)

    def prep_url(self,url):
        return 'http://'+url if 'http://' not in url else url

    def dig(self,dom):
        if dom in self.cached_ips: return self.cached_ips[dom]
        try:
            self.cached_ips[dom] = ip = socket.gethostbyname(dom)
        except Exception as e:
            log.debug(' - exception raised in Spider.dig')
            self.stats['err'].append(
                { 'error': str(e),'url':dom }
                )
            return None
        return ip

    def poisoned(self):
        try:
            if self.q.get(True,1) is None:
                log.debug(' - {} :: poison pill received'.format(self.name))
                return True
        except Empty:
            if args.verbose: log.debug(' - {} :: empty queue read'.format(self.name))
        return False

    def get_links(self, url):
        if self.poisoned():
            return 'KILL'
        if not args.silent: print ' - {} :: crawling '.format(self.name), url
        start = time.clock()
        try:
            req = self.browser.open(url)
        except Exception as e:
            log.debug(' - exception raised in Spider.get_links')
            self.stats['err'].append(
                { 'error': str(e),'url':url }
                )

        self.stats['times'].append(time.clock()-start)
        links = [ln for ln in self.browser.links() if ln not in self.exclude]
        self.stats['url_counts'].append(len(links))

        log.debug(' - {} :: found {} links on {}'.format(
                                                    self.name,
                                                    len(links),
                                                    url
                                                    ))

        for link in self.browser.links():
            if self.poisoned():
                return 'KILL'

            if link.absolute_url not in self.history:
                ln = link.absolute_url
                dom = urlparse.urlparse(ln).hostname

                if dom and self.ip == self.dig(dom):
                    self.history.append(ln)
                    try:
                        sig = self.get_links(ln)
                        if sig == 'KILL': return sig
                    except BrowserStateError:
                        pass # Move on to the next URL when state is unexpected
                    except Exception as e:
                        log.debug(' - unexpected exception in Spider.get_links(child)')
                else:
                    self.stats['links_skipped'] += 1
        return

def prep_browser():
    if args.verbose:
        log.debug('[*] Preparing browser ({})'.format(os.getpid()))

    # Defaults :
    b = mechanize.Browser()
    b.set_handle_robots(args.robots)
    b.set_handle_gzip(args.gz)
    b.set_handle_refresh(mechanize._http.HTTPRefreshProcessor(),max_time=1)

    ua = 'PokeyBot/1.0 (+https://pokeybill.us/bots/)'

    # With the user-agent vary option, substitute your own ua strings
    # must be placed within the docs directory in a file ua.txt
    if args.ua is not None:
        ua = args.ua
    else:
        if args.vary:
            log.debug(' - varying user-agent')
            try:
                with open('../docs/ua.txt','rb') as useragents:
                    possibles = [l for l in useragents.readlines() if l.rstrip()]
            except:
                log.error(' - error reading docs/ua.txt')
                if args.debug: raise
                ua = 'PokeyBot/1.0 (+https://pokeybill.us/bots/)'
            else:
                ua = possibles[random.randint(0,len(possibles)-1)]

    if args.verbose:
        log.debug(' - user-agent : {}'.format(ua))

    headers = [('User-Agent', ua)]

    for line in [
        ('Accept',
         'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        ),
        ('Accept-Language', 'en-gb,en;q=0.5'),
        ('Accept-Charset', 'ISO-8859-1,utf-8;q=0.7,*;q=0.7'),
        ('Keep-Alive', str(args.maxtime)),
        ('Connection', 'keep-alive'),
        ('Cache-Control', 'max-age=0'),
        ]:
        headers.append(line)

    b.addheaders = headers

    if args.verbose:
        b.set_debug_http(True)
        b.set_debug_redirects(True)
        b.set_debug_responses(True)

    return b

def report():
    stats = args.s
    try:
        bar = '============================='
        print '\n', bar
        print('Links crawled     : {}'.format(stats.crawled_count))
        try:
            avg_time = sum(stats.times)/float(len(stats.times))
            print('Avg load time     : {:.5f}'.format(avg_time))
        except:
            print('0')
        print('\tMax time  : {:.5f}'.format(max(stats.times)))
        print('\tMin time  : {:.5f}'.format(min(stats.times)))
        print('\tTotal     : {:.5f}'.format(sum(stats.times)))
        print('\nAvg URLs/page     : {:.2f}'.format(sum(stats.url_counts)/float(len(stats.url_counts))))
        print('URLs skipped      : {}'.format(stats.external_skipped))

        url_err_set = set(stats.err['urls'])
        print('\nURLs with Errors  : {}'.format(len(url_err_set)))
        print('Errors returned   : {}'.format(len(stats.err['errors'])))
        print bar, '\n'

        # Option to display error list
        if len(url_err_set)>0:
            if not args.assume_yes:
                ch = raw_input('View error detail? (y/n) > ').lower()
            if args.assume_yes or (ch=='y'):
                print('[*] Displaying top 5 errors')
                srtd_list = sorted(
                                stats.err['errors'].items(),
                                key=operator.itemgetter(1)
                                )
                for key in srtd_list[:5]:
                    print(' * {} : count[{}]'.format(key[0],key[1]))

    except Exception as e:
        if args.debug: raise
        log.info('[*] Exception in report(): {},{}'.format(e,str(e)))

def kill_jobs(jobs,q,s):
    results = []

    log.debug(' - {} :: beginning cleanup'.format(args.parent_name))
    for j in jobs:
        try:
            q.put(None,1)
        except:
            log.debug(' - {} :: queue full, skipping put'.format(args.parent_name))
            continue

    returned = 0
    while True:
        try:
            result = q.get(True,1)
            if result == None:
                q.put(None,1)   # push back any poison pills removed
            else:
                if args.debug and args.verbose:
                    log.debug(' - {} :: received from queue : {}'.format(
                                                            args.parent_name,
                                                            result
                                                            ))
                else:
                    log.debug(' - {} :: received {} items from queue'.format(
                                                            args.parent_name,
                                                            len(result)
                                                            ))
                count_beans(result,s)
                returned += 1

                if returned >= args.procs:
                    break

        except Empty:
            continue
        except:
            if args.debug: raise
            continue

    log.debug(' - {} :: sending term signals'.format(args.parent_name))
    for j in jobs:
        q.put(None,False)

    log.debug(' - {} :: joining jobs'.format(args.parent_name))
    for j in jobs:
        j.join(1)

    log.debug(' - {} :: cleaning up jobs'.format(args.parent_name))
    # Clean up stalling processes (data-destructive!)
    if any(j.is_alive() for j in jobs):
        for j in jobs:
            j.terminate()

    log.debug(' - {} :: kill routine completed'.format(args.parent_name))

def count_beans(stats,s):
    # Calls the various statistics-gathering methods of Stats
    s.crawled(stats['visited'],stats['url_counts'],stats['links_skipped'])
    s.time(stats['times'])
    for e in stats['err']:
        s.error(e)
    s.urls(stats['urls'])

def user_prompt(msg):
    if not args.assume_yes:
        ch = raw_input(msg).upper()
    if args.assume_yes or (ch=='Y'):
        return True
    return False

def check_args():
    # Operator and logical assertions

    # >5 begins to see noticeable slowness on some machines
    # use multiple sources for higher load simulations
    max_procs = cpu_count()*5
    if args.procs > max_procs:
        msg = '[!] Proc count over max ({}, cpu count x 5) - use this limit? > '.format(max_procs)
        # use raw_input so it is always str()
        if user_prompt(msg):
            args.procs = max_procs
            log.debug('\tuser changed max_procs to : {}'.format(max_procs))

    if not args.logging and args.logpath:
        msg = '[!] Log path specified, but logging is not enabled - enable logging? >'
        if user_prompt(msg):
            args.logging = True
            log.debug('\tuser enabled logging')

    if args.debug:
        args.silent = False

    if args.index:
        base_path = os.path.dirname(os.path.realpath(__file__))
        log.debug(' - {} :: base path - {}'.format(args.parent_name,base_path))
        path_list = base_path.split('/')[:-1]
        path_list.append('tests')
        fpath = '{}/{}_{}.idx'.format(
                '/'.join(path_list),
                args.url.replace(' ',''),
                int(time.time())
                )
        log.info('[*] Index file : {}'.format(fpath))
        args.idx_path = fpath

def write_index(s):
    log.debug(' - {} :: unique urls : {}'.format(args.parent_name,s.unique_urls))
    with open(args.idx_path,'w+') as ofile:
        ofile.writelines(url for url in s.unique_urls)

# If --silent is used without -d|--debug or --verbose, show progress bar
def do_progress_bar(max_time):
    # Disable output buffering for inline updates
    sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)
    start = time.clock()
    max_width = 40          # Progress bar width
    interval = max_time/float(max_width)  # loop interval will scale
    print('@'),
    while True:
        if max_width <= 0:
            print('@')
            return
        else:
            print('>'),
            time.sleep(interval)
            max_width -= 1

args = parse_arguments()
log = setup_logger(args)

if __name__=="__main__":
    os.environ['http_proxy']=''
    args.l = log
    args.s = s = Stats()
    args.parent_name = 'Crawler {}'.format(os.getpid())
    check_args()    # Basic input validation
    q = Queue() # Multiprocessing queue
    jobs = []
    fail = False

    try:
        # Start the worker processes
        log.debug(' - {} :: starting worker processes'.format(args.parent_name))
        for i in range(args.procs):
            p = Process(
                        target = Spider,
                        args = ((q,s),)
                        )
            p.start()
            jobs.append(p)

        # Wait for the maximum execution time to expire
        if not args.verbose and not args.debug and args.silent:
            do_progress_bar(args.maxtime)
        else:
            time.sleep(args.maxtime)
        log.info("[*] Time's up!")
    except KeyboardInterrupt:
        log.warning(' - {} :: Keyboard interrupt detected!'.format(args.parent_name))
        kill_jobs(jobs,q,s)
        sys.exit(0)
    except Exception as e:
        fail = True
        if args.debug: raise
        log.error('[*] Error Encountered : {},{}'.format(e,str(e)))
        sys.exit(1)

    try:
        log.debug("[*] @@ kill_jobs() @@")
        if args.verbose: 
            log.debug(' *  jobs : {}'.format([job.pid for job in jobs]))

        kill_jobs(jobs,q,s)
        if args.index: write_index(s)
        if args.report and not fail:
            log.debug(' - {} :: printing report'.format(args.parent_name)) 
            report()
        log.debug('[*] {} :: killing me'.format(args.parent_name))
    except:
        if args.debug: raise
        sys.exit(1)
    else:
        log.info('[*] Crawl completed successfully')