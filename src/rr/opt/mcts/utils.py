"""Container module for code (constants, functions, etc) which does not necessarily belong in any
other place within the `rr.opt.mcts` package.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging
import logging.config


INF = float("inf")  # Shorthand for writing the whole 'float("inf")' stuff :P


class Undefined(object):
    """A feature-less class whose only purpose is to instantiate once as the `UNDEFINED`
    singleton constant. This constant is supposed to be used in contexts where `None` might be a
    valid value.
    """
    __instance = None

    def __new__(cls):
        if cls.__instance is None:
            cls.__instance = object.__new__(cls)
        return cls.__instance

    def __repr__(self):
        return "UNDEFINED"


UNDEFINED = Undefined()  # just an object to be used when None might be a valid value


def blank_instance(cls):
    """Create a new blank instance of `cls`.

    Creates a new blank object without the initialization procedure (__new__() -> __init__())
    automatically executed when creating instances by calling the class constructor. Also,
    since the __new__() method is called without arguments, the new object will be completely
    blank but bound to the argument class.
    """
    return cls.__new__(cls)


def max_elems(iterable, key=None):
    """Find the elements in 'iterable' corresponding to the maximum values w.r.t. 'key'.

    Returns:
        A `(max_elems, max_key)` pair.
    """
    iterator = iter(iterable)
    try:
        elem = next(iterator)
    except StopIteration:
        raise ValueError("argument iterable must be non-empty")
    max_elems = [elem]
    max_key = elem if key is None else key(elem)
    for elem in iterator:
        curr_key = elem if key is None else key(elem)
        if curr_key > max_key:
            max_elems = [elem]
            max_key = curr_key
        elif curr_key == max_key:
            max_elems.append(elem)
    return max_elems, max_key


logger = logging.getLogger("rr.opt.mcts")
debug = logger.debug
info = logger.info
warn = logger.warning
error = logger.error


def config_logging(name="rr.opt.mcts", level="INFO"):
    logging.config.dictConfig({
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': '[%(levelname)s] %(name)s: %(message)s',
            },
        },
        'handlers': {
            'default': {
                'level': level,
                'formatter': 'standard',
                'class': 'logging.StreamHandler',
            },
        },
        'loggers': {
            name: {
                'handlers': ['default'],
                'level': level,
                'propagate': True,
            },
        }
    })
