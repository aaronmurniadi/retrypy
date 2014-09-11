import re
import time
from functools import partial, wraps

always_true = lambda *args, **kwargs: True


def _parse_search(input):
    if isinstance(input, basestring):
        return lambda x, *_: x in input
    elif isinstance(input, re._pattern_type):
        return lambda x, *_: input.search(x)
    elif hasattr(input, '__call__'):
        return input
    raise TypeError("Matches must be strings, regex, or functions")


def _parse_exceptions(input):
    matches = []
    for e in input:
        if isinstance(e, (tuple, list)):
            matches.append((e[0], _parse_search(e[1])))
        else:
            matches.append((e, always_true))

    exceptions = map(lambda x: x[0], matches)
    return tuple(exceptions), matches


def _should_retry(e, matches, count):
    for e_type, test in matches:
        if isinstance(e, e_type):
            return test(e.message, count)
    return False


def _retry(func, exceptions, times, wait):
    exceptions, matches = _parse_exceptions(exceptions)
    previous_exception = None
    for n in xrange(times):
        try:
            return func()
        except exceptions as e:
            if not _should_retry(e, matches, n):
                raise e
            previous_exception = e
        time.sleep(wait)
    raise previous_exception


def retry(*args, **kwargs):
    if args and hasattr(args[0], '__call__'):
        return _function(*args, **kwargs)
    return _decorator(*args, **kwargs)


def _function(
    func,
    args=None,
    kwargs=None,
    exceptions=None,
    times=5,
    wait=1,
):
    '''
        A wrapper to automagically retry a function call if it fails

        Parameters:
            func: The function you want to call.
            args: Positional args to be passed to func
            kwargs: keywords args to be passed to func
            exceptions: an array of Exception types you want to retry on.
            Exceptable Inputs:
                [ExceptionType1, ExceptionType2 ... ]
                [(ExceptionType1, RegEx) ...] => regex test
                [(ExceptionType1, String) ...] => contains string test
                [(ExceptionType1, Function) ...] => custom test function
            times: number of times to retry
            wait: number of seconds to wait between tries
    '''
    if args is None:
        args = []
    if kwargs is None:
        kwargs = {}
    if exceptions is None:
        exceptions = [Exception]

    if times < 1:
        raise TypeError("Cannot try less than 1 time")

    return _retry(
        partial(func, *args, **kwargs),
        exceptions,
        times,
        wait,
    )


def _decorator(**decorator_kwargs):
    def wrap(func):
        @wraps(func)
        def wrapped(*func_args, **func_kwargs):
            return retry(
                func,
                args=func_args,
                kwargs=func_kwargs,
                **decorator_kwargs
            )

        return wrapped
    return wrap
