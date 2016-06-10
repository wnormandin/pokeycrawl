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

from  multiprocessing import Process, Queue
# Multiprocessing Queue inherits from Queue, need to import error classes
# from the stdlib Queue
from Queue import Empty

def parse_arguments():

    # Defines options for command-line invocation
    parser = argparse.ArgumentParser()

    parser.add_argument('url',type=str,help='The URL to crawl')
    parser.add_argument('-s','--speed',type=float,default=0.25,
                help='set the crawl speed (defaults to 0.25s between clicks)')
    parser.add_argument('-v','--vary',action='store_true',
                help='vary the user-agent')
    parser.add_argument('-d','--debug',action='store_true',
                help='enable debug (verbose) messages')
    parser.add_argument('-p','--procs',type=int,default=4,
                choices=range(1,6),help='Concurrent processes (max 5)')
    parser.add_argument('-r','--report',action='store_true',
                help='display post-execution summary')
    parser.add_argument('--ua',type=str,
                help='specify a user-agent (overrides -v, def=firefox)')
    parser.add_argument('--gz',action='store_true',
                help='accept gzip compression (experimental)')
    parser.add_argument('--robots', action='store_true',
                help='honor robots.txt directives')
    parser.add_argument('--maxtime',type=int,default=20,
                help='Max run time in seconds')
    parser.add_argument('--verbose',action='store_true',
                help='displays all header and http debug info')
    parser.add_argument('--silent',action='store_true',
                help='silences URL crawl notifications')

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

def bean_wrap(cls):

    # Allows returns other than the class instance
    # overriding the default invocation behavior
    def wrapper(args,):

        instance = cls(args,)
        if args[0].debug:
            print 'Received : ', instance.retval
        args[1].put(instance.retval)

    return wrapper

#@bean_wrap
class Spider:

    """ Spider superclass, contains all essential methods """

    def __init__(self,prms):
        # Takes any argument-containing namespace
        self.args,(self.q,self.r),s = prms
        self.result = None
        if self.args.debug:
            print "Spider spawned - PID {}".format(os.getpid())
        self.args = args
        self.cached_ips = {}
        self.history = []
        self.browser = prep_browser(args)
        self.url = self.prep_url(args.url)
        self.ip = self.dig(urlparse.urlparse(self.url).hostname)

        # Each process aggregates site visit statistics
        # which are passed back via the stats Queue (r)
        self.stats = {
                'times':[],
                'visited':0,
                'err':[],
                'url_counts':[],
                'links_skipped':0,
                'ip':self.ip
                }

        # Grab the current worker process id
        self.name = 'Worker ({})'.format(
                    os.getpid()
                    )

        # Start the crawl
        try:
            if self.ip is not None:
               self.get_links(self.url)
               self.stats['visited'] = len(self.history)
        except KeyboardInterrupt:
            pass    # Skip processing for KeyboardInterrupts
        except:
            raise   # Raise exceptions
        finally:
            try:
                self.stats['visited'] = len(self.history)
                self.r.put(self.stats)
            except:
                raise

    def prep_url(self,url):
        return 'http://'+url if 'http' not in url else url

    def dig(self,dom):
        if dom in self.cached_ips: return self.cached_ips[dom]
        try:
            self.cached_ips[dom] = ip = socket.gethostbyname(dom)
        except Exception as e:
            if self.args.debug:
                print '{} : '.format(dom),str(e)
            self.stats['err'].append(
                { 'error': str(e),'url':dom }
                )
            return None
        return ip

    def get_links(self, url):
        if not self.args.silent: print '{} : Crawling '.format(self.name), url
        start = time.clock()
        try:
            req = self.browser.open(url)
        except Exception as e:
            if self.args.debug:
                print '{} : '.format(url),str(e)
            self.stats['err'].append(
                { 'error': str(e),'url':url }
                )


        self.stats['times'].append(time.clock()-start)
        self.stats['url_counts'].append(len([ln for ln in self.browser.links()]))

        for link in self.browser.links():
            try:
                if self.q.get(True,self.args.speed) == 'DONE':
                    print 'Killing ', self.name
                    return 'KILL'
            except Empty:
                pass    # Not concerned with empty queue reads

            if link.absolute_url not in self.history:
                ln = link.absolute_url
                dom = urlparse.urlparse(ln).hostname

                if dom and self.ip == self.dig(dom):
                    self.history.append(ln)
                    try:
                        sig = self.get_links(ln)
                        if sig == 'KILL': return sig
                    except Exception as e:
                        if self.args.debug:
                            print '{} : '.format(ln),str(e)
                        self.stats['err'].append(
                            { 'error': str(e),'url':ln }
                            )
                else:
                    self.stats['links_skipped'] += 1
        return

