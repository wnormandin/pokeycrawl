# -*- coding: utf-8 -*-
import operator
import socket
import logging
import multiprocessing
import os, sys
import time
import urlparse
log = logging.getLogger('pokeycrawl')


# Uses ascii color codes, may not play nicely with all terminals
class Color:
    BLACK_ON_GREEN = '\x1b[1;30;42m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    DARKCYAN = '\033[36m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'
    MSG = '\x1b[1;32;44m'
    ERR = '\x1b[1;31;44m'
    TST = '\x1b[7;34;46m'

def color_wrap(val,color,logging=False):
    if logging:
        return val
    return '{}{}{}'.format(color,val,Color.END)

def do_progress_bar(max_time):
    # Disable output buffering for inline updates

    def __progress_step(char,interval):
        percent=((orig_max-interval)/float(orig_max))*100
        if percent >= 75:
            return color_wrap(char,Color.BLUE)
        elif percent >= 50:
            return color_wrap(char,Color.GREEN)
        elif percent >= 25:
            return color_wrap(char,Color.YELLOW)
        else:
            return color_wrap(char,Color.RED)

    sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)
    start = time.clock()
    max_width = 40          # Progress bar width
    orig_max = max_width
    interval = max_time/float(max_width)  # loop interval will scale
    print(__progress_step('@',max_width)),
    max_width -= 1
    while True:
        if max_width <= 0:
            print(__progress_step('@',max_width))
            return
        else:
            print(__progress_step('>',max_width)),
            time.sleep(interval)
            max_width -= 1

def dig(cache,dom):
    dom = dom.replace('http://','')
    dom = dom.replace('https://','')
    #log.debug('[-] Digging: {}'.format(dom))
    if dom in cache: return cache[dom]
    try:
        cache[dom]=ip=socket.gethostbyname(dom)
    except Exception:
        log.error(color_wrap('[!] Dig failed: {}'.format(dom),Color.ERR))
        return
    return ip

def report(args,meta):

    def __try_op(op,val,err_val=0):
        try:
            return op(val)
        except TypeError:
            if args.test: raise
            return err_val

    def _error_counts(errs):
        # Get unique errors
        uniq = set(errs)
        counts = {}
        for err in uniq:
            counts[err] = 0
            for line in errs:
                if err == line:
                    counts[err]+=1

        return sorted(counts.items(), key=operator.itemgetter(1))[:4]

    def _p(msg,col=None):
        if col is not None:
            print color_wrap(msg,col)
            return
        print msg

    def _lsort(l):
        return sorted((str(i) for i in l), key=len)
        #return l.sort(key=lambda item: (len(item),item))

    def _p_list(l,tab='\t'):
        # Prints list contents in length-alphabetical order
        # tab char is flexible
        if l is not None and l:
            for item in _lsort(l):
                _p('{}{}'.format(tab,item))

    stats = args.s
    try:
        bar = '============================='
        _p('{}{}'.format('\n',bar),Color.GREEN)
        _p('Metadata',Color.MSG)
        _p('Queue Reads       : {}'.format(meta['func_calls']['_poll']))
        _p('Execution Time    : {}s'.format(meta['execution_time']))
        col = Color.ERR if meta['interrupted'] else Color.GREEN
        _p('Interrupted       : {}'.format(meta['interrupted']),col)
        _p('{}'.format(bar),Color.GREEN)
        _p('Crawl Statistics',Color.MSG)
        _p('Links crawled     : {}'.format(stats.crawled_count.count))
        _p('Unique urls       : {}'.format(len(stats.unique_urls.count)))
        if args.detailed: _p_list(stats.unique_urls.count)
        _p('Redirect Count    : {}'.format(len(stats.redirects.count)))
        if args.detailed: _p_list(stats.redirects.count)
        try:
            avg_time = sum(stats.times.count)/float(len(stats.times.count))
        except:
            avg_time = 0
        _p('Avg load time     : {:.5f}s'.format(avg_time))
        _p('\tMax time  : {:.5f}s'.format(__try_op(max,stats.times.count)))
        _p('\tMin time  : {:.5f}s'.format(__try_op(min,stats.times.count)))
        _p('\tTotal     : {:.5f}s'.format(__try_op(sum,stats.times.count)))

        try:
            msg = __try_op(sum,stats.url_counts.count,1)/float(
            __try_op(len,stats.url_counts.count,1))
        except ZeroDivisionError:
            msg = 0
        _p('Avg URLs/page     : {:.2f}'.format(msg))
        _p('URLs skipped      : {}'.format(stats.external_skipped.count))
        _p('Request Timeouts  : {}'.format(len(stats.timeouts.count)))
        if args.detailed and stats.timeouts.count:
            for timeout in set(stats.timeouts.count):
                msg = stats.timeouts.count.count(timeout)
                _p('\t{} : {}'.format(timeout,msg),Color.YELLOW)

        _p('Status Codes      : {}'.format(len(stats.response_codes.count)))
        if args.detailed and stats.response_codes.count:
            for code in set(stats.response_codes.count):
                if code in xrange(200,210):
                    col = Color.GREEN
                else:
                    col = Color.YELLOW
                msg = color_wrap(stats.response_codes.count.count(code),col)
                code = color_wrap(code,col)
                _p('\t{}\t  : {}'.format(
                     code,msg
                     ))

        url_err_set = __try_op(set,stats.error_urls.count,[0])
        _p('URLs with Errors  : {}'.format(
                __try_op(len,url_err_set)),Color.YELLOW)
        _p('Errors returned   : {}'.format(
                __try_op(len,stats.errors.count)),Color.YELLOW)
        _p('{}{}'.format(bar, '\n'),Color.GREEN)

        # Option to display error list
        if len(url_err_set)>0:
            if not args.yes:
                ch = raw_input('View error detail? (y/n) > ').lower()
            if args.yes or (ch=='y'):
                _p('[!] Displaying top 5 errors',Color.ERR)
                srtd_list = _error_counts(stats.errors.count)
                for key in srtd_list[:5]:
                    print(' * {} : count[{}]'.format(key[0],key[1]))

    except Exception as e:
        if args.debug: raise
        log.info('[*] Exception in report(): {},{}'.format(e,str(e)))

class Counter():
    def __init__(self,name,counter_type=None):
        # Counter class, limited support of the following
        # formats.  Increment operation is thread-safe
        self.lock = multiprocessing.Lock()
        self.name=name
        self.type=counter_type
        if counter_type is None:
            self.count=0
        else:
            # Supported types - any iterable
            self.count=counter_type()

    def increment(self,val=None,verbose=False):
        if verbose:
            log.debug('[-] Counter:{} :: Waiting for lock'.format(self.name))
        self.lock.acquire()
        try:
            if verbose:
                log.debug('[-] Counter:{} :: Lock acquired'.format(self.name))
            if self.type is None:
                if val is not None:
                    self.count+=val
                else:
                    self.count+=1
            elif self.type is list:
                try:
                    if isinstance(val,list):
                        self.count.extend(val)
                    else:
                        self.count.append(val)
                except:
                    raise
            elif self.type is dict:
                    self.count[val]+=1
            try:
                length=len(self.count)
            except TypeError:
                length = self.count
            if verbose:
                log.debug('[-] Counter:{} :: length:{}'.format(
                                    color_wrap(self.name,Color.MSG),
                                    color_wrap(length,Color.MSG)))
        finally:
            self.lock.release()

        if self.name in ('unique_urls','error_urls','form_urls','redirects'):
            self.unique_count()

    def unique_count(self):
        assert isinstance(self.count,list), \
            'Invalid counter type for unique: {}'.format(type(self.count))
        self.count = list(set(self.count))

class Stats:

    """ Various counters/convenience methods for reporting """

    counters = ['crawled_count','external_skipped','forms_crawled',
                'forms_parsed']

    list_counters = ['errors','error_urls','times','url_counts', 'timeouts',
                    'response_codes','unique_urls','form_urls','redirects',
                    'function_calls']

    def __init__(self):
        self.refresh()

    def refresh(self):
        # re-initialize each counter
        for counter in Stats.counters:
            setattr(self,counter,Counter(counter))

        for list_count in Stats.list_counters:
            setattr(self,list_count,Counter(list_count,list))

        log.debug('[*] Statistics Refreshed')

    def next_count(self,args,verbose=False):
        key,val=args
        getattr(self,key).increment(val,verbose)

def user_prompt(args,msg):
    if not args.yes:
        ch = raw_input(msg).upper()
    if args.yes or (ch=='Y'):
        return True
    return False
