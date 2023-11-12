import logging
import ssl
import asyncio
from typing import Dict, List, Callable, Union, Any
from multiprocessing import Process
from tornado.web import Application
from tornado.routing import Router
from tornado.httpserver import HTTPServer as TornadoHTTP1Server
# from tornado_http2.server import Server as TornadoHTTP2Server 
from tornado import ioloop
from tornado.httputil import HTTPServerRequest
from time import perf_counter

from ..param import Parameterized
from ..param.parameters import Integer, IPAddress, ClassSelector, Selector, TypedList, Boolean, String


from .utils import create_default_logger
from .decorators import get, put, post, delete, remote_method
from .data_classes import HTTPServerResourceData
from .serializers import JSONSerializer
from .constants import GET, PUT, POST, OPTIONS, DELETE, USE_OBJECT_NAME, CALLABLE
from .webserver_utils import log_resources, log_request, update_resources
from .zmq_message_brokers import MessageMappedZMQClientPool
from .handlers import (BaseRequestHandler, GetResource, PutResource, OptionsResource, 
                       PostResource, DeleteResource, FileHandlerResource)
from .remote_object import RemoteObject, RemoteObjectDB
from .eventloop import Consumer
from .host_utilities import HTTPServerUtilities, SERVER_INSTANCE_NAME


asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


class CustomRouter(Router):   
    
    def __init__(self, app : Application, logger : logging.Logger, IP : str, 
                    file_server_paths) -> None:
        self.app = app                
        self.logger = logger
        self.IP = IP
        self.logger.info('started webserver at {}, ready to receive requests.'.format(self.IP))
        self.file_server_paths = file_server_paths

    def find_handler(self, request : HTTPServerRequest):
        
        start_time = perf_counter()
        log_request(request, self.logger)
        
        if (request.method == GET):            
            for path in self.file_server_paths["STATIC_ROUTES"].keys():
                if request.path.startswith(path):
                    print("static handler")
                    return self.app.get_handler_delegate(request, FileHandlerResource, 
                        target_kwargs=dict(
                        path=self.file_server_paths["STATIC_ROUTES"][path].directory              
                        ),
                        path_args=[bytes(request.path.split('/')[-1], encoding='utf-8')])
            handler = GetResource
        elif (request.method == POST):
            handler = PostResource
        elif (request.method == PUT):
            handler = PutResource
        elif (request.method == DELETE):
            handler = DeleteResource
        elif (request.method == OPTIONS):
            handler = OptionsResource
        else:
            handler = OptionsResource

        return self.app.get_handler_delegate(request, handler, 
                    target_kwargs=dict(
                        client_address='*',
                        start_time=start_time                        
                    ))



__http_methods__ = {
    GET  : get, 
    POST : post,
    PUT  : put,
    DELETE : delete
}

