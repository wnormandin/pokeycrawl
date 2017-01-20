#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

"""
This utility uses multiprocessing to crawl websites, simulating multiple users
in order to load-test website functionality or simply to index the URLs within
a site.
https://github.com/wnormandin/pokeycrawl
"""
# HTTP requests and parsing
import requests
from requests.exceptions import RequestException,ConnectionError,Timeout
import urlparse

# Utility Modules
import random
import os, sys

# Multiprocessing dependencies
import multiprocessing
from multiprocessing import Queue
from HTMLParser import HTMLParser
from Queue import Empty

# Date and time manipulation modules
from time import sleep
from datetime import datetime, timedelta, time
import tzlocal
strftime = time.strftime

def ts():
    # Timestamp function
    # is_dst=None raises an error if no local tz available
    return tzlocal.get_localzone().localize(datetime.now(),is_dst=None)

this = sys.modules[__name__] # grab module instance
this.start = ts()
this.meta={
          'func_calls':{},
          'execution_time':0
          }

# Module imports
from config import args as defaults
from log import setup_logger
from cli import parse_arguments, check_args
from _util import Stats, user_prompt, report, dig, Color,color_wrap
from _util import do_progress_bar

def counted(func):
    # Wrapper to count primary application function calls
    def wrapper(*args, **kwargs):
        # Aggregate using Stats.<key>.count.increment()
        if not meta['func_calls'].get(func.__name__):
            meta['func_calls'][func.__name__]=1
        else:
            meta['func_calls'][func.__name__]+=1
        return func(*args, **kwargs)
    return wrapper

class Crawler(object):
    """ Base class for crawler objects """

    def __init__(self,stats,forms,stop):
        self.start = ts()
        self.pid = os.getpid()
        self._clear_stat_cache()
        self.absolute_history=[] # when history is cleared, add unique urls

        self.stats_q = stats
        self.form_q = forms
        self.stop = stop

        if app_args.test or app_args.verbose:
            log.debug('[-] {} started'.format(self.name))

    #@counted
    def _clear_stat_cache(self):
        if app_args.test or app_args.verbose:
            log.debug('[-] {} :: _clear_stat_cache() called'.format(self.name))
        self.stat_cache = {}
        for counter in Stats.counters:
            self.stat_cache[counter]=0
        for list_count in Stats.list_counters:
            self.stat_cache[list_count]=[]

    @property
    def name(self):
        return '{} {}'.format(self.__class__.__name__,self.pid)

    @property
    def f_queue_next(self):
        return self.form_q.get(True,app_args.timeout)

    @f_queue_next.setter
    def f_queue_next(self,data):
        self.queue_write(self.form_q,data)

    @property
    def s_queue_next(self):
        return self.stats_q.get(True,app_args.timeout)

    @s_queue_next.setter
    def s_queue_next(self,data):
        self.queue_write(self.stats_q,data)

    def queue_write(self,q,d):
        try:
            for item in d:
                if d[item]:
                    if app_args.test:
                        log.debug('[-] {} :: sending {}:{} to queue {}'.format(
                                                            self.name,
                                                            item,
                                                            d[item],
                                                            q))
                    q.put({item:d[item]})
        except TypeError:
            if d is None:
                q.put(None)
            else:
                raise

    def execute(self):
        while not self.stop.wait(app_args.speed):
            pass
        color_log('[*] {}::kill signal received'.format(self.name),
                Color.MSG)
        self.s_queue_next = None # signal task completion

