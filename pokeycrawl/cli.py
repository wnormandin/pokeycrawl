#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

import argparse

def parse_arguments():

    # Defines options for command-line invocation
    parser = argparse.ArgumentParser()

    parser.add_argument('url',type=str,help='The URL to crawl')
    parser.add_argument('-s','--speed',type=float,default=0.15,
                help='set the crawl speed (defaults to 0.15s)')
    parser.add_argument('-f','--forms',action='store_true',
                help='submit (safe) dummy data to forms found in responses')
                # http://www.pythonforbeginners.com/cheatsheet/python-mechanize-cheat-sheet
                # ideas - add a list of page titles in the reporting
                # report on the size of the data collected
                #
                # try login forms with dummy data:
                # If the protected site didn't receive the authentication data you would
                # end up with a 410 error in your face
                # br.add_password('http://safe-site.domain', 'username', 'password')
                # br.open('http://safe-site.domain')
    parser.add_argument('-v','--vary',action='store_true',
                help='vary the user-agent (requires a list in docs/ua.txt)')
    parser.add_argument('-d','--debug',action='store_true',
                help='enable debug (verbose) messages')
    parser.add_argument('-p','--procs',type=int,default=4,
                help='concurrent processes (~=simulated visitors)')
    parser.add_argument('-r','--report',action='store_true',
                help='display post-execution summary')
    parser.add_argument('-i','--index', action='store_true',
                help='stores an index in tests/ in the format URL_EPOCH')
    parser.add_argument('--ua',type=str,
                help='specify a user-agent (overrides -v)')
    parser.add_argument('--gz',action='store_true',
                help='accept gzip compression (experimental)')
    parser.add_argument('--robots', action='store_true',
                help='honor robots.txt directives')
    parser.add_argument('--maxtime',type=int,default=20,
                help='max run time in seconds')
    parser.add_argument('--verbose',action='store_true',
                help='displays all header and http debug info')
    parser.add_argument('--silent',action='store_true',
                help='silences URL crawl notifications')
    parser.add_argument('-l','--logging', action='store_true',
                help='enable logging')
    parser.add_argument('--logpath', default=False,
                help='specify a log path (defaults to ./text/crawl.log)')
    parser.add_argument('-y','--assume-yes',action='store_true',
                help='assumes a "yes" response to any prompts')

    # The --robots and --gz arguments are experimentally supported in 
    # mechanize, check your mechanize version for details and potential
    # issues.

    return parser.parse_args()
