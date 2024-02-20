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
from .data_classes import HTTPResource
from .utils import create_default_logger, run_method_somehow
from .serializers import JSONSerializer
from .constants import Instructions
from .webserver_utils import log_request, update_resources
from .zmq_message_brokers import MessageMappedZMQClientPool
from .handlers import RPCHandler
from .remote_object import RemoteObject, RemoteObjectDB



class HTTPServer(Parameterized):

    address = IPAddress(default='0.0.0.0', 
                    doc = "set custom IP address, default is localhost (0.0.0.0)") # type: str
    port = Integer(default=8080, bounds=(1, 65535),  
                    doc = "the port at which the server should be run (unique)" ) # ytype: int
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
        self.zmq_client_pool = MessageMappedZMQClientPool(self.remote_objects, 
                                    self._IP, json_serializer=self.serializer)
        
        self.resources = dict(
            FILE_SERVER = dict(STATIC_ROUTES = dict(), DYNAMIC_ROUTES = dict()),
            GET     = dict(STATIC_ROUTES = dict(), DYNAMIC_ROUTES = dict()),
            POST    = dict(STATIC_ROUTES = dict(), DYNAMIC_ROUTES = dict()),
            PUT     = dict(STATIC_ROUTES = dict(), DYNAMIC_ROUTES = dict()),
            DELETE  = dict(STATIC_ROUTES = dict(), DYNAMIC_ROUTES = dict()),
            OPTIONS = dict(STATIC_ROUTES = dict(), DYNAMIC_ROUTES = dict())
        )
        return True


    def listen(self) -> None:
        assert self.all_ok, 'HTTPServer all is not ok before starting' 
        # Will always be True or cause some other exception
        run_method_somehow(self._fetch_remote_object_resources())
        self.request_handler.zmq_client_pool = self.zmq_client_pool
        self.event_loop = ioloop.IOLoop.current()
        handlers = []
        for route, http_resource in self.resources["GET"]["STATIC_ROUTES"].items():
            handlers.append((route, self.request_handler, {'resource' : http_resource}))
            """
            for handler based tornado rule matcher, the Rule object has following
            signature
            
            def __init__(
                self,
                matcher: "Matcher",
                target: Any,
                target_kwargs: Optional[Dict[str, Any]] = None,
                name: Optional[str] = None,
            ) -> None:

            matcher - based on route
            target - handler
            target_kwargs - given to handler's initialize
            name - ...

            len == 2 tuple is route + handler
            len == 3 tuple is route + handler + target kwargs
        
            so we give (path, RPCHandler, {'resource' : HTTPResource})
         
            path is extracted from remote_method(URL_path='....')
            RPCHandler is the base handler of this package
            resource goes into target kwargs as the HTTPResource generated by 
                remote_method and RemoteParamater contains all the info given 
                to make RPCHandler work
            """
        self.app = Application(handlers=handlers)
        # self.app.remote_object_http_resources = self.resources["GET"]["STATIC_ROUTES"]
        # self.router=(app=self.app)
        if self.protocol_version == 2:
            raise NotImplementedError("Current HTTP2 is not implemented.")
            self.server = TornadoHTTP2Server(router, ssl_options=self.ssl_context)
        else:
            self.server = TornadoHTTP1Server(self.app, ssl_options=self.ssl_context)
        self.server.listen(port=self.port, address=self.address)    
        self.logger.info(f'started webserver at {self.address}:{self.port}, ready to receive requests.')
        self.event_loop.start()


    async def _fetch_remote_object_resources(self):
        for client in self.zmq_client_pool:
            await client.handshake_complete()
            _, _, _, _, _, reply = await client.async_execute(
                        f'/{client.server_instance_name}{Instructions.HTTP_RESOURCES}', 
                        raise_client_side_exception=True)
            update_resources(self.resources, reply["returnValue"]) # type: ignore
            # _, _, _, _, _, reply = await client.read_attribute('/'+client.server_instance_name + '/object-info', raise_client_side_exception = True)
            # remote_object_info.append(RemoteObjectDB.RemoteObjectInfo(**reply["returnValue"])) # Should raise an exception if returnValue key is not found for some reason. 
       
        
    def stop(self) -> None:
        raise NotImplementedError("closing HTTP server currently not supported.")
        self.server.close_all_connections()
        self.event_loop.close()
      
    

# async def _setup_server(address : str, port : int, logger : logging.Logger, subscription : str, 
#                 consumers : List[Union[Consumer, RemoteObject, str]], resources : Dict[str, Dict[str, Any]], 
#                 ssl_context : ssl.SSLContext, json_serializer  : JSONSerializer, version : float = 2) -> None:
#     IP = "{}:{}".format(address, port)
#     instance_names = []
#     server_remote_objects = {}
#     remote_object_info = []
#     if consumers is not None:
#         for consumer in consumers:
#             if isinstance(consumer, RemoteObject):
#                 server_remote_objects[consumer.instance_name] = consumer
#                 update_resources(resources, consumer.httpserver_resources) 
#                 remote_object_info.append(consumer.object_info) 
#             elif isinstance(consumer, Consumer): 
#                 instance = consumer.consumer(*consumer.args, **consumer.kwargs)
#                 server_remote_objects[instance.instance_name] = instance
#                 update_resources(resources, instance.httpserver_resources)
#                 remote_object_info.append(instance.object_info) 
#             else:
#                 instance_names.append(consumer)
   
#     zmq_client_pool = MessageMappedZMQClientPool(instance_names, IP, json_serializer = json_serializer)
#     for client in zmq_client_pool:
#         await client.handshake_complete() 
#         _, _, _, _, _, reply = await client.read_attribute('/'+client.server_instance_name + '/resources/http', raise_client_side_exception = True)
#         update_resources(resources, reply["returnValue"]) # type: ignore
#         _, _, _, _, _, reply = await client.read_attribute('/'+client.server_instance_name + '/object-info', raise_client_side_exception = True)
#         remote_object_info.append(RemoteObjectDB.RemoteObjectInfo(**reply["returnValue"])) # Should raise an exception if returnValue key is not found for some reason. 
    
#     for RO in server_remote_objects.values():
#         if isinstance(RO, HTTPServerUtilities):
#             RO.zmq_client_pool = zmq_client_pool
#             RO.remote_object_info = remote_object_info
#             RO._httpserver_resources = resources
#             if subscription:
#                 await RO.subscribe_to_host(subscription, port)
#                 break
    
#     BaseRequestHandler.zmq_client_pool = zmq_client_pool
#     BaseRequestHandler.json_serializer = zmq_client_pool.json_serializer
#     BaseRequestHandler.local_objects   = server_remote_objects
#     GetResource.resources = resources.get(GET,  dict())        
#     PostResource.resources = resources.get(POST, dict()) 
#     PutResource.resources = resources.get(PUT,  dict()) 
#     DeleteResource.resources = resources.get(DELETE, dict())
#     OptionsResource.resources = resources.get(OPTIONS, dict())
#     # log_resources(logger, resources)   
#     Router = CustomRouter(Application(), logger, IP, resources.get('FILE_SERVER'))   
#     # if version == 2:   
#     #     S = TornadoHTTP2Server(Router, ssl_options=ssl_context)
#     # else: 
#     S = TornadoHTTP1Server(Router, ssl_options=ssl_context)    
#     S.listen(port=port, address=address) 


__all__ = ['HTTPServer']