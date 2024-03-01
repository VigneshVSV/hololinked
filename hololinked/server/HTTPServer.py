import logging
import ssl
import typing
from tornado import ioloop
from tornado.web import Application
from tornado.httpserver import HTTPServer as TornadoHTTP1Server
# from tornado_http2.server import Server as TornadoHTTP2Server 

from ..param import Parameterized
from ..param.parameters import (Integer, IPAddress, ClassSelector, Selector, 
                    TypedList, String)
from .utils import create_default_logger, run_coro_sync
from .serializers import JSONSerializer
from .zmq_message_brokers import MessageMappedZMQClientPool
from .handlers import RPCHandler, BaseHandler, EventHandler, RemoteObjectsHandler



class HTTPServer(Parameterized):
    """
    HTTP(s) server to route requests to ``RemoteObject``. Only one HTTPServer per process supported.
    """

    address = IPAddress(default='0.0.0.0', 
                    doc="set custom IP address, default is localhost (0.0.0.0)") # type: str
    port = Integer(default=8080, bounds=(1, 65535),  
                    doc="the port at which the server should be run (unique)" ) # ytype: int
    protocol_version = Selector(objects=[1, 1.1, 2], default=2, 
                    doc="for HTTP 2, SSL is mandatory. HTTP2 is recommended. \
                    When no SSL configurations are provided, defaults to 1.1" ) # type: float
    logger = ClassSelector(class_=logging.Logger, default=None, allow_None=True, 
                    doc="Supply a custom logger here or set log_level parameter to a valid value" ) # type: logging.Logger
    log_level = Selector(objects=[logging.DEBUG, logging.INFO, logging.ERROR, logging.CRITICAL, logging.ERROR], 
                    default=logging.INFO, 
                    doc="Alternative to logger, this creates an internal logger with the specified log level" ) # type: int
    remote_objects = TypedList(item_type=str, default=None, allow_None=True, 
                       doc="Remote Objects to be served by the HTTP server" ) # type: typing.List[str]
    host = String(default=None, allow_None=True, 
                doc="Host Server to subscribe to coordinate starting sequence of remote objects & web GUI" ) # type: str
    serializer = ClassSelector(class_=JSONSerializer,  default=None, allow_None=True,
                    doc="optionally, supply your own JSON serializer for custom types" ) # type: JSONSerializer
    ssl_context = ClassSelector(class_=ssl.SSLContext, default=None, allow_None=True, 
                    doc="use it for highly customized SSL context to provide encrypted communication") # type: typing.Optional[ssl.SSLContext]    
    certfile = String(default=None, allow_None=True, 
                    doc="alternative to SSL context, provide certificate file & key file to allow the server \
                        to create a SSL connection on its own") # type: str
    keyfile = String(default=None, allow_None=True, 
                    doc="alternative to SSL context, provide certificate file & key file to allow the server \
                            to create a SSL connection on its own") # type: str
    network_interface = String(default='Ethernet',  
                            doc="Currently there is no logic to detect the IP addresss (as externally visible) correctly, \
                            therefore please send the network interface name to retrieve the IP. If a DNS server is present, \
                            you may leave this field" ) # type: str
    request_handler = ClassSelector(default=RPCHandler, class_=RPCHandler, isinstance=False, 
                            doc="custom web request handler of your choice" ) # type: RPCHandler
    event_handler = ClassSelector(default=EventHandler, class_=(EventHandler, BaseHandler), isinstance=False, 
                            doc="custom event handler of your choice for handling events") # type: typing.Union[BaseHandler, EventHandler]
    allowed_clients = TypedList(item_type=str,
                            doc="short attribute for setting client in CORS, overload set_headers() to implement custom CORS")

    def __init__(self, remote_objects : typing.List[str], *, port : int = 8080, address : str = '0.0.0.0', 
                host : str = None, logger : typing.Optional[logging.Logger] = None, log_level : int = logging.INFO, 
                certfile : str = None, keyfile : str = None, serializer : JSONSerializer = None,  
                ssl_context : ssl.SSLContext = None, protocol_version : int = 1, 
                network_interface : str = 'Ethernet', request_handler : RPCHandler = RPCHandler) -> None:
        super().__init__(
            remote_objects=remote_objects,
            port=port, 
            address=address, 
            host=host,
            logger=logger, 
            log_level=log_level,
            serializer=serializer, 
            protocol_version=protocol_version,
            certfile=certfile, 
            keyfile=keyfile,
            ssl_context=ssl_context,
            network_interface=network_interface,
            request_handler=request_handler
        )
        

    @property
    def all_ok(self) -> bool:
        self._IP = f"{self.address}:{self.port}"
        if self.logger is None:
            self.logger = create_default_logger('{}|{}'.format(self.__class__.__name__, 
                                            f"{self.address}:{self.port}"), 
                                            self.log_level)
            
        self.handlers = [
            (r'/remote-objects', RemoteObjectsHandler, {'request_handler' : self.request_handler})
        ]
        self.app = Application(handlers=self.handlers)
        
        self.zmq_client_pool = MessageMappedZMQClientPool(self.remote_objects, 
                                    self._IP, json_serializer=self.serializer)
        BaseHandler.zmq_client_pool = self.zmq_client_pool
        BaseHandler.json_serializer = self.serializer
        BaseHandler.logger = self.logger
        BaseHandler.clients = ', '.join(self.allowed_clients)
        BaseHandler.application = self.app

        return True


    def listen(self) -> None:
        assert self.all_ok, 'HTTPServer all is not ok before starting' 
        # Will always be True or cause some other exception   
        self.event_loop = ioloop.IOLoop.current()
        self.event_loop.add_future(RemoteObjectsHandler.connect_to_remote_object(
            [client for client in self.zmq_client_pool]))
        
        if self.protocol_version == 2:
            raise NotImplementedError("Current HTTP2 is not implemented.")
            self.server = TornadoHTTP2Server(router, ssl_options=self.ssl_context)
        else:
            self.server = TornadoHTTP1Server(self.app, ssl_options=self.ssl_context)
        self.server.listen(port=self.port, address=self.address)    
        self.logger.info(f'started webserver at {self._IP}, ready to receive requests.')
        self.event_loop.start()

    def stop(self) -> None:
        self.server.stop()
        run_coro_sync(self.server.close_all_connections())
        self.event_loop.close()    



__all__ = ['HTTPServer']