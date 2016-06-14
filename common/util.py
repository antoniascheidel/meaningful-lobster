#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Misc. utility functions! Mostly logging right now.
"""

# TODO: Create enum
LOG_COLORS = {
    'CRITICAL': 'red',
    'DEBUG': 'cyan',
    'ERROR': 'red',
    'INFO': 'green',
    'MARK': 'purple',
    'WARNING': 'yellow',
}


class InvalidColorException(Exception):
    """
    Exception to be raised if an invalid color is requested for logging,
    """
    pass


def log(message, level="debug"):
    import datetime
    import sys

    from termcolor import colored

    # We will probably have to update this at some point as we change how we
    # run our code. My reference used sys._getframe(2)
    caller_frame = sys._getframe(1)
    caller_lineno = caller_frame.f_lineno
    caller_funcname = caller_frame.f_code.co_name

    color = None
    try:
        color = LOG_COLORS[level.upper()]
    except KeyError:
        raise InvalidColorException

    print colored(
        '[%s] [%s:%s] - %s' % (str(datetime.datetime.utcnow()),
                               caller_funcname, caller_lineno, message), color)
