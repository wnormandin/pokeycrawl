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
import threading

from Queue import Queue, Empty
from threading import Thread, current_thread

current_thread().name='pokeycrawl'
this = sys.modules[__name__]

# Module imports
from config import args as defaults
from log import setup_logger
from cli import parse_arguments, check_args
from _util import Stats, user_prompt, report, dig, Color,color_wrap
from _util import do_progress_bar

class Crawler(object):
    """ Base class for crawler objects """

    def __init__(self):
        self.__rename()
        if args.test or args.verbose:
            log.debug('[-] {} started'.format(self.name))

    def __rename(self):
        self.name=current_thread().name

class Spider(Crawler):
    pass

class FormCrawler(Spider):
    pass

class PageParser(Crawler):
    pass

def abort(exit_code):
    # Add code to safely exit
    color_log('[!] Beginning abort sequence',Color.ERR)
    sys.exit(exit_code)

class PokeyCrawl():
    """ Primary application class """

    def __init__(self):
        # Initialize args, log, queue, and other object
        self.q = Queue()

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

        self.pool={}
        for i in xrange(worker_count):
            t = Thread(target=Spider,name='Spider {}'.format(i))
            self.pool[t.name]=t

        for j in xrange(fc_count):
            f = Thread(target=FormCrawler,name='FormCrawler {}'.format(j))
            self.pool[f.name]=f

        for k in xrange(parser_count):
            p = Thread(target=PageParser,name='PageParser {}'.format(k))
            self.pool[p.name]=p

        if args.test:
            self.tester.worker_info(self.pool)

        log.debug('[*] {} workers added to the pool'.format(len(self.pool)))

    def start_workers(self):
        for worker in self.pool:
            self.pool[worker].start()

    def join_workers(self):
        for worker in self.pool:
            self.pool[worker].join()

    def init_stats(self,s):
        args.s=s
        if args.test:
            self.tester.initial_stats(s)

    def __execute(self,test=False):
        log.debug('[*] Executing the crawl')

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

def color_log(msg,color,lvl='debug'):
    getattr(log,lvl)(color_wrap(msg,color,args.logging))

if __name__=='__main__':

    assert isinstance(threading.current_thread(), threading._MainThread)
    # When executed or invoked via python -m,
    # parse command-line arguments and setup the logger
    # args/log must exist at a module level when not invoking
    # at the command line.
    this.args = parse_arguments(defaults)
    this.log = setup_logger(args)

    try:
        app = PokeyCrawl()
        app.prep_workers()
        app.init_stats(Stats())
        color_log('[!] Preparations complete, crawl commencing',Color.MSG)
        app.start_workers()
        color_log('[!] Workers started',Color.MSG)
        do_progress_bar(args.maxtime)
        app.join_workers()
        color_log('[!] Workers joined',Color.MSG)
        if args.report:
            report(args)
    except KeyboardInterrupt,SystemExit:
        color_log('[!] KeyboardInterrupt detected',Color.ERR,'error')
        abort(0)
    except Exception as e:
        if args.debug: raise
        abort(1)
