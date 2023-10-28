# adapted from pyro - https://github.com/irmen/Pyro5 - see following license
# currently not used correctly because its not correctly integrated to the package 
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

class Configuration:

    __slots__ = [
        "HOST", "TEMP_DIR" 
        # "NS_HOST", "NS_PORT", "NS_BCPORT", "NS_BCHOST", "NS_AUTOCLEAN", "NS_LOOKUP_DELAY",
        # "NATHOST", "NATPORT", "COMPRESSION", "SERVERTYPE", "COMMTIMEOUT", "POLLTIMEOUT", "MAX_RETRIES",
        # "SOCK_REUSE", "SOCK_NODELAY", "DETAILED_TRACEBACK", "THREADPOOL_SIZE", "THREADPOOL_SIZE_MIN",
        # "MAX_MESSAGE_SIZE", "BROADCAST_ADDRS", "PREFER_IP_VERSION", "SERIALIZER"
        , "SERPENT_BYTES_REPR",
        # "ITER_STREAMING", "ITER_STREAM_LIFETIME", "ITER_STREAM_LINGER", "LOGFILE", "LOGLEVEL", "LOGWIRE",
        # "SSL", "SSL_SERVERCERT", "SSL_SERVERKEY", "SSL_SERVERKEYPASSWD", "SSL_REQUIRECLIENTCERT",
        # "SSL_CLIENTCERT", "SSL_CLIENTKEY", "SSL_CLIENTKEYPASSWD", "SSL_CACERTS"
    ]

    def __init__(self):
        self.reset_variables()
        self.reset_actions()


    def reset_variables(self, use_environment : bool = True):
        """
        Reset to default config items.
        If use_environment is False, won't read environment variables settings (useful if you can't trust your env).
        """
        self.HOST = "localhost"
        self.TEMP_DIR = tempfile.gettempdir() + "\\daqpy"
        # self.NS_HOST = "localhost"
        # self.NS_PORT = 9090
        # self.NS_BCPORT = 9091
        # self.NS_BCHOST = None
        # self.NS_AUTOCLEAN = 0.0
        # self.NS_LOOKUP_DELAY = 0.0
        # self.NATHOST = None
        # self.NATPORT = 0
        # self.COMPRESSION = False
        # self.SERVERTYPE = "thread"
        # self.COMMTIMEOUT = 0.0
        # self.POLLTIMEOUT = 2.0
        # self.MAX_RETRIES = 0
        # self.SOCK_REUSE = True  # so_reuseaddr on server sockets?
        # self.SOCK_NODELAY = False  # tcp_nodelay on socket?
        # self.DETAILED_TRACEBACK = False
        # self.THREADPOOL_SIZE = 80
        # self.THREADPOOL_SIZE_MIN = 4
        # self.MAX_MESSAGE_SIZE = 1024 * 1024 * 1024  # 1 gigabyte
        # self.BROADCAST_ADDRS = ["<broadcast>", "0.0.0.0"]
        # self.PREFER_IP_VERSION = 0  # 4, 6 or 0 (0=let OS choose according to RFC 3484)
        # self.SERIALIZER = "serpent"
        self.SERPENT_BYTES_REPR = False
        # self.LOGWIRE = False
        # self.ITER_STREAMING = True
        # self.ITER_STREAM_LIFETIME = 0.0
        # self.ITER_STREAM_LINGER = 30.0
        # self.LOGFILE = _pyro_logfile
        # self.LOGLEVEL = _pyro_loglevel
        # self.SSL = False
        # self.SSL_SERVERCERT = ""
        # self.SSL_SERVERKEY = ""
        # self.SSL_SERVERKEYPASSWD = ""
        # self.SSL_REQUIRECLIENTCERT = False
        # self.SSL_CLIENTCERT = ""
        # self.SSL_CLIENTKEY = ""
        # self.SSL_CLIENTKEYPASSWD = ""
        # self.SSL_CACERTS = ""
        # if use_environment:
        #     # environment variables overwrite config items
        #     prefix = "PYRO_"
        #     for item, envvalue in (e for e in os.environ.items() if e[0].startswith(prefix)):
        #         item = item[len(prefix):]
        #         if item not in self.__slots__:
        #             raise ValueError("invalid Pyro environment config variable: %s%s" % (prefix, item))
        #         value = getattr(self, item)
        #         valuetype = type(value)
        #         if valuetype is set:
        #             envvalue = {v.strip() for v in envvalue.split(",")}
        #         elif valuetype is list:
        #             envvalue = [v.strip() for v in envvalue.split(",")]
        #         elif valuetype is bool:
        #             envvalue = envvalue.lower()
        #             if envvalue in ("0", "off", "no", "false"):
        #                 envvalue = False
        #             elif envvalue in ("1", "yes", "on", "true"):
        #                 envvalue = True
        #             else:
        #                 raise ValueError("invalid boolean value: %s%s=%s" % (prefix, item, envvalue))
        #         else:
        #             try:
        #                 envvalue = valuetype(envvalue)
        #             except ValueError:
        #                 raise ValueError("invalid Pyro environment config value: %s%s=%s" % (prefix, item, envvalue)) from None
        #         setattr(self, item, envvalue)

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

    def as_dict(self):
        """returns this config as a regular dictionary"""
        return {item: getattr(self, item) for item in self.__slots__}
        
    def dump(self):
        """Easy config diagnostics"""
        # from .protocol import PROTOCOL_VERSION
        # result = ["Pyro version: %s" % __version__,
        #           "Loaded from: %s" % os.path.dirname(__file__),
        #           "Python version: %s %s (%s, %s)" % (platform.python_implementation(),
        #                                               platform.python_version(), platform.system(), os.name),
        #           "Protocol version: %d" % PROTOCOL_VERSION,
        #           "Currently active global configuration settings:"]
        # for item, value in sorted(self.as_dict().items()):
        #     result.append("{:s} = {:s}".format(item, str(value)))
        # return "\n".join(result)
        pass 

global_config = Configuration()


__all__ = ['global_config', 'Configuration']