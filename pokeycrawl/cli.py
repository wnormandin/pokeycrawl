#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

import argparse
import logging
log = logging.getLogger('pokeycrawl')


def parse_arguments(args):

    def add_arg(arg,boolean=False):
        flag='-{}'.format(arg[0][0][0]) if arg[0][1] else None
        name='--{}'.format(arg[0][0])
        if args.test:
            log.debug(' - Argument received: {}'.format(arg))
        if boolean:
            if flag is not None:
                parser.add_argument(flag,name,help=arg[1],action=arg[2])
            else:
                parser.add_argument(name,help=arg[1],action=arg[2])
        else:
            if flag is not None:
                parser.add_argument(flag,name,type=arg[1],
                                    help=arg[2],default=arg[3])
            else:
                parser.add_argument(name,type=arg[1],
                                    help=arg[2],default=arg[3])

    # Defines options for command-line invocation
    parser = argparse.ArgumentParser(
            description="Crawl and index websites.  Set default values in config.py",
            prog='pokeycrawl',
            usage="%(prog)s [options] URL"
            )

    # Boolean (flags)
    flags=[[('forms',True),'enable form crawling'],
           [('vary',True),'vary the user-agent using docs/ua.txt'],
           [('debug',True),'enable debug messages and error raising'],
           [('report',True),'display a post-execution summary'],
           [('index',True),'save an index file in tests/URL_EPOCH'],
           [('gz',False),'accept gzip compression (experimental)'],
           [('robots',False),'process robots.txt directives (experimental)'],
           [('verbose',False),'display verbose HTTP transfer output'],
           [('silent',False),'silence URL crawl notifications'],
           [('logging',True),'enable logging output to file'],
           [('yes',True),'assume "yes" for any prompts'],
           [('test',True),'basic test, does not send requests'],
           [('parse',False),'parse pages for forms (more resource-intensive)']
           ]

    # Parameters
    params=[[('speed',True),float,'set the crawl speed'],
            [('ua',False),str,'specify a user-agent string'],
            [('procs',True),int,'max worker threads'],
            [('maxtime',False),int,'maximum run time in seconds'],
            [('logpath',False),str,'specify a log path']
            ]

    for f in flags:
        # Examine the default in config.py and process
        # accordingly
        store=getattr(args,f[0][0])
        if store:
            f.append('store_false')
        else:
            f.append('store_true')
        add_arg(f,True)

    for p in params:
        # Set defaults for parameters from config.py
        p.append(getattr(args,p[0][0]))
        add_arg(p,False)

    parser.add_argument('url',type=str,help='The URL to crawl')
    # The --robots and --gz arguments are experimentally supported in 
    # mechanize, check your mechanize version for details and potential
    # issues.

    return parser.parse_args()