class HTTPServer(Parameterized):

    address   = IPAddress( default = '0.0.0.0', 
                    doc = "set custom IP address, default is localhost (0.0.0.0)" )
    port      = Integer  ( default = 8080, bounds = (0, 65535), 
                    doc = "the port at which the server should be run (unique)" )
    protocol_version = Selector ( objects = [1.1, 2], default = 2, 
                    doc = """for HTTP 2, SSL is mandatory. HTTP2 is recommended. 
                    When no SSL configurations are provided, defaults to 1.1""" )
    logger    = ClassSelector ( class_ = logging.Logger, default = None, allow_None = True, 
                    doc = "Supply a custom logger here or set log_level parameter to a valid value" )
    log_level = Selector ( objects = [logging.DEBUG, logging.INFO, logging.ERROR, logging.CRITICAL, logging.ERROR], 
                    default = logging.INFO, 
                    doc = "Alternative to logger, this creates an internal logger with the specified log level" )
    consumers = TypedList ( item_type = (RemoteObject, Consumer, str), default = None, allow_None = True, 
                    doc = "Remote Objects to be served by the HTTP server" )
    subscription = String ( default = None, allow_None = True, 
                    doc = "Host Server to subscribe to coordinate starting sequence of remote objects & web GUI" ) 
    json_serializer = ClassSelector ( class_ = JSONSerializer,  default = None, allow_None = True,
                    doc = "optionally, supply your own JSON serializer for custom types" )
    ssl_context = ClassSelector ( class_ = ssl.SSLContext , default = None, allow_None = True, 
                    doc = "use it for highly customized SSL context to provide encrypted communication" )    
    certfile    = String ( default = None, allow_None = True, 
                    doc = """alternative to SSL context, provide certificate file & key file to allow the server 
                            to create a SSL connection on its own""" )
    keyfile     = String ( default = None, allow_None = True, 
                    doc = """alternative to SSL context, provide certificate file & key file to allow the server 
                            to create a SSL connection on its own""" )
    server_network_interface = String ( default = 'Ethernet',  
                    doc = """Currently there is no logic to detect the IP addresss (as externally visible) correctly, therefore 
                    please send the network interface name to retrieve the IP. If a DNS server is present or , you may leave 
                    this field""" )

    def __init__(self, consumers = None, port = 8080, address = '0.0.0.0', subscription = None, logger = None, 
                log_level = logging.INFO, certfile = None, keyfile = None, json_serializer = None,  ssl_context = None, 
                protocol_version = 2 ) -> None:
        super().__init__(
            consumers = consumers,
            port = port, 
            address = address, 
            subscription = subscription,
            logger = logger, 
            log_level = log_level,
            json_serializer = json_serializer, 
            protocol_version = protocol_version,
            certfile = certfile, 
            keyfile = keyfile,
            ssl_context  = ssl_context
        )
        # functions that the server directly serves 
        self.server_process = None
        self.resources = dict(
            FILE_SERVER = dict(STATIC_ROUTES = dict(), DYNAMIC_ROUTES = dict()),
            GET     = dict(STATIC_ROUTES = dict(), DYNAMIC_ROUTES = dict()),
            POST    = dict(STATIC_ROUTES = dict(), DYNAMIC_ROUTES = dict()),
            PUT     = dict(STATIC_ROUTES = dict(), DYNAMIC_ROUTES = dict()),
            DELETE  = dict(STATIC_ROUTES = dict(), DYNAMIC_ROUTES = dict()),
            OPTIONS = dict(STATIC_ROUTES = dict(), DYNAMIC_ROUTES = dict())
        )

    @property
    def all_ok(self) -> bool:
        IP = "{}:{}".format(self.address, self.port)
        if self.logger is None:
            self.logger = create_default_logger('{}|{}'.format(self.__class__.__name__, IP), self.log_level)
        UtilitiesConsumer =  Consumer(HTTPServerUtilities, logger = self.logger, db_config_file = None, 
                        zmq_client_pool = None, instance_name = SERVER_INSTANCE_NAME,
                        remote_object_info = None)
        if self.consumers is None:
            self.consumers = [UtilitiesConsumer]
        else: 
            self.consumers.append(UtilitiesConsumer)
        return True

    def start(self, block : bool = False) -> None:
        assert self.all_ok, 'HTTPServer all is not ok before starting' # Will always be True or cause some other exception
        if block:
            start_server(self.address, self.port, self.logger, self.subscription, self.consumers, self.resources, #type: ignore
                         self.ssl_context, self.json_serializer)
        else:
            self.server_process = Process(target = start_server, args = (self.address, self.port, self.logger, 
                        self.subscription, self.consumers, self.resources, self.ssl_context, self.json_serializer))
            self.server_process.start() 

    def stop(self) -> None:
        if self.server_process:
            try:
                self.server_process.close() 
            except ValueError:
                self.server_process.kill() 
            self.server_process = None

    def http_method_decorator(self, http_method : str, URL_path = USE_OBJECT_NAME):
        def decorator(given_func):
            func = remote_method(URL_path=decorator.URL_path, 
                            http_method=decorator.http_method)(given_func)
            self.resources[http_method]["STATIC_ROUTES"][decorator.URL_path] = HTTPServerResourceData (
                                            what=CALLABLE,
                                            instance_name='',
                                            instruction=func,
                                            fullpath=decorator.URL_path,
                                        )
                
            return func
        decorator.http_method = http_method 
        decorator.URL_path = URL_path
        return decorator

    def get(self, URL_path = USE_OBJECT_NAME):
        return self.http_method_decorator(GET, URL_path)
    
    def post(self, URL_path = USE_OBJECT_NAME):
        return self.http_method_decorator(POST, URL_path)
    
    def put(self, URL_path = USE_OBJECT_NAME):
        return self.http_method_decorator(PUT, URL_path)

    def delete(self, URL_path = USE_OBJECT_NAME):
        return self.http_method_decorator(DELETE, URL_path)
                        


