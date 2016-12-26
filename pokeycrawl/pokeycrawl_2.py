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

from Queue import Queue, Empty
from threading import Thread, current_thread

# Module imports
from config import args as defaults
from log import setup_logger
from cli import parse_arguments, check_args
from _util import Stats, user_prompt, report, dig, Color

class Crawler(object):
    """ Base class for crawler objects """

    def __init__(self):
        self.__rename()
        self.__

    def __rename(self):
        self.name=current_thread().name

class Spider:
    pass

class FormCrawler(Spider):
    pass

class PageParser:
    pass

def abort(exit_code):
    # Add code to safely exit
    # clean up, close connections, etc
    log.debug('[!] Beginning abort sequence')
    sys.exit(exit_code)

class PokeyCrawl():
    """ Primary application class """

    def __init__(self):
        # Initialize args, log, queue, and other object
        self.args = args = parse_arguments(defaults)
        self.log = log = setup_logger(args)
        self.q = Queue()

        # Status messaging
        log.debug('[*] Application started')
        log.debug('[*] Logger {} spawned'.format(log.name))

        if args.test:
            self.tester=AppTester(log)
            self.tester.print_args(args)

    def prep_workers(self):
        worker_count=self.args.procs
        fc_count=self.args.procs/2 if self.args.forms else 0
        parser_count=1 if self.args.parse else 0

        self.pool={}
        for i in xrange(worker_count):
            t = Thread(target=Spider,name='Worker {}'.format(i))
            self.pool[t.name]=t

        for j in xrange(fc_count):
            f = Thread(target=FormCrawler,name='FCWorker {}'.format(j))
            self.pool[f.name]=f

        for k in xrange(parser_count):
            p = Thread(target=PageParser,name='Parser {}'.format(k))
            self.pool[p.name]=p

        if self.args.test:
            self.tester.worker_info(self.pool)

        self.log.debug('[*] {} workers added to the pool'.format(len(self.pool)))

    def init_stats(self,s):
        self.args.s=s
        if self.args.test:
            self.tester.initial_stats(s)

    def __execute(self,test=False):
        self.log.debug('[*] Executing the crawl')

class AppTester():
    """ Performs various tests when --test is passed """

    def __init__(self,log):
        self.log=log

    def print_args(self,args):
        self.log.info('[^] -*- Parameter Values -*-')
        for arg in vars(args):
            self.log.info('[^] {} :: {}'.format(
                                        arg,
                                        getattr(args,arg)
                                        ))
        self.log.info('[^] -*- End Parameter List -*-')

    def initial_stats(self,stats):
        self.log.info('[^] -*- Crawl Stats Initialized -*-')
        for item in vars(stats):
            self.log.info('[^] {} :: {}'.format(
                                        item,
                                        getattr(stats,item).count
                                        ))
        self.log.info('[^] -*- End Initial Stats -*-')

    def worker_info(self,pool):
        self.log.info('[^] -*- Worker List -*-')
        for p in pool:
            self.log.info('[^] {} :: {}'.format(
                                        pool[p].__class__.__name__,
                                        p
                                        ))
        self.log.info('[^] -*- End Woker List -*-')

if __name__=='__main__':
    # When invoked at the command line or via python -m,
    # parse command-line arguments to

    global log
    global args
    app = PokeyCrawl()
    # app = PokeyCrawl(args,log)
    app.prep_workers()
    app.init_stats(Stats())

    jobs=[]

    try:
        pass
    except KeyboardInterrupt,SystemExit:
        abort(0)
    except Exception as e:
        if debug: raise
        abort(1)
