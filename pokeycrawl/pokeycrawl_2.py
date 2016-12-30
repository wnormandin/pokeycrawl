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
from HTMLParser import HTMLParser
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

    def __init__(self,stats,forms,stop):
        self.start = time.clock()
        self._rename()
        self._clear_stat_cache()

        self.stats_q = stats
        self.form_q = forms
        self.stop = stop

        if args.test or args.verbose:
            log.debug('[-] {} started'.format(self.name))

    def _clear_stat_cache(self):
        if args.test or args.verbose:
            log.debug('[-] {} :: _clear_stat_cache() called'.format(self.name))
        self.stat_cache = {}
        for counter in Stats.counters:
            self.stat_cache[counter]=0
        for list_count in Stats.list_counters:
            self.stat_cache[list_count]=[]

    def _rename(self):
        self.name='{} {}'.format(self.__class__.__name__,os.getpid())

    def _queue_read(self,q):
        try:
            # Pull an item from the queue of interest
            return q.get(True,args.timeout)
        except Empty:
            # Ignoring empty queue reads
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

    def __init__(self,arg_list):
        # Explicitly calling super(Crawler...) to avoid infinite loop
        # in the FormCrawler child
        Crawler.__init__(self,*arg_list)

        self.cached_ips = {} # cache IPs to minimize dig() ops
        self.history = []   # request history
        self.exclude = []   # URLs to be excluded from future requests
        self.to_do = []     # list of found URLs to be processed
        self.baseurl = self.base_url()
        self.parser = BasicParser()

        # Set up cookie support
        self.jar = requests.cookies.RequestsCookieJar()

        # Start the crawl
        self.execute()

    def next_task(self):
        # Default behavior is to start at the beginning
        # when the list of unique links has been visited
        if self.to_do:
            retval = random.choice(self.to_do)
            self.visited(retval)
            self.to_do.remove(retval)
            return retval
        else:
            if args.maxtime==0:
                color_log('[!] {} :: Out of links!  Crawl complete'.format(
                                                         self.name),Color.MSG)
                return
            # Restart the crawl
            self.history = []
            return args.url

    def q_task_done(self,q):
        try:
            q.task_done()
        except:
            if args.debug: raise

    def base_url(self):
        return urlparse.urlsplit(args.url).hostname

    def get_links(self,response):
        # Get links from the response body using the BasicParser
        self.parser._read(response.text)
        for link in self.parser.links:
            matched=False
            if link is not None:
                for item in self.history + self.exclude + self.to_do:
                    if link == item:
                        matched=True
                if not matched:
                    dom = urlparse.urlparse(link).hostname
                    if dom and self.ip == dig(dom):
                        self.to_do.append(link)

    def visited(self,url):
        # Iterating here for clarity, only full URL matches
        # should be considered 'visited'
        for item in self.history:
            if url==item:
                return
        self.history.append(url)

    # http://docs.python-requests.org/en/master/user/quickstart/
    def make_request(self,uri,auth=None,payload=None,method=requests.get):
        try:
            if auth is not None:
                # auth=('user','pass') login via HTTP
                return method(uri,auth=auth,timeout=args.timeout,cookies=self.jar)
            elif payload is not None:
                # payload={'key':'value'...} automatically form-encoded by requests
                return method(uri,data=payload,timeout=args.timeout,cookies=self.jar)
            else:
                assert method is not requests.post, \
                    color_wrap('[!] POST requests require data!',Color.ERR,args.logging)
                return method(uri,timeout=args.timeout,cookies=self.jar)
        except RequestException as e:
            color_log('[!] {} :: {}'.format(self.name,e.message),Color.ERR,'error')
            return

    def process_response(self,response):
        code = response.status_code
        head = response.headers
        body = response.text
        history = response.history
        cookies = response.cookies

        if code in range(200,210):
            self.get_links(response)
            self.stat_cache['crawled_count']+=1
            self.stat_cache['unique_urls'].append(response.url)
            if history:
                self.stat_cache['redirects'].extend(
                                    [u.status_code for u in history]
                                    )

            if cookies:
                # Parse cookie details here
                pass

    def clean_up(self):
        self._q_send(self.stats_q,self.stat_cache)
        self.q_task_done(self.stats_q)
        log.debug('[-] Cleanup complete, auto-joining')
        self.join()

    def execute(self):
        iteration = 0
        while not self.stop.wait(args.timeout):
            iteration += 1
            # Do normal execution
            try:
                request_start=time.clock()
                up_next = self.next_task()
                if up_next is None:
                    # Signals the end of the crawl when a negative or
                    # zero-value --maxtime parameter is passed
                    self.clean_up()
                    return
                response = self.make_request(self.next_task())
                self.stat_cache['times'].append(time.clock()-request_start)
            except:
                if args.debug: raise
                pass
                # catch stuff
            else:
                if response is not None:
                    self.process_response(response)

            diff=time.clock()-self.start
            if diff < args.speed:
                time.sleep(diff)

            # Don't flood the queue
            if iteration % 3 == 0:
                self._queue_send(self.stats_q,self.stat_cache)
                self._clear_stat_cache()

        # Clean up after stop request received
        # send any remaining results to stats_q
        log.debug('[*] {} :: Execution complete'.format(self.name))

        return