def start_server(address : str, port : int, logger : logging.Logger, subscription : str, 
            consumers : List[Union[Consumer, RemoteObject, str]], resources : Dict[str, Any], ssl_context : ssl.SSLContext, 
            json_serializer : JSONSerializer) -> None:
    """
    A separate function exists to start the server to be able to fork from current process
    """
    event_loop = ioloop.IOLoop.current()
    event_loop.run_sync(lambda : _setup_server(address, port, logger, subscription, consumers, resources, ssl_context, 
                                               json_serializer))
    # written as async function because zmq client is async, therefore run_sync for current use
    if BaseRequestHandler.zmq_client_pool is not None:
        event_loop.add_callback(BaseRequestHandler.zmq_client_pool.poll)
    event_loop.start()


async def _setup_server(address : str, port : int, logger : logging.Logger, subscription : str, 
                consumers : List[Union[Consumer, RemoteObject, str]], resources : Dict[str, Dict[str, Any]], 
                ssl_context : ssl.SSLContext, json_serializer  : JSONSerializer, version : float = 2) -> None:
    IP = "{}:{}".format(address, port)
    instance_names = []
    server_remote_objects = {}
    remote_object_info = []
    if consumers is not None:
        for consumer in consumers:
            if isinstance(consumer, RemoteObject):
                server_remote_objects[consumer.instance_name] = consumer
                update_resources(resources, consumer.httpserver_resources) 
                remote_object_info.append(consumer.object_info) 
            elif isinstance(consumer, Consumer): 
                instance = consumer.consumer(*consumer.args, **consumer.kwargs)
                server_remote_objects[instance.instance_name] = instance
                update_resources(resources, instance.httpserver_resources)
                remote_object_info.append(instance.object_info) 
            else:
                instance_names.append(consumer)
   
    zmq_client_pool = MessageMappedZMQClientPool(instance_names, IP, json_serializer = json_serializer)
    for client in zmq_client_pool:
        await client.handshake_complete() 
        _, _, _, _, _, reply = await client.read_attribute('/'+client.server_instance_name + '/resources/http', raise_client_side_exception = True)
        update_resources(resources, reply["returnValue"]) # type: ignore
        _, _, _, _, _, reply = await client.read_attribute('/'+client.server_instance_name + '/object-info', raise_client_side_exception = True)
        remote_object_info.append(RemoteObjectDB.RemoteObjectInfo(**reply["returnValue"])) # Should raise an exception if returnValue key is not found for some reason. 
    
    for RO in server_remote_objects.values():
        if isinstance(RO, HTTPServerUtilities):
            RO.zmq_client_pool = zmq_client_pool
            RO.remote_object_info = remote_object_info
            RO._httpserver_resources = resources
            if subscription:
                await RO.subscribe_to_host(subscription, port)
                break
    
    BaseRequestHandler.zmq_client_pool = zmq_client_pool
    BaseRequestHandler.json_serializer = zmq_client_pool.json_serializer
    BaseRequestHandler.local_objects   = server_remote_objects
    GetResource.resources = resources.get(GET,  dict())        
    PostResource.resources = resources.get(POST, dict()) 
    PutResource.resources = resources.get(PUT,  dict()) 
    DeleteResource.resources = resources.get(DELETE, dict())
    OptionsResource.resources = resources.get(OPTIONS, dict())
    # log_resources(logger, resources)   
    Router = CustomRouter(Application(), logger, IP, resources.get('FILE_SERVER'))   
    # if version == 2:   
    #     S = TornadoHTTP2Server(Router, ssl_options=ssl_context)
    # else: 
    S = TornadoHTTP1Server(Router, ssl_options=ssl_context)    
    S.listen(port = port, address = address) 


__all__ = ['HTTPServer']