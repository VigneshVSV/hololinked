import datetime
import sys
import uuid
import logging
import re 
import asyncio
import inspect
import typing
import asyncio



def uuid4_in_bytes() -> bytes:
    """
    uuid.uuid4() in bytes
    """
    return bytes(str(uuid.uuid4()), encoding = 'utf-8')


def current_datetime_ms_str():
    """
    default: YYYY-mm-dd_HH:MM:SS.fff e.g. 2022-12-01 13:00:00.123 
    This default is (almost) ISO8601 compatible and is natively recognized by Pandas
    """
    curtime = datetime.datetime.now()
    return curtime.strftime('%Y%m%d_%H%M%S') + '{:03d}'.format(int(curtime.microsecond /1000))


def pep8_to_dashed_URL(word : str) -> str: 
    """
    Make an underscored, lowercase form from the expression in the string.
    Example::
        >>> pep8_to_dashed_URL("device_type")
        'device-type'
    """
    return re.sub(r'_+', '-', word)


def get_default_logger(name : str, log_level : int = logging.INFO, log_file = None,
                format : str = '%(levelname)-8s - %(asctime)s:%(msecs)03d - %(name)s - %(message)s' ) -> logging.Logger:
    """
    the default logger used by most of hololinked package, when arguments are not modified.
    StreamHandler is always created, pass log_file for a FileHandler as well.

    Parameters
    ----------
    name: str 
        name of logger
    log_level: int 
        log level
    log_file: str
        valid path to file
    format: str
        log format

    Returns
    -------
    logging.Logger:
        created logger
    """
    logger = logging.getLogger(name) 
    logger.setLevel(log_level)
    default_handler = logging.StreamHandler(sys.stdout)
    default_handler.setFormatter(logging.Formatter(format, datefmt='%Y-%m-%dT%H:%M:%S'))
    logger.addHandler(default_handler)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter(format, datefmt='%Y-%m-%dT%H:%M:%S'))
        logger.addHandler(file_handler)
    return logger


def run_coro_sync(coro : typing.Coroutine):
    """
    run coroutine synchronously
    """
    try:
        eventloop = asyncio.get_event_loop()
    except RuntimeError:
        eventloop = asyncio.new_event_loop()
    if eventloop.is_running():
        raise RuntimeError(f"asyncio event loop is already running, cannot setup coroutine {coro.__name__} to run sync, please await it.")
        # not the same as RuntimeError catch above.  
    else:
        return eventloop.run_until_complete(coro)


def run_callable_somehow(method : typing.Union[typing.Callable, typing.Coroutine]) -> typing.Any:
    """
    either schedule a coroutine or run it until its complete
    """
    if not (asyncio.iscoroutinefunction(method) or asyncio.iscoroutine(method)):
        return method()
    try:
        eventloop = asyncio.get_event_loop()
    except RuntimeError:
        eventloop = asyncio.new_event_loop()
    if eventloop.is_running():    
        task = lambda : asyncio.create_task(method) # check later if lambda is necessary
        eventloop.call_soon(task)
    else:
        task = method
        return eventloop.run_until_complete(task)


def get_signature(callable : typing.Callable) -> typing.Tuple[typing.List[str], typing.List[type]]: 
    """
    Retrieve the names and types of arguments based on annotations for the given callable.

    Parameters
    ----------
    callable: Callable
        function or method (not tested with __call__)
    
    Returns
    -------
    tuple: List[str], List[type]
        arguments name and types respectively
    """
    arg_names = []
    arg_types = []

    for param in inspect.signature(callable).parameters.values():
        arg_name = param.name
        arg_type = param.annotation if param.annotation != inspect.Parameter.empty else None

        arg_names.append(arg_name)
        arg_types.append(arg_type)

    return arg_names, arg_types


__all__ = [
    uuid4_in_bytes.__name__,
    current_datetime_ms_str.__name__,
    pep8_to_dashed_URL.__name__,
    get_default_logger.__name__,
    run_coro_sync.__name__,
    run_callable_somehow.__name__,
    get_signature.__name__
]



