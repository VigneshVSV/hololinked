# routing ideas from https://www.tornadoweb.org/en/branch6.3/routing.html
import typing
import logging
from json import JSONDecodeError
from tornado.web import RequestHandler, StaticFileHandler
from tornado.iostream import StreamClosedError

from .constants import CommonInstructions
from .serializers import JSONSerializer
from .zmq_message_brokers import AsyncZMQClient, MessageMappedZMQClientPool, EventConsumer
from .webserver_utils import *
from .utils import current_datetime_ms_str
from .data_classes import HTTPResource, ServerSentEvent



class BaseHandler(RequestHandler):

    zmq_client_pool : MessageMappedZMQClientPool
    json_serializer : JSONSerializer
    clients : str
    logger : logging.Logger

    def initialize(self, resource : typing.Union[HTTPResource, ServerSentEvent]) -> None:
        self.resource = resource

    def set_headers(self):
        raise NotImplementedError("implement set headers in child class to call it",
                            " before directing the request to RemoteObject")
    
    def prepare_arguments(self) -> typing.Dict[str, typing.Any]:
        """
        merges all arguments to a single JSON body (for example, to provide it to 
        method execution as parameters)
        """
        try:
            arguments = self.json_serializer.loads(self.request.arguments)
        except JSONDecodeError:
            arguments = {}
        if len(self.request.query_arguments) >= 1:
            for key, value in self.request.query_arguments.items():
                if len(value) == 1:
                    arguments[key] = self.json_serializer.loads(value[0]) 
                else:
                    arguments[key] = [self.json_serializer.loads(val) for val in value]
        if len(self.request.body) > 0:
            arguments.update(self.json_serializer.loads(self.request.body))
        return arguments



class RPCHandler(BaseHandler):

    def set_headers(self):
        self.set_status(200)
        self.set_header("Content-Type" , "application/json")  


    async def get(self):
        if not self.resource.method == 'GET':
            self.set_status(404)
        else:
            self.set_headers()
            await self.handle_through_remote_object()        
        self.finish()

    async def post(self):
        if not self.resource.method == 'POST':
            self.set_status(404, "not found")
        else:
            self.set_headers()
            await self.handle_through_remote_object()        
        self.finish()
    
    async def patch(self):
        if not self.resource.method == 'PATCH':
            self.set_status(404, "not found")
        else:
            self.set_headers()
            await self.handle_through_remote_object()        
        self.finish()
    
    async def put(self):
        if not self.resource.method == 'PUT':
            self.set_status(404, "not found")
        else:
            self.set_headers()
            await self.handle_through_remote_object()        
        self.finish()
    
    async def delete(self):
        if not self.resource.method == 'DELETE':
            self.set_status(404, "not found")
        else:
            self.set_headers()
            await self.handle_through_remote_object()        
        self.finish()

    async def options(self):
        self.set_status(204)
        self.add_header("Access-Control-Allow-Origin", self.clients)
        self.set_header("Access-Control-Allow-Headers", "*")
        self.set_header("Access-Control-Allow-Methods", ', '.join(self.resource.method))
        self.finish()
    

    async def handle_through_remote_object(self) -> None:
        try:
            arguments = self.prepare_arguments()
            context = dict(fetch_execution_logs=arguments.pop('fetch_execution_logs', False))
            timeout = arguments.pop('timeout', None)
            if self.resource.request_as_argument:
                arguments['request'] = self.request
            reply = await self.zmq_client_pool.async_execute(self.resource.instance_name, 
                                    self.resource.instruction, arguments,
                                    context=context, raise_client_side_exception=True, 
                                    server_timeout=timeout, client_timeout=None) # type: ignore
            # message mapped client pool currently strips the data part from return message
            # and provides that as reply directly 
        except Exception as ex:
            reply = self.json_serializer.dumps(format_exception_as_json(ex))
        if reply:
            self.write(reply)
        


class EventHandler(BaseHandler):

    def initialize(self, resource : typing.Union[HTTPResource, ServerSentEvent]) -> None:
        self.resource = resource

    def set_headers(self) -> None:
        self.set_header("Content-Type", "text/event-stream")
        self.set_header("Cache-Control", "no-cache")
        self.set_header("Connection", "keep-alive")

    async def get(self):
        self.set_headers()
        await self.handle_datastream()
        self.finish()

    async def options(self):
        self.set_status(204)
        self.set_header("Access-Control-Allow-Origin", self.clients)
        self.set_header("Access-Control-Allow-Methods", 'GET')
        self.finish()


    async def handle_datastream(self) -> None:    
        try:                        
            event_consumer = EventConsumer(self.request.path, self.resource.socket_address, 
                            f"{self.resource.event_name}|HTTPEvent|{current_datetime_ms_str()}")
            data_header = b'data: %s\n\n'
            while True:
                try:
                    data = await event_consumer.receive_event()
                    if data:
                        # already JSON serialized 
                        self.write(data_header % data)
                        await self.flush()
                        self.logger.debug(f"new data sent - {self.resource.event_name}")
                except StreamClosedError:
                    break 
                except Exception as ex:
                    self.write(data_header % self.json_serializer.dumps(
                        format_exception_as_json(ex)))
            event_consumer.exit()
        except Exception as ex:
            self.write(data_header % self.json_serializer.dumps(
                        format_exception_as_json(ex)))


    async def handled_imagestream(self) -> None:
        try:
            self.set_header("Content-Type", "application/x-mpegURL")
            event_consumer = EventConsumer(self.request.path, self.resource.socket_address, 
                            f"{self.resource.event_name}|HTTPEvent|{current_datetime_ms_str()}")         
            self.write("#EXTM3U\n")
            delimiter = "#EXTINF:{},\n"
            data_header = b'data:image/jpeg;base64,%s\n'
            while True:
                try:
                    data = await event_consumer.receive_event()
                    if data:
                        # already serialized 
                        self.write(delimiter)
                        self.write(data_header % data)
                        await self.flush()
                        self.logger.debug(f"new image sent - {self.resource.event_name}")
                except StreamClosedError:
                    break 
                except Exception as ex:
                    self.write(data_header % self.json_serializer.dumps(
                        format_exception_as_json(ex)))
            event_consumer.exit()
        except Exception as ex:
            self.write(data_header % self.json_serializer.dumps(
                        format_exception_as_json(ex)))
    


class FileHandler(StaticFileHandler):

    @classmethod
    def get_absolute_path(cls, root: str, path: str) -> str:
        """
        Returns the absolute location of ``path`` relative to ``root``.

        ``root`` is the path configured for this `StaticFileHandler`
        (in most cases the ``static_path`` `Application` setting).

        This class method may be overridden in subclasses.  By default
        it returns a filesystem path, but other strings may be used
        as long as they are unique and understood by the subclass's
        overridden `get_content`.

        .. versionadded:: 3.1
        """
        return root+path
    


class RemoteObjectsHandler(BaseHandler):

    def initialize(self, resource: HTTPResource | ServerSentEvent, request_handler) -> None:
        self.request_handler = request_handler
        return super().initialize(resource)
    
    async def get(self):
        with self.async_session() as session:
            pass
    
    async def post(self):
        arguments = self.prepare_arguments()
        self.set_status(200)
        await self.connect_to_remote_object()
        self.finish()

    
    async def connect_to_remote_object(self, clients : typing.List[AsyncZMQClient]):
        resources = dict()
        for client in clients:
            await client.handshake_complete()
            _, _, _, _, _, reply = await client.async_execute(
                        f'/{client.server_instance_name}{CommonInstructions.HTTP_RESOURCES}', 
                        raise_client_side_exception=True)
            update_resources(resources, reply["returnValue"]) # type: ignore
            # _, _, _, _, _, reply = await client.read_attribute('/'+client.server_instance_name + '/object-info', raise_client_side_exception = True)
            # remote_object_info.append(RemoteObjectDB.RemoteObjectInfo(**reply["returnValue"])) # Should raise an exception if returnValue key is not found for some reason. 
        
        handlers = []
        for route, http_resource in resources.items():
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
            RPCHandler is the base handler of this package for RPC purposes
            resource goes into target kwargs as the HTTPResource generated by 
                remote_method and RemoteParamater contains all the info given 
                to make RPCHandler work
            """