class Spider(Crawler):

    """ Base class for Spider objects (Spider,FormCrawler) """

    def __init__(self,arg_list):
        # Explicitly calling super(Crawler...) to avoid infinite loop
        # in the FormCrawler child
        Crawler.__init__(self,*arg_list)

        if app_args.verbose: log.debug(
                    '[-] {} :: initializing attributes'.format(self.name)
                    )
        self.cached_ips = {} # cache IPs to minimize dig() ops
        self.history = []   # request history
        self.exclude = []   # URLs to be excluded from future requests
        self.to_do = []     # list of found URLs to be processed
        self.parser = BasicParser()
        if app_args.test:
            self.tester = AppTester()

        self.ip = dig(self.cached_ips,app_args.url)

        # Set up cookie support
        if app_args.verbose: log.debug(
                    '[-] {} :: Cookie jar created'.format(self.name)
                    )
        self.jar = requests.cookies.RequestsCookieJar()

        # Start the crawl
        try:
            self.execute()
        except KeyboardInterrupt:
            self.clean_up()

    def next_task(self):
        # Default behavior is to start at the beginning
        # when the list of unique links has been visited
        if self.to_do:
            retval = random.choice(self.to_do)
            self.visited(retval)
            self.to_do.remove(retval)
            return retval
        else:
            if app_args.maxtime==0:
                color_log('[!] {} :: Out of links!  Crawl complete'.format(
                                                         self.name),Color.MSG)
                return
            # Restart the crawl
            self.absolute_history.extend(self.history)
            self.absolute_history = list(set(self.absolute_history))
            self.history = []
            return app_args.url

    @property
    def base_url(self):
        return urlparse.urlsplit(app_args.url).hostname

    #@counted
    def get_links(self,response):
        # Get links from the response body using the BasicParser
        # Need to prefer <body> URLs over head/foot
        self.parser._read(response.text,response.url)
        for phase in self.parser.links:
            for link in self.parser.links[phase]:
                matched=False
                if link is not None:
                    for item in self.history + self.exclude + self.to_do:
                        if link == item:
                            matched=True
                    if not matched:
                        dom = urlparse.urlparse(link).hostname
                        if dom and self.ip == dig(self.cached_ips,dom):
                            if dom not in self.absolute_history:
                                if app_args.verbose:
                                    log.debug('[-] {} :: To-Do:{}'.format(
                                                        self.name,
                                                        link
                                                        ))
                            self.to_do.append(link)

    def visited(self,url):
        # Iterating here for clarity, only full URL matches
        # should be considered 'visited'
        for item in self.history:
            if url==item:
                return
        self.history.append(url)

    # http://docs.python-requests.org/en/master/user/quickstart/
    @counted
    def make_request(self,uri,auth=None,payload=None,method=requests.get):
        if (not app_args.silent) or app_args.debug:
            log.info('[*] {} :: crawling {}'.format(self.name,uri))
        try:
            if auth is not None:
                # auth=('user','pass') login via HTTP
                return method(uri,auth=auth,timeout=app_args.timeout,cookies=self.jar)
            elif payload is not None:
                # payload={'key':'value'...} automatically form-encoded by requests
                return method(uri,data=payload,timeout=app_args.timeout,cookies=self.jar)
            else:
                assert method is not requests.post, \
                    color_wrap('[!] POST requests require data!',Color.ERR,app_args.logging)
                return method(uri,timeout=app_args.timeout,cookies=self.jar)
        except Timeout:
            self.stat_cache['timeouts'].append(uri)
            sleep(app_args.speed)
            return
        except RequestException as e:
            color_log('[!] {} :: {}'.format(self.name,e.message),Color.ERR,'error')
            self.stat_cache['response_codes'].append(500)
            self.stat_cache['errors'].append(e[0])
            self.stat_cache['error_urls'].append(uri)
            return

    @counted
    def process_response(self,response):
        code = response.status_code
        self.stat_cache['response_codes'].append(code)
        head = response.headers
        body = response.text
        history = response.history
        cookies = response.cookies

        if app_args.test:
            self.tester.response_details(response)

        self.stat_cache['crawled_count']+=1

        if history:
            self.stat_cache['redirects'].extend(
                                [u.status_code for u in history]
                                )

        if code in xrange(199,400):
            self.get_links(response)
            if cookies:
                # Parse cookie details here
                pass
        else:
            self.stat_cache['errors'].append(response.head)
            self.stat_cache['error_urls'].append(response.url)

    def clean_up(self):
        self.s_queue_next = self.stat_cache
        log.debug('[-] Cleanup complete')

    def execute(self):
        iteration = 0
        while not self.stop.wait(app_args.speed):
            iteration += 1
            # Do normal execution
            try:
                request_start = ts()
                up_next = self.next_task()
                if up_next is None:
                    # Signals the end of the crawl when a negative or
                    # zero-value --maxtime parameter is passed
                    self.clean_up()
                    return
                next_url = self.next_task()
                response = self.make_request(next_url)
                self.stat_cache['unique_urls'].append(next_url)
                self.stat_cache['times'].append(tdiff(request_start,ts()))
            except:
                if app_args.debug: raise
                # Add more specific exception handling here
                # check for errors likely to be raised from 
                # called methods
            if response is not None:
                self.process_response(response)

            diff=tdiff(self.start,ts())
            if diff < app_args.speed:
                sleep(diff)

            # Don't flood the queue
            if iteration % 3 == 0:
                self.s_queue_next = self.stat_cache
                self._clear_stat_cache()

        # Clean up after stop request received
        # send any remaining results to stats_q
        self.clean_up()
        self.s_queue_next = None # signal completion
        log.debug('[*] {} :: Execution complete'.format(self.name))
        return

