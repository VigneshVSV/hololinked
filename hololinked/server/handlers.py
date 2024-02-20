# routing ideas from https://www.tornadoweb.org/en/branch6.3/routing.html
import typing
from json import JSONDecodeError
from tornado.web import RequestHandler, StaticFileHandler
from tornado.iostream import StreamClosedError
from time import perf_counter

from .serializers import JSONSerializer
from .zmq_message_brokers import MessageMappedZMQClientPool, EventConsumer
from .webserver_utils import *
from .utils import current_datetime_ms_str
from .data_classes import HTTPResource, ServerSentEvent



class RPCHandler(RequestHandler):

    zmq_client_pool : MessageMappedZMQClientPool
    json_serializer : JSONSerializer
    clients : str

    def initialize(self, resource : typing.Union[HTTPResource, ServerSentEvent]) -> None:
        self.resource = resource

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
    

    def prepare_arguments(self, 
            path_arguments : typing.Optional[typing.Dict] = None
        ) -> typing.Dict[str, typing.Any]:
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
        


class EventHandler(RequestHandler):

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

    def options(self):
        self.set_status(204)
        self.add_header("Access-Control-Allow-Origin", self.clients)
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
                        # print(f"data sent")
                        self.write(data_header % data)
                        await self.flush()
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
                        # print(f"image data sent {data[0:100]}")
                        await self.flush()
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