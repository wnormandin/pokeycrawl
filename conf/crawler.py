#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-
from argparse import Namespace
args = Namespace()
#############################
"""
PokeyCrawl configuration settings

"""
#############################

#!# Global Defaults
LOG_PATH='./text/crawl.log'

""" Maximum execution time for worker processes """
MAX_TIME=20
""" Maximum concurrent worker threads """
MAX_PROCS=4
""" Delay between requests """
CRAWL_SPEED=0.15
""" Defaults to the PokeyBot UA string """
USER_AGENT="PokeyBot/1.0 (+https://pokeybill.us/bots)"

#!# WebsiteParser Settings
"""
Set to True to activate the SiteParser which
will review returned HTML for forms to be
passed to the FormCrawler workers in addition
to the default sites
"""
SITE_PARSE=False

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
FORMS=False

