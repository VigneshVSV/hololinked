import zmq
import asyncio
import logging
import socket
import ssl
import typing
from tornado import ioloop
from tornado.web import Application
from tornado.httpserver import HTTPServer as TornadoHTTP1Server
from tornado.httpclient import AsyncHTTPClient, HTTPRequest

# from tornado_http2.server import Server as TornadoHTTP2Server 


from ..param import Parameterized
from ..param.parameters import (Integer, IPAddress, ClassSelector, Selector, TypedList, String)
from .constants import CommonRPC, HTTPServerTypes, ResourceTypes, ServerMessage
from .webserver_utils import get_IP_from_interface
from .data_classes import HTTPResource, ServerSentEvent
from .utils import get_default_logger, run_coro_sync
from .serializers import JSONSerializer
from .database import RemoteObjectInformation
from .zmq_message_brokers import  AsyncZMQClient, MessageMappedZMQClientPool
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
                            doc="serves request and sets CORS only from these clients, other clients are reject with 403")

    def __init__(self, remote_objects : typing.List[str], *, port : int = 8080, address : str = '0.0.0.0', 
                host : str = None, logger : typing.Optional[logging.Logger] = None, log_level : int = logging.INFO, 
                certfile : str = None, keyfile : str = None, serializer : JSONSerializer = None,
                allowed_clients : typing.Union[str, typing.Iterable[str]] = None,   
                ssl_context : ssl.SSLContext = None, protocol_version : int = 1, 
                network_interface : str = 'Ethernet', request_handler : RPCHandler = RPCHandler, 
                event_handler : typing.Union[BaseHandler, EventHandler] = EventHandler) -> None:
        super().__init__(
            remote_objects=remote_objects,
            port=port, 
            address=address, 
            host=host,
            logger=logger, 
            log_level=log_level,
            serializer=serializer or JSONSerializer(), 
            protocol_version=protocol_version,
            certfile=certfile, 
            keyfile=keyfile,
            ssl_context=ssl_context,
            network_interface=network_interface,
            request_handler=request_handler,
            event_handler=event_handler,
            allowed_clients=allowed_clients if allowed_clients is not None else []
        )
        self._type = HTTPServerTypes.REMOTE_OBJECT_SERVER
        self._lost_remote_objects = dict() # see update_router_with_remote_object
               

    @property
    def all_ok(self) -> bool:
        self._IP = f"{self.address}:{self.port}"
        if self.logger is None:
            self.logger = get_default_logger('{}|{}'.format(self.__class__.__name__, 
                                            f"{self.address}:{self.port}"), 
                                            self.log_level)
            
        self.app = Application(handlers=[
            (r'/remote-objects', RemoteObjectsHandler, dict(request_handler=self.request_handler, 
                                                        event_handler=self.event_handler))
        ])
        
        self.zmq_client_pool = MessageMappedZMQClientPool(self.remote_objects, identity=self._IP, 
                                                    deserialize_server_messages=False, json_serializer=self.serializer)
    
        event_loop = asyncio.get_event_loop()
        event_loop.call_soon(lambda : asyncio.create_task(self.update_router_with_remote_objects()))
        event_loop.call_soon(lambda : asyncio.create_task(self.subscribe_to_host()))
        event_loop.call_soon(lambda : asyncio.create_task(self.zmq_client_pool.poll()) )
        
        if self.protocol_version == 2:
            raise NotImplementedError("Current HTTP2 is not implemented.")
            self.server = TornadoHTTP2Server(self.app, ssl_options=self.ssl_context)
        else:
            self.server = TornadoHTTP1Server(self.app, ssl_options=self.ssl_context)
        return True
    

    async def subscribe_to_host(self):
        if self.host is None:
            return
        client = AsyncHTTPClient()
        for i in range(300): # try for five minutes
            try:
                res = await client.fetch(HTTPRequest(
                        url=f"{self.host}/subscribers",
                        method='POST',
                        body=JSONSerializer.dumps(dict(
                                hostname=socket.gethostname(),
                                IPAddress=get_IP_from_interface(self.network_interface), 
                                port=self.port, 
                                type=self._type,
                                https=self.ssl_context is not None 
                            )),
                        validate_cert=False,
                        headers={"content-type" : "application/json"}
                    ))
            except Exception as ex:
                self.logger.error(f"Could not subscribe to host {self.host}. error : {str(ex)}, error type : {type(ex)}.")
                if i >= 299:
                    raise ex from None
            else: 
                if res.code in [200, 201]:
                    self.logger.info(f"subsribed successfully to host {self.host}")
                    break
                elif i >= 299:
                    raise RuntimeError(f"could not subsribe to host {self.host}. response {JSONSerializer.loads(res.body)}")
            await asyncio.sleep(1)
        # we lose the client anyway so we close it. if we decide to reuse the client, changes needed
        client.close() 


    def listen(self) -> None:
        assert self.all_ok, 'HTTPServer all is not ok before starting' # Will always be True or cause some other exception   
        self.event_loop = ioloop.IOLoop.current()
        self.server.listen(port=self.port, address=self.address)    
        self.logger.info(f'started webserver at {self._IP}, ready to receive requests.')
        self.event_loop.start()

    def stop(self) -> None:
        self.server.stop()
        run_coro_sync(self.server.close_all_connections())
        self.event_loop.close()    


    async def update_router_with_remote_objects(self)-> None:
        """
        updates HTTP router with paths from newly instantiated ``RemoteObject``s
        """
        await asyncio.gather(*[self.update_router_with_remote_object(client) for client in self.zmq_client_pool])

        
    async def update_router_with_remote_object(self, client : AsyncZMQClient):
        if client.instance_name in self._lost_remote_objects:
            # Just to avoid duplication of this call as we proceed at single client level and not message mapped level
            return 
        self._lost_remote_objects[client.instance_name] = client
        self.logger.info(f"attempting to update router with remote object {client.instance_name}.")
        while True:
            try:
                await client.handshake_complete()
                resources = dict() # type: typing.Dict[str, HTTPResource]
                reply = (await client.async_execute(
                                instruction=CommonRPC.http_resource_read(client.instance_name), 
                                raise_client_side_exception=True
                            ))[ServerMessage.DATA]
                resources.update(reply)

                handlers = []
                for instruction, http_resource in resources.items():
                    if http_resource["what"] in [ResourceTypes.PARAMETER, ResourceTypes.CALLABLE] :
                        resource = HTTPResource(**http_resource)
                        handlers.append((resource.fullpath, self.request_handler, dict(
                                                                resource=resource, 
                                                                owner=self                                                     
                                                            )))
                    elif http_resource["what"] == ResourceTypes.EVENT:
                        resource = ServerSentEvent(**http_resource)
                        handlers.append((instruction, self.event_handler, dict(
                                                                resource=resource,
                                                                owner=self 
                                                            )))
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
                    RPCHandler is the base handler of this package for RPC purposes
                    resource goes into target kwargs as the HTTPResource generated by 
                        remote_method and RemoteParamater contains all the info given 
                        to make RPCHandler work
                    """
                self.app.wildcard_router.add_rules(handlers)
                self.logger.info(f"updated router with remote object {client.instance_name}.")
                break
            except Exception as ex:
                self.logger.error(f"error while trying to update router with remote object - {str(ex)}. " +
                                  "Trying again in 5 seconds")
                await asyncio.sleep(5)
       
        try:
            reply = (await client.async_execute(
                        instruction=CommonRPC.object_info_read(client.instance_name), 
                        raise_client_side_exception=True
                    ))[ServerMessage.DATA]
            object_info = RemoteObjectInformation(**reply)
            object_info.http_server ="{}://{}:{}".format("https" if self.ssl_context is not None else "http", 
                                                socket.gethostname(), self.port)
    
            await client.async_execute(
                        instruction=CommonRPC.object_info_write(client.instance_name),
                        arguments=dict(value=object_info), 
                        raise_client_side_exception=True
                    )
        except Exception as ex:
            self.logger.error(f"error while trying to update remote object with HTTP server details - {str(ex)}. " +
                                "Trying again in 5 seconds")
        self.zmq_client_pool.poller.register(client.socket, zmq.POLLIN)
        self._lost_remote_objects.pop(client.instance_name)
               
    


__all__ = ['HTTPServer']