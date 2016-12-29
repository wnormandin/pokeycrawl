#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

"""
This utility uses multiprocessing to crawl websites, simulating multiple users
in order to load-test website functionality or simply to index the URLs within
a site.
https://github.com/wnormandin/pokeycrawl
"""

import requests
import urlparse
import random
import time
import os, sys
import multiprocessing
from Queue import Queue, Empty
from requests.exceptions import RequestException,ConnectionError,Timeout

this = sys.modules[__name__]

# Module imports
from config import args as defaults
from log import setup_logger
from cli import parse_arguments, check_args
from _util import Stats, user_prompt, report, dig, Color,color_wrap
from _util import do_progress_bar

class Crawler():
    """ Base class for crawler objects """

    def __init__(self,stats,queues,stop):
        self.start = time.clock()
        self._rename()

        self.stats = stats
        self.queues = queues
        self.stop = stop

        if args.test or args.verbose:
            log.debug('[-] {} started'.format(self.name))

    def _rename(self):
        self.name='Worker {}'.format(os.getpid())

    def _queue_read(self,q):
        try:
            return q.get(True,args.timeout)
        except Queue.Empty:
            return

    def _queue_send(self,q,data):
        try:
            q.put(data)
        except:
            # handle stuff
            pass

    def join(self, timeout=None):
        # Stuff to do before joining
        super(multiprocessing.Process, self).join(timeout)

    def execute(self):
        while not self.stop.wait(args.timeout):
            pass
        color_log('[*] {}::kill signal received'.format(self.name),
                Color.MSG)

class Spider(Crawler):

    """ Base class for Spider objects (Spider,FormCrawler) """

    def _rename(self):
        self.name='Spider {}'.format(os.getpid())

    def __init__(self,arg_list):
        # Explicitly calling super(Crawler...) to avoid infinite loop
        # in the FormCrawler child
        Crawler.__init__(self,*arg_list)

        self.cached_ips = {} # cache IPs to minimize dig() ops
        self.history = []   # request history
        self.exclude = []   # URLs to be excluded from future requests

        response=self.execute()
        if response is not None:
            args.s.crawled_count.increment()
            args.s.response_codes.increment(response.status_code)
            args.s.url_counts.increment(response.url)

    # http://docs.python-requests.org/en/master/user/quickstart/
    def make_request(self,uri,auth=None,payload=None,method=requests.get):
        try:
            if auth is not None:
                # auth=('user','pass') login via HTTP
                return method(uri,auth=auth,timeout=args.timeout)
            elif payload is not None:
                # payload={'key':'value'...} automatically form-encoded by requests
                return method(uri,data=payload,timeout=args.timeout)
            else:
                assert method is not requests.post, \
                    color_wrap('[!] POST requests require data!',Color.ERR,args.logging)
                return method(uri,timeout=args.timeout)
        except RequestException as e:
            color_log('[!] {} :: {}'.format(
                                self.name,str(e[-1])),
                                Color.ERR,
                                'error'
                                )
            return

    def execute(self):
        while not self.stop.wait(args.timeout):
            # Do normal execution
            try:
                # crawl
                pass
            except:
                pass
                # catch stuff
        # Clean up after stop request received
        # send any remaining results to stats_q
        log.debug('[*] {} :: Execution complete'.format(self.name))
        return self.make_request(args.url)

class FormCrawler(Spider):

    def _rename(self):
        self.name = 'FormCrawler {}'.format(os.getpid())

class PageParser(Crawler):

    def _rename(self):
        self.name = 'PageParser {}'.format(os.getpid())

    def __init__(self,arg_list):
        Crawler.__init__(self,*arg_list)

def abort(exit_code):
    # Add code to safely exit
    color_log('[!] Beginning abort sequence',Color.ERR)
    stop.set()
    sys.exit(exit_code)

class PokeyCrawl():
    """ Primary application class """

    def __init__(self):
        # Initialize args, log, queue, and other object
        self.stat_q = stat_q
        self.form_q = form_q
        self.html_q = html_q

        self.expired = False
        self.start = time.clock()
        log.debug('[*] PokeyCrawl initialized at {}'.format(self.start))

        # Status messaging
        log.debug('[*] Application started')
        log.debug('[*] Logger {} spawned'.format(log.name))

        if args.test:
            self.tester=AppTester()
            self.tester.print_args()

    def prep_workers(self):
        worker_count=args.procs
        fc_count=args.procs/2 if args.forms else 0
        parser_count=1 if args.parse else 0

        # Condense this section to a function once the logic
        # is fleshed out
        Proc = multiprocessing.Process
        self.pool={}
        for i in xrange(worker_count):
            t = Proc(
                    target=Spider,
                    args=((stat_q,(html_q,),stop),)
                    )
            self.pool[t.name]=t

        for j in xrange(fc_count):
            f = Proc(
                    target=FormCrawler,
                    args=((stat_q,(form_q,),stop),)
                    )
            self.pool[f.name]=f

        for k in xrange(parser_count):
            p = Proc(
                    target=PageParser,
                    args=((stat_q,(html_q,form_q),stop),)
                    )
            self.pool[p.name]=p

        if args.test:
            self.tester.worker_info(self.pool)

        log.debug('[*] {} workers added to the pool'.format(len(self.pool)))

    def _poll(self):
        try:
            result = self.stat_q.get(False,args.timeout)
        except Empty:
            # ignore empty queue reads
            pass
        else:
            log.debug('[*] {} received'.format(result))
            # parse results

    def start_workers(self):
        for worker in self.pool:
            self.pool[worker].start()

    def join_workers(self):
        stop.set()
        for worker in self.pool:
            self.pool[worker].join()

    def init_stats(self,s):
        args.s=s
        if args.test:
            self.tester.initial_stats(s)

    def execute(self,test=False):
        if args.verbose:
            log.debug('[*] {} :: execute() invoked'.format(self.name))
        if test:
            self.start_workers()
            time.sleep(args.maxtime)
            self.join_workers()

class AppTester():
    """ Performs various tests when --test is passed """

    def print_args(self):
        log.info('[@] -*- Parameter Values -*-')
        for arg in vars(args):
            log.info('[-] {} :: {}'.format(
                                        arg,
                                        getattr(args,arg)
                                        ))
        log.info('[@] -*- End Parameter List -*-')

    def get_text_result(self,bool_result,col=False):
        if bool_result:
            msg=color_wrap('PASS',Color.GREEN)
        else:
            msg=color_wrap('FAIL',Color.GREEN)

        return msg

    def initial_stats(self,stats):

        def __increment_counters():
            try:
                for item in vars(stats):
                    for i in xrange(1,6):
                        getattr(stats,item).increment(i)
            except Exception as e:
                raise
                return False
            else:
                return True

        log.info('[@] -*- Crawl Stats Initialized -*-')
        log.info('[@] -*- Testing Counters -*-')

        test_result = self.get_text_result(__increment_counters())
        log.info('[!] -*- Counters: {} -*-'.format(test_result))

        for item in vars(stats):
            log.info('[-] {} :: {}'.format(
                                        item,
                                        getattr(stats,item).count
                                        ))
        stats.refresh()
        log.info('[@] -*- End Initial Stats -*-')

    def worker_info(self,pool):
        log.info('[@] -*- Worker List -*-')
        for p in pool:
            log.info('[-] {} :: {}'.format(
                                        pool[p].__class__.__name__,
                                        p
                                        ))
        log.info('[@] -*- End Woker List -*-')

def color_log(msg,color,method='debug'):
    getattr(log,method)(color_wrap(msg,color,args.logging))

if __name__=='__main__':

    # When executed or invoked via python -m,
    # parse command-line arguments and setup the logger
    # args/log must exist at a module level when not invoking
    # at the command line.
    this.args = parse_arguments(defaults)
    this.log = setup_logger(args)

    this.stat_q = Queue() # Statistics Queue - might not be necessary
    this.form_q = Queue() # Queue for sending forms to the FormCrawler
    this.html_q = Queue() # Queue for passing html from Spiders to Parsers

    this.stop = multiprocessing.Event() # Event to handle kill signalling

    try:
        app = PokeyCrawl()
        app.init_stats(Stats())
        app.prep_workers()
        color_log('[!] Preparations complete, crawl commencing',Color.MSG)
        app.execute(True)
        color_log('[!] Application Executed',Color.MSG)
        if args.report:
            report(args)
    except KeyboardInterrupt,SystemExit:
        color_log('[!] KeyboardInterrupt detected',Color.ERR,'error')
        abort(0)
    except Exception as e:
        if args.debug: raise
        abort(1)