def prep_browser(args):

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
            with open('../docs/ua.txt','rb') as useragents:
                possibles = [l for l in useragents.readlines() if l.rstrip()]
            ua = possibles[random.randint(0,len(possibles)-1)]

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

def report(args):
    stats = args.s
    try:
        bar = '============================='
        print '\n', bar
        print 'Links crawled    : {}'.format(stats.crawled_count)
        try:
            avg_time = sum(stats.times)/float(len(stats.times))
            print 'Avg load time    : {:.5f}'.format(avg_time)
        except:
            print '0',
        print '\tMax time : {:.5f}'.format(max(stats.times))
        print '\tMin time : {:.5f}'.format(min(stats.times))
        print '\tTotal    : {:.5f}'.format(sum(stats.times))
        print '\nAvg URLs/page    : {:.5f}'.format(sum(stats.url_counts)/float(len(stats.url_counts)))
        print 'URLs skipped      : {}'.format(stats.external_skipped)

        url_err_set = set(stats.err['urls'])
        print '\nURLs with Errors  : {}'.format(len(url_err_set))
        print 'Errors returned   : {}'.format(len(stats.err['errors']))
        if len(url_err_set)>0:
            if raw_input('- View error detail? (y/n) > ').lower()=='y':
                print '- Displaying top 5 errors'
                srtd_list = sorted(
                                stats.err['errors'].items(),
                                key=operator.itemgetter(1)
                                )
                for key in srtd_list[:5]:
                    print '\t{} :: Count : {}'.format(*key)
        print bar
    except Exception as e:
        if args.debug: raise
        print '[*] Exception in report(): {},{}'.format(e,str(e))

def kill_jobs(jobs,q,r,s):
    results = []
    while any([j.is_alive() for j in jobs]):
        for j in jobs:
            try:
                q.put('DONE',False)
            except:
                print 'Queue full, skipping put'
                continue

    for j in jobs:
        j.join()

    while True:
        try:
            result = r.get(True,1)
            #print '[*] Received from queue : {}'.format(result)
            count_beans(result,s)
        except Empty:
            break
        except:
            raise
            continue

def count_beans(stats,s):
    s.crawled(stats['visited'],stats['url_counts'],stats['links_skipped'])
    s.time(stats['times'])
    for e in stats['err']:
        s.error(e)

if __name__=="__main__":

    os.environ['http_proxy']=''
    args = parse_arguments()
    args.s = s = Stats()
    q = Queue() # Multiprocessing send queue
    r = Queue() # Multiprocessing receive queue
    jobs = []
    fail = False

    try:
        # Start the worker processes
        for i in range(args.procs):
            p = Process(
                        target = Spider,
                        args = ((args,(q,r),s),)
                        )
            p.start()
            jobs.append(p)

        # Wait for the maximum execution time to expire
        time.sleep(args.maxtime)
        print 'Times up!'
    except KeyboardInterrupt:
        print '\nKeyboard interrupt detected!'
    except Exception as e:
        fail = True
        if args.debug: raise
        print '[*] Error Encountered : {},{}'.format(e,str(e))
    else:
        print '[*] Crawl completed successfully'
    finally:
        try:
            kill_jobs(jobs,q,r,s)
            if args.report and not fail: report(args)
            if not fail: sys.exit(0)
            raise AssertionError('Execution Failed!')
        except:
            sys.exit(1)
