import datetime
import sys
import uuid
import logging
import re 
import asyncio
import inspect
import typing
import asyncio
from ..param.exceptions import wrap_error_text as wrap_text



def copy_parameters(src : str = 'D:/onedrive/desktop/dashboard/scada/scadapy/scadapy/param/parameters.py', 
                    dst : str = 'D:/onedrive/desktop/dashboard/scada/scadapy/scadapy/server/remote_parameters.py') -> None:

    skip_classes = ['Infinity', 'resolve_path', 'normalize_path', 'BaseConstrainedList', 'TypeConstrainedList', 
                'TypeConstrainedDict', 'TypedKeyMappingsConstrainedDict', 'Event']
    end_line = 'def hashable'
    additional_imports = ['from ..param.parameters import (TypeConstrainedList, TypeConstrainedDict, abbreviate_paths,\n',
                        '                       TypedKeyMappingsConstrainedDict, resolve_path, concrete_descendents, named_objs)\n'
                        'from .remote_parameter import RemoteParameter\n',
                        'from .constants import HTTP, PROXY, USE_OBJECT_NAME, GET, PUT']

    def fetch_line() -> typing.Generator[str]:
        with open(src, 'r') as file:
            oldlines = file.readlines()
            for line in oldlines: 
                yield line

    remote_init_kwargs = [
        '\t\t\tURL_path : str = USE_OBJECT_NAME, http_method : typing.Tuple[str, str] = (GET, PUT),\n', 
        '\t\t\tstate : typing.Optional[typing.Union[typing.List, typing.Tuple, str, Enum]] = None,\n',
        '\t\t\tdb_persist : bool = False, db_init : bool = False, db_commit : bool = False,\n'
        '\t\t\taccess_type : str = (HTTP, PROXY),\n',
    ]

    remote_super_init = [
        '\t\t\tURL_path=URL_path, http_method=http_method, state=state, db_persist=db_persist,\n',
        '\t\t\tdb_init=db_init, db_commit=db_commit, access_type=access_type)\n'
    ]

    common_linegen = fetch_line()
    newlines = []

    def skip_to_init_doc():
        for line in common_linegen:
            if 'doc : typing.Optional[str] = None' in line:
                return line
            else:
                newlines.append(line)

    def skip_to_super_init_end():
        for line in common_linegen:
            if 'precedence=precedence)' in line:
                return line
            else:
                newlines.append(line)

    def is_function(line : str) -> bool:
        if 'def ' in line and 'self' not in line and 'cls' not in line and 'obj' not in line:
            return True
        return False 
    
    def next_line_after_skip_class_or_function() -> str:
        for line_ in common_linegen:
            if ('class ' in line_ and ':' in line_) or is_function(line_):
                return line_ 

    def process_current_line(line : str):
        newline = line
        if 'import ' in line and 'parameterized ' in line: 
            newlines_ = [line.replace('from .parameterized', 'from ..param.parameterized').replace('ParamOverrides,', ''), 
                        next(common_linegen).replace('ParameterizedFunction, descendents,', ''), 
                        *additional_imports]
            newlines.extend(newlines_)
            return
        elif 'from collections import OrderedDict' in line:
            newlines.append('from enum import Enum\n')
        elif 'from .utils' in line or 'from .exceptions' in line:
            newline = line.replace('from .', 'from ..param.')
        elif 'class ' in line and ':' in line and line.startswith('class'):
            if '(Parameter):' in line: 
                newline = line.replace('(Parameter):', '(RemoteParameter):') 
                newlines.append(newline)           
            else:
                classname_with_inheritance = line.split(' ', 1)[1][:-2] # [:-2] for removing colon 
                classname_without_inheritance = classname_with_inheritance.split('(', 1)[0]
                if classname_without_inheritance in skip_classes:
                    newline = next_line_after_skip_class_or_function()
                    process_current_line(newline)
                    return
                else:
                    newlines.append(line)
            newline = skip_to_init_doc()
            newlines.append(newline)
            newlines.extend(remote_init_kwargs)
            newline = skip_to_super_init_end()
            if newline:
                newline = newline.replace('precedence=precedence)', 'precedence=precedence,')
                newlines.append(newline)
                newlines.extend(remote_super_init)
            return
        elif 'Parameter.__init__' in line:
            newline = line.replace('Parameter.__init__', 'RemoteParameter.__init__')
        elif is_function(line):
            newline = next_line_after_skip_class_or_function()
            process_current_line(newline)
            return
        newlines.append(newline)


    for line in common_linegen:
        process_current_line(line)
        if end_line in line:
            newlines.pop()
            break
        
    with open(dst, 'w') as file:
        file.writelines(newlines)


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


def dashed_URL(word : str) -> str: 
    """
    Make an underscored, lowercase form from the expression in the string.
    Example::
        >>> underscore("DeviceType")
        'device_type'
    As a rule of thumb you can think of :func:`underscore` as the inverse of
    :func:`camelize`, though there are cases where that does not hold::
        >>> camelize(underscore("IOError"))
        'IoError'
    """
    word = re.sub(r"([A-Z]+)([A-Z][a-z])", r'\1_\2', word)
    word = re.sub(r"([a-z\d])([A-Z])", r'\1_\2', word)
    return word.lower().replace('_', '-')


def create_default_logger(name : str, log_level : int = logging.INFO, log_file = None,
                format : str = '%(levelname)-8s - %(asctime)s:%(msecs)03d - %(name)s - %(message)s' ) -> logging.Logger:
    """
    the default logger used by most of hololinked package. StreamHandler is always created, pass log_file for a FileHandler
    as well.
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


def run_coro_sync(coro):
    """
    run coroutine synchronously
    """

    eventloop = asyncio.get_event_loop()
    if eventloop.is_running():
        raise RuntimeError("asyncio event loop is already running, cannot setup coroutine to run sync, please await it or set schedule = True.")
    else:
        eventloop.run_until_complete(coro)


def run_method_somehow(method : typing.Union[typing.Callable, typing.Coroutine]) -> typing.Any:
    """
    either schedule the coroutine or run it until its complete
    """
    if not (asyncio.iscoroutinefunction(method) or asyncio.iscoroutine(method)):
        return method()
    eventloop = asyncio.get_event_loop()
    if eventloop.is_running():    
        task = lambda : asyncio.create_task(method) # check later if lambda is necessary
        eventloop.call_soon(task)
    else:
        task = method
        eventloop.run_until_complete(task)


def get_signature(function : typing.Callable): 
    # Retrieve the names and types of arguments
    arg_names = []
    arg_types = []

    for param in inspect.signature(function).parameters.values():
        arg_name = param.name
        arg_type = param.annotation if param.annotation != inspect.Parameter.empty else None

        arg_names.append(arg_name)
        arg_types.append(arg_type)

    return arg_names, arg_types


__all__ = ['current_datetime_ms_str', 'wrap_text', 'copy_parameters', 'dashed_URL']



