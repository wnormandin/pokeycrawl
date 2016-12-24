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
import socket
import time
#import argparse
import os, sys
import logging
import cookielib

from Queue import Queue, Empty
from threading import Thread

# Module imports
from config import args
from log import setup_logger
from cli import parse_arguments

log = setup_logger(args)
if __name__=='__main__':
    # When invoked at the command line or via python -m,
    # parse command-line arguments to 
    args = parse_arguments(args)
