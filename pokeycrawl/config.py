#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-
import time
from argparse import Namespace
args = Namespace()
#############################
"""
PokeyCrawl configuration settings

"""
#############################

#!# Global Defaults

# Maximum execution time for worker processes
args.maxtime=20
# Maximum concurrent worker threads
args.procs=4
# Delay between requests
args.speed=0.15
# Defaults to the PokeyBot UA string
args.ua="PokeyBot/1.0 (+https://pokeybill.us/bots)"
# Vary the user-agent string from the file docs/ua.txt
args.vary=False
# Enable debug messages and error raising
args.debug=False
# Enable post-execution summary
args.report=False
# Create an index of the URLs crawled in /tests/URL_UNIXEPOCH
args.index=False
# GZip support (experimental in mechanize)
args.gz=False
# robots.txt support (experimental in mechanize)
args.robots=False
# Enable verbose messages
args.verbose=False
# Enable logging to file
args.logging=False
args.logpath='tests/{}.log'.format(int(time.time()))
# Assume 'Yes' to all prompts
args.yes=False
# Run diagnostic test, displays all parameters, verbose crawl
# output without actually sending requests.
args.test=False
# Silence crawl messages, will enable the progress bar
args.silent=False
# Set request timeout in seconds (per request)
args.timeout=1

#!# WebsiteParser Settings
"""
Set to True to activate the SiteParser which
will review returned HTML for forms to be
passed to the FormCrawler workers in addition
to the default sites
"""
args.parse=False

#!# Spider Settings

#!# FormCrawler Settings
"""
Set to True to activate the FormCrawler
FormCrawlers will be spawned at half the
rate of Spider workers and will target
common pages with forms :
  /wp-admin/wp-login
  /administrator
  /admin
  /login.php
  /login
  /contact-us
  /contact
  /contactus
  ...etc
The intended result is a more accurate depiction
of normal web traffic, including PHP and database
queries which are typically much more resource-
intensive than simple page loads.
"""
args.forms=False