class BasicParser(HTMLParser):

    def __init__(self):
        self.links = self._generate_dict()
        self.scripts = self._generate_dict()

        for flag in ['in_head','in_body','in_foot']:
            setattr(self,flag,False)

    def _read(self,data):
        # Flush output before re-using
        self._lines = []
        self.reset()
        self.feed(data)

    def _generate_dict(self):
        return { 'head':[], 'body':[], 'foot':[], None:[] }

    def _current_phase(self):
        if self.in_body: return 'body'
        if self.in_head: return 'head'
        if self.in_foot: return 'foot'

    def _handle_anchor(self,attrs):
        for attr in attrs:
            if attr[0]=='href':
                self.links[self._current_phase()].append(attr[1])

    def _handle_script(self,attrs):
        script_type = None
        script_src = None

        for attr in attrs:
            if attr[0] == 'type':
                script_type = attr[1]
            elif attr[0] == 'src':
                script_src = attr[1]
        if script_type is not None or script_src is not None:
            self.scripts[self._current_phase()].append((script_type,script_src))

    def handle_starttag(self,tag,attrs):
        if tag=='body':
            self.in_body=True
        if tag=='head':
            self.in_head=True
        if tag=='foot':
            self.in_foot=True
        if tag=='a':
            self._handle_anchor(attrs)
        if tag=='script':
            self._handle_script(attrs)

    def handle_endtag(self,tag):
        if tag=='body':
            self.in_body=False
        if tag=='head':
            self.in_head=False
        if tag=='foot':
            self.in_foot=False

class FormCrawler(Spider):

    def _parse_form(self,frm):
        pass

def abort(exit_code):
    # Add code to safely exit
    color_log('[!] Beginning abort sequence',Color.ERR)
    stop.set()
    time.sleep(args.timeout)
    sys.exit(exit_code)

class PokeyCrawl():
    """ Primary application class """

    def __init__(self):
        # Initialize args, log, queue, and other object
        self.stat_q = stat_q
        self.form_q = form_q

        self._rename()

        self.expired = False
        self.start = time.time()
        log.debug('[*] PokeyCrawl initialized at {}'.format(self.start))

        # Status messaging
        log.debug('[*] Application started')
        log.debug('[*] Logger {} spawned'.format(log.name))

        if args.test:
            self.tester=AppTester()
            self.tester.print_args()

    def _rename(self):
        self.name='{} {}'.format(self.__class__.__name__,os.getpid())

    def prep_workers(self):
        worker_count=args.procs
        fc_count=args.procs/2 if args.forms else 0

        # Condense this section to a function once the logic
        # is fleshed out
        self.pool={}

        for count in [
                     (Spider,worker_count,stop),
                     (FormCrawler,fc_count,stop)
                     ]:
            self.gen_worker(*count)

        log.debug('[*] {} workers added to the pool'.format(len(self.pool)))

    def gen_worker(self,target,count,stop):
        # Populate the worker pool
        Proc = multiprocessing.Process
        params = (self.stat_q,self.form_q,stop)
        if args.verbose:
            log.debug('[-] Creating {} with {} parameter(s)'.format(
                        target.__name__, len(params))
                        )
        for i in xrange(count):
            p = Proc(target=target, args=(params,))
            self.pool[p.name]=p

    def _poll(self):
        try:
            result = self.stat_q.get(False,args.timeout)
        except Empty:
            # ignore empty queue reads
            return

        for key in result:
            # Increment the counters
            getattr(args.s,key).increment(args.s[key])
        log.debug('[*] {} :: {} counter(s) incremented'.format(
                                            self.name,len(result))
                                            )

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
            pass

        self.start_workers()
        while True:
            if time.time()-self.start > args.maxtime:
                log.debug('[*] {} :: Time Expired!'.format(self.name))
                break
            self._poll()
            # Don't flood queue reads
            time.sleep(0.01)
        stop.set()
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
