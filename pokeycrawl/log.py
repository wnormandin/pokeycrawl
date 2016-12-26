import logging
import os,sys

def setup_logger(args):

    def __console_logging(logger,cfmt):
        cons_handler = logging.StreamHandler(sys.stdout)
        cons_handler.setFormatter(cfmt)
        cons_handler.setLevel(logger.level)
        logger.addHandler(cons_handler)

    def __file_logging(logger,fpath=os.path.join(os.path.dirname(__file__),
                                                 args.logpath)):
        fpath = _resolve_path(fpath)
        fmt = logging.Formatter('%(asctime)s %(threadName)-8s :: %(message)s')
        file_handler = logging.FileHandler(fpath,'a')
        file_handler.setFormatter(fmt)
        file_handler.setLevel(logger.level)
        logger.addHandler(file_handler)

    def _get_level():
        if args.silent and args.logging and not args.debug:
            return logging.DEBUG
        if args.debug:
            return logging.DEBUG
        if args.verbose:
            return logging.INFO
        return logging.WARNING

    def _touch(fpath):
        if not os.path.exists(fpath):
            with open(fpath, 'w+') as f:
                return True
        return False

    def _resolve_path(fpath):
        # Convert to absolute path, touch file
        fpath = os.path.realpath(fpath)
        result = _touch(fpath)
        return fpath

    # Setup console and file output based on command-line parameters
    if args.debug and args.verbose:
        cfmt = logging.StreamHandler('%(asctime)s | %(filename)s[%(process)d] > %(message)s')
    else:
        cfmt = logging.StreamHandler('%(threadName)-8s :: %(message)s')

    logger = logging.getLogger('pokeycrawl')
    logger.setLevel(_get_level())

    # Add the console handler if not in silent mode
    if not (args.silent and args.logging and not args.debug) or not args.silent:
        __console_logging(logger,cfmt)

    if args.logging:
        params = (logger,args.logpath,)
        __file_logging(*params)

    return logger