class FormCrawler(Spider):

    def __init__(self,arg_list):
        Crawler.__init__(self, *arg_list)

        iteration = 0
        while not self.stop.wait(app_args.timeout):
            iteration += 1

            try:
                next_form = self.f_queue_next
            except Empty:
                continue # ignoring empty queue reads

            if next_form is not None:
                url,data = next_form
            else:
                continue # not doing anything with None atm

            self.handle_form(data) # Process the form, send request, get stats

            if iteration % 3 == 0:
                # send back collected stats
                pass

class BasicParser(HTMLParser):

    def __init__(self):
        self.links = self._generate_dict()
        self.scripts = self._generate_dict()

        for flag in ['in_head','in_body','in_foot']:
            setattr(self,flag,False)

    def _read(self,data,url):
        # Flush output before re-using
        self.req_url = url
        self._lines = []
        self.reset()
        self.feed(data)

    def _generate_dict(self):
        return { 'head':[], 'body':[], 'foot':[], None:[] }

    def _current_phase(self):
        if self.in_body: return 'body'
        if self.in_head: return 'head'
        if self.in_foot: return 'foot'

    def _validate(self,parsed):
        if not parsed.scheme:
            return
        return parsed.geturl()

    def _handle_anchor(self,attrs):
        for attr in attrs:
            if attr[0]=='href':
                parsed = urlparse.urlparse(attr[1])
                fqdn = self._validate(parsed)
                if fqdn:
                    self.links[self._current_phase()].append(fqdn)

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


@counted
def abort(exit_code):
    # Add code to safely exit
    color_log('[!] Beginning abort sequence',Color.ERR)
    stop.set()
    # Give workers time to exit
    sleep(app_args.speed)
    sys.exit(exit_code)

class PokeyCrawl(Crawler):
    """ Primary application class """

    def __init__(self,stats_q,form_q,stop):
        # Initialize args, log, queue, and other object
        self.stats_q = stats_q
        self.form_q = form_q
        self.stop = stop
        self.pid = os.getpid()
        self.worker_count=app_args.procs

        self.expired = False
        self.start = ts()
        log.info('[*] PokeyCrawl initialized at {}'.format(
                                                format_time(self.start)
                                                ))

        # Status messaging
        log.debug('[*] Application started')
        log.debug('[*] Logger {} spawned'.format(log.name))

        if app_args.test:
            self.tester=AppTester()
            self.tester.print_args()

    @property
    def name(self):
        return '{} {}'.format(self.__class__.__name__,self.pid)

    def prep_workers(self):
        fc_count=self.worker_count/2 if app_args.forms else 0

        # Condense this section to a function once the logic
        # is fleshed out
        self.pool={}

        for count in [
                     (Spider,self.worker_count),
                     (FormCrawler,fc_count)
                     ]:
            self.gen_worker(*count)

        log.debug('[*] {} workers added to the pool'.format(len(self.pool)))

    def gen_worker(self,target,count):
        # Populate the worker pool
        Proc = multiprocessing.Process
        params = (self.stats_q,self.form_q,self.stop)
        if app_args.verbose:
            log.debug('[-] Creating {} with {} parameter(s)'.format(
                        target.__name__, len(params))
                        )
        for i in xrange(count):
            p = Proc(target=target, args=(params,))
            self.pool[p.name]=p

    @counted
    def _poll(self):
        try:
            result = self.s_queue_next
            if app_args.test:
                log.debug('[-] {} :: queue read ({})'.format(self.name,result))
        except Empty:
            # ignore empty queue reads
            if app_args.test:
                log.debug('[-] {} :: queue empty'.format(self.name))
            return
        if result is not None:
            for key in result:
                # Increment the counters
                app_args.s.next_count((key,result[key]),app_args.test)
        else:
            return
        return len(result)

    def start_workers(self):
        for worker in self.pool:
            self.pool[worker].start()

    def join_workers(self):
        self.stop.set()
        for worker in self.pool:
            self.pool[worker].join()

    def init_stats(self,s):
        app_args.s=s
        if app_args.test:
            self.tester.initial_stats(s)

    def execute(self,test=False):
        if app_args.verbose:
            log.debug('[*] {} :: execute() invoked'.format(self.name))
        if test:
            pass

        self.start_workers()
        while True:
            if tdiff(self.start,ts()) > app_args.maxtime:
                color_log('[*] {} :: Time Expired!'.format(self.name),
                        Color.MSG)
                break
            self._poll()
            # Don't flood queue reads
            sleep(0.01)
        self.stop.set()
        self.join_workers()
        self.wrap_up()

    def wrap_up(self):
        # Perform final queue collection
        if app_args.verbose:
            log.debug('[-] {} :: Wrap-up started'.format(self.name))
        while True:
            if self._poll() is None:
                break
            sleep(0.01)
        if app_args.verbose:
            log.debug('[-] {} :: Wrap-up complete'.format(self.name))

