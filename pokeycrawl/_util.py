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
    except Exception as e:
        log.error('[!] exception raised in _utils.dig:{}'.format(e))
        return
    return ip

def report(args):

    def __try_op(val,op,err_val=0):
        try:
            return op(val)
        except TypeError:
            return err_val

    stats = args.s
    try:
        bar = color_wrap('=============================',Color.GREEN)
        print '\n', bar
        print('Links crawled     : {}'.format(stats.crawled_count.count))
        try:
            avg_time = sum(stats.times.count)/float(len(stats.times.count))
            print('Avg load time     : {:.5f}'.format(avg_time))
        except:
            print('0')
        print('\tMax time  : {:.5f}'.format(__try_op(max,stats.times.count)))
        print('\tMin time  : {:.5f}'.format(__try_op(min,stats.times.count)))
        print('\tTotal     : {:.5f}'.format(__try_op(sum,stats.times.count)))
        print('\nAvg URLs/page     : {:.2f}'.format(
            __try_op(sum,stats.url_counts.count,1)/float(
            __try_op(len,stats.url_counts.count,1)
            )))
        print('URLs skipped      : {}'.format(stats.external_skipped.count))

        print('Status Codes      :')
        for code in set(stats.response_codes.count):
            print('\t{} : {}'.format(
                 code,stats.response_codes.count.count(code)
                 ))

        url_err_set = __try_op(set,stats.error_urls.count,[0])
        print('\nURLs with Errors  : {}'.format(color_wrap(
            __try_op(len,url_err_set),Color.YELLOW)
            ))
        print('Errors returned   : {}'.format(color_wrap(
            __try_op(len,stats.errors.count),Color.YELLOW)
            ))
        print bar, '\n'

        # Option to display error list
        if len(url_err_set)>0:
            if not args.yes:
                ch = raw_input('View error detail? (y/n) > ').lower()
            if args.yes or (ch=='y'):
                print(color_wrap('[!] Displaying top 5 errors',Color.ERR))
                srtd_list = sorted(
                                stats.errors.count,
                                key=operator.itemgetter(1)
                                )
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
        finally:
            self.lock.release()

class Stats:

    """ Various counters/convenience methods for reporting """

    counters = ['crawled_count','external_skipped','forms_crawled',
                'forms_parsed']

    list_counters = ['errors','error_urls','times','url_counts',
                    'response_codes','unique_urls','form_urls','redirects']

    def __init__(self):
        self.refresh()

    def refresh(self):
        # re-initialize each counter
        for counter in Stats.counters:
            setattr(self,counter,Counter(counter))

        for list_count in Stats.list_counters:
            setattr(self,list_count,Counter(list_count,list))

        log.debug('[*] Statistics Refreshed')

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
            pass

        self.unique_urls.append(new)
        self.unique_urls = list(__unique(sorted(self.unique_urls)))

    def crawled(self,count,url_counts,external_skipped):
        # increment the crawled_count
        self.crawled_count.increment()
        self.url_counts.increment(url_counts)
        self.external_skipped.increment(external_skipped)

    def time(self,times):
        # add times to the list for averaging
        self.times.increment(times)

    def error(self,deets):
        # increment each error encountered
        # deets['url], deets['error']
        self.error_urls.increment(deets['url'])
        self.errors.increment(deets['error'])

def user_prompt(args,msg):
    if not args.assume_yes:
        ch = raw_input(msg).upper()
    if args.assume_yes or (ch=='Y'):
        return True
    return False
