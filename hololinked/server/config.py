# adapted from pyro - https://github.com/irmen/Pyro5 - see following license
# currently not used correctly because its not integrated to the package 
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
import platform
from . import __version__


class Configuration:

    __slots__ = [
        "TEMP_DIR", "TCP_SOCKET_SEARCH_START_PORT", "TCP_SOCKET_SEARCH_END_PORT",
        "PRIMARY_HOST", "LOCALHOST_PORT", 
        "DB_CONFIG_FILE", "COOKIE_SECRET",
        "PWD_HASHER_TIME_COST", "PWD_HASHER_MEMORY_COST"
    ]

    def __init__(self):
        self.reset_variables()
        self.reset_actions()


    def reset_variables(self, use_environment : bool = True):
        """
        Reset to default config items.
        If use_environment is False, won't read environment variables settings (useful if you can't trust your env).
        """
        self.TEMP_DIR = f"{tempfile.gettempdir()}{os.sep}hololinked"
        self.TCP_SOCKET_SEARCH_START_PORT = 60000
        self.TCP_SOCKET_SEARCH_END_PORT = 65535

        return 
        # qualname is not defined
        if use_environment:
            # environment variables overwrite config items
            prefix = __qualname__.split('.')[0]
            for item, envvalue in (e for e in os.environ.items() if e[0].startswith(prefix)):
                item = item[len(prefix):]
                if item not in self.__slots__:
                    raise ValueError(f"invalid environment config variable: {prefix}{item}")
                value = getattr(self, item)
                valuetype = type(value)
                if valuetype is set:
                    envvalue = {v.strip() for v in envvalue.split(",")}
                elif valuetype is list:
                    envvalue = [v.strip() for v in envvalue.split(",")]
                elif valuetype is bool:
                    envvalue = envvalue.lower()
                    if envvalue in ("0", "off", "no", "false"):
                        envvalue = False
                    elif envvalue in ("1", "yes", "on", "true"):
                        envvalue = True
                    else:
                        raise ValueError(f"invalid boolean value: {prefix}{item}={envvalue}")
                else:
                    try:
                        envvalue = valuetype(envvalue)
                    except ValueError:
                        raise ValueError(f"invalid environment config value: {prefix}{item}={envvalue}") from None
                setattr(self, item, envvalue)

    def reset_actions(self):
        try:
            os.mkdir(self.TEMP_DIR)
        except FileExistsError:
            pass

    def copy(self):
        """returns a copy of this config"""
        other = object.__new__(Configuration)
        for item in self.__slots__:
            setattr(other, item, getattr(self, item))
        return other

    def asdict(self):
        """returns this config as a regular dictionary"""
        return {item: getattr(self, item) for item in self.__slots__}
        
    def dump(self):
        """Easy config diagnostics"""
        return {
            "version" : __version__,
            "path" : os.path.dirname(__file__),
            "python" : f"{platform.python_implementation()} {platform.python_version()} ({platform.system()}, {os.name})" ,
            "configuration" : self.asdict()
        }
            
  
  
global_config = Configuration()


__all__ = ['global_config', 'Configuration']