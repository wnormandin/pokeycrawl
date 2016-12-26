# -*- coding: utf-8 -*-
import operator
import socket
import logging
import threading

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

def color_wrap(val,color):
	return '{}{}{}'.format(color,val,Color.END)

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
        bar = color_wrap('=============================',Color.GREEN)
        print '\n', bar
        print('Links crawled     : {}'.format(stats.crawled_count.count))
        try:
            avg_time = sum(stats.times.count)/float(len(stats.times.count))
            print('Avg load time     : {:.5f}'.format(avg_time))
        except:
            print('0')
        print('\tMax time  : {:.5f}'.format(max(stats.times.count)))
        print('\tMin time  : {:.5f}'.format(min(stats.times.count)))
        print('\tTotal     : {:.5f}'.format(sum(stats.times.count)))
        print('\nAvg URLs/page     : {:.2f}'.format(
								sum(stats.url_counts.count)/float(len(
												stats.url_counts.count))
								))
        print('URLs skipped      : {}'.format(stats.external_skipped.count))

        url_err_set = set(stats.error_urls.count)
        print('\nURLs with Errors  : {}'.format(
							color_wrap(len(url_err_set)),Color.YELLOW))
        print('Errors returned   : {}'.format(
							color_wrap(len(stats.errors.count)),Color.YELLOW))
        print bar, '\n'

        # Option to display error list
        if len(url_err_set)>0:
            if not args.yes:
                ch = raw_input('View error detail? (y/n) > ').lower()
            if args.yes or (ch=='y'):
                print(color_wrap('[*] Displaying top 5 errors',Color.RED))
                srtd_list = sorted(
                                stats.errors.count.items(),
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
		self.lock = threading.Lock()
		self.name=name
		self.type=counter_type
		if counter_type is None:
			self.count=0
		else:
			# Supported types - any iterable
			self.count=counter_type()

	def increment(self,val=None):
		log.debug('[-] Counter:{} :: Waiting for lock'.format(self.name))
		self.lock.acquire()
		try:
			log.debug('[-] Counter:{} :: Lock acquired'.format(self.name))
			if self.type is None:
				if val is not None:
					self.count+=val
				else:
					self.count+=1
			else:
				try:
					self.count.extend(val)
				except:
					try:
						self.count[val]+=1
					except:
						log.debug('[!] Unable to increment, Value: {} :: {}'.format(
									val,type(self.count)))
		finally:
			self.lock.release()

class Stats:

    """ Stores various counters/convenience methods for reporting """

    def __init__(self):
        self.refresh()

    def refresh(self):
        # re-initialize each counter
		for counter in ['crawled_count','external_skipped']:
			setattr(self,counter,Counter(counter))

		for list_count in ['errors','error_urls','times','url_counts','unique_urls']:
			setattr(self,list_count,Counter(list_count,list))

		log.debug('[@] Counters initialized')

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
