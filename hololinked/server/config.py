# adapted from pyro - https://github.com/irmen/Pyro5 - see following license
"""
MIT License

Copyright (c) Irmen de Jong

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
import tempfile
import os
import typing 
import warnings

from .. import __version__
from .serializers import PythonBuiltinJSONSerializer


class Configuration:
    """
    Allows to auto apply common settings used throughout the package,
    instead of passing these settings as arguments. Import ``global_config`` variable
    instead of instantitation this class. 

    Supports loading configuration from a JSON file whose path is specified 
    under environment variable HOLOLINKED_CONFIG. 

    Values are mutable in runtime and not type checked. Keys of JSON file 
    must correspond to supported value name. Supported values are - 

    TEMP_DIR - system temporary directory to store temporary files like IPC sockets. 
    default - tempfile.gettempdir().
    
    TCP_SOCKET_SEARCH_START_PORT - starting port number for automatic port searching 
    for TCP socket binding, used for event addresses. default 60000.
    
    TCP_SOCKET_SEARCH_END_PORT - ending port number for automatic port searching 
    for TCP socket binding, used for event addresses. default 65535.

    DB_CONFIG_FILE - file path for database configuration. default None. 

    SYSTEM_HOST - system view server qualified IP or name. default None.
    
    PWD_HASHER_TIME_COST - system view server password authentication time cost, 
    default 15. Refer argon2-cffi docs. 

    PWD_HASHER_MEMORY_COST - system view server password authentication memory cost. 
    Refer argon2-cffi docs.

    USE_UVLOOP - signicantly faster event loop for Linux systems. Reads data from network faster. default False. 

    Parameters
    ----------
    use_environment: bool
        load files from JSON file specified under environment

    """

    __slots__ = [
        # folders
        "TEMP_DIR",
        # TCP socket 
        "TCP_SOCKET_SEARCH_START_PORT", "TCP_SOCKET_SEARCH_END_PORT",
        # system view
        "PRIMARY_HOST", "LOCALHOST_PORT", 
        # database
        "DB_CONFIG_FILE", 
        # HTTP server
        "COOKIE_SECRET",
        # credentials
        "PWD_HASHER_TIME_COST", "PWD_HASHER_MEMORY_COST",
        # Eventloop
        "USE_UVLOOP", "TRACE_MALLOC",
        'validate_schema_on_client', 'validate_schemas'
    ]

    def __init__(self, use_environment : bool = False):
        self.load_variables(use_environment)
        self.reset_actions()

    def load_variables(self, use_environment : bool = False):
        """
        set default values & use the values from environment file. 
        Set use_environment to False to not use environment file. 
        """
        self.TEMP_DIR = f"{tempfile.gettempdir()}{os.sep}hololinked"
        self.TCP_SOCKET_SEARCH_START_PORT = 60000
        self.TCP_SOCKET_SEARCH_END_PORT = 65535
        self.PWD_HASHER_TIME_COST = 15
        self.USE_UVLOOP = False
        self.TRACE_MALLOC = False
        self.validate_schema_on_client = False
        self.validate_schemas = True 

        if not use_environment:
            return 
        # environment variables overwrite config items
        file = os.environ.get("HOLOLINKED_CONFIG", None)
        if not file:
            warnings.warn("no environment file found although asked to load from one", UserWarning)
            return
        with open(file, "r") as file:
            config = PythonBuiltinJSONSerializer.load(file) # type: typing.Dict
        for item, value in config.items():
            setattr(self, item, value)

    def reset_actions(self):
        "actions to be done to reset configurations (not actions to be called)"
        try:
            os.mkdir(self.TEMP_DIR)
        except FileExistsError:
            pass

    def copy(self):
        "returns a copy of this config as another object"
        other = object.__new__(Configuration)
        for item in self.__slots__:
            setattr(other, item, getattr(self, item))
        return other

    def asdict(self):
        "returns this config as a regular dictionary"
        return {item: getattr(self, item) for item in self.__slots__}


global_config = Configuration()


__all__ = ['global_config', 'Configuration']