# -*- coding: utf-8 -*-
import operator
import socket
import logging

log = logging.getLogger('pokeycrawl')

def dig(cache,dom):
    if dom in cache: return cache[dom]
    try:
        cache[dom]=ip=socket.gethostbyname(dom)
    except Exception as e:
        log.debug(' - exception raised in _utils.dig')
        return
    return ip

def report(args):
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
        print('\nAvg URLs/page     : {:.2f}'.format(
								sum(stats.url_counts)/float(len(stats.url_counts))
								))
        print('URLs skipped      : {}'.format(stats.external_skipped))

        url_err_set = set(stats.err['urls'])
        print('\nURLs with Errors  : {}'.format(len(url_err_set)))
        print('Errors returned   : {}'.format(len(stats.err['errors'])))
        print bar, '\n'

        # Option to display error list
        if len(url_err_set)>0:
            if not args.yes:
                ch = raw_input('View error detail? (y/n) > ').lower()
            if args.yes or (ch=='y'):
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
            pass

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
        except TypeError:
            self.err['errors'][deets['error']] = 1

def user_prompt(args,msg):
    if not args.assume_yes:
        ch = raw_input(msg).upper()
    if args.assume_yes or (ch=='Y'):
        return True
    return False