class AppTester():
    """ Performs various tests when --test is passed """

    def __init__(self):
        self.col = Color.TST

    def _log(self,msg):
        #color_log(msg,self.col)
        log.info(msg)

    def print_args(self):
        self._log('[!] -*- Parameter Values -*-')
        for arg in vars(app_args):
            self._log('[-] {} :: {}'.format(
                                        arg,
                                        getattr(app_args,arg)
                                        ))
        self._log('[!] -*- End Parameter List -*-')

    def get_text_result(self,bool_result,col=False):
        if bool_result:
            msg=color_wrap('PASS',Color.GREEN)
        else:
            msg=color_wrap('FAIL',Color.RED)

        return msg

    def response_details(self,response):

        if response.status_code in range(200,210):
            code_color = Color.GREEN
        else:
            code_color = Color.RED

        for item in ['history','cookies']:
            attr = getattr(response,item)
            if len(attr)>0:
                col = Color.GREEN
            else:
                col = Color.RED
            setattr(self,item,color_wrap(len(attr),col))

        log_str = '[!] Response :: '
        log_str += 'URL:{}, Result:{}, Cookies:{}, Redirects:{}'.format(
                response.url, color_wrap(response.status_code,code_color),
                self.cookies, self.history)
        self.cookies = None
        self.history = None

        head_str = '[!] Headers :: '
        for item in ['Content-Length','Content-Encoding',
                    'Server','Vary','Cache-Control','Date']:
            if item in response.headers:
                head_str += '{}:{}, '.format(item,response.headers[item])

        self._log(log_str)
        self._log(head_str[:-2])

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

        self._log('[!] -*- Crawl Stats Initialized -*-')
        self._log('[!] -*- Testing Counters -*-')

        test_result = self.get_text_result(__increment_counters())
        self._log('[!] -*- Counters: {} -*-'.format(test_result))

        for item in vars(stats):
            self._log('[-] {} :: {}'.format(
                                        item,
                                        getattr(stats,item).count
                                        ))
        stats.refresh()
        self._log('[!] -*- End Initial Stats -*-')

def color_log(msg,color,method='debug'):
    getattr(log,method)(color_wrap(msg,color,app_args.logging))

def format_time(timestamp,date=True):
    # Convert dates to pretty format for printing
    if not date:
        # Allow for flexible parsing
        return
    fmt = '%Y-%m-%d::%T:%z'
    return timestamp.strftime(fmt)

def tdiff(t1,t2):
    # calculates the diff of t1 and t2
    # t1 and t2 are datetime.datetime objects
    # diff is a timedelta
    diff = t1-t2
    return abs(diff.total_seconds())

if __name__=='__main__':
    # When the script is executed or invoked via python -m,
    # parse command-line arguments and setup the logger
    # args/log _must_ exist at a module level when not invoking
    # at the command line.
    this.app_args = parse_arguments(defaults)
    check_args(app_args)
    this.log = setup_logger(app_args)

    stats_q = Queue() # Statistics Queue - might not be necessary
    form_q = Queue() # Queue for sending forms to the FormCrawler
    this.stop = multiprocessing.Event() # Event to handle kill signalling
    items = stats_q,form_q,stop # Application control items

    try:
        app = PokeyCrawl(*items)
        app.init_stats(Stats())
        app.prep_workers()
        color_log('[!] Preparations complete, crawl commencing',Color.MSG,'info')
        app.execute(True)
        color_log('[!] Application Executed',Color.MSG,'info')
        meta['execution_time'] = tdiff(ts(),this.start)
        meta['interrupted'] = False
        if app_args.report:
            report(app_args,meta)
    except KeyboardInterrupt,SystemExit:
        meta['execution_time'] = tdiff(ts(),this.start)
        meta['interrupted'] = True
        msg = '[!] KeyboardInterrupt detected, aborting (Ctrl+C again to exit)'
        color_log(msg,Color.ERR,'error')
        stop.set()
        sleep(app_args.timeout)
        if app_args.report:
            report(app_args,meta)
        abort(0)
    except Exception as e:
        if app_args.debug: raise
        abort(1)
