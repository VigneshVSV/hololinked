# routing ideas from https://www.tornadoweb.org/en/branch6.3/routing.html
import traceback
import typing
from typing import List, Dict, Any, Union, Callable, Tuple
from types import FunctionType
from tornado.web import RequestHandler, StaticFileHandler
from tornado.iostream import StreamClosedError
from tornado.httputil import HTTPServerRequest
from time import perf_counter

from .constants import (IMAGE_STREAM, EVENT, CALLABLE, ATTRIBUTE, FILE)
from .serializers import JSONSerializer
from .path_converter import extract_path_parameters
from .zmq_message_brokers import MessageMappedZMQClientPool, EventConsumer
from .webserver_utils import log_request
from .remote_object import RemoteObject
from .eventloop import EventLoop
from .utils import current_datetime_ms_str
from .data_classes import FileServerData

# UnknownHTTPServerData = HTTPServerResourceData(
#     what = 'unknown', 
#     instance_name = 'unknown',
#     fullpath='unknown',
#     instruction = 'unknown'
# )



class FileHandlerResource(StaticFileHandler):

    @classmethod
    def get_absolute_path(cls, root: str, path: str) -> str:
        """Returns the absolute location of ``path`` relative to ``root``.

        ``root`` is the path configured for this `StaticFileHandler`
        (in most cases the ``static_path`` `Application` setting).

        This class method may be overridden in subclasses.  By default
        it returns a filesystem path, but other strings may be used
        as long as they are unique and understood by the subclass's
        overridden `get_content`.

        .. versionadded:: 3.1
        """
        return root+path
    


class BaseRequestHandler(RequestHandler):
    """
    Defines functions common to Request Handlers
    """  
    zmq_client_pool : Union[MessageMappedZMQClientPool, None] = None 
    json_serializer : JSONSerializer
    resources       : Dict[str, Dict[str, Union[FileServerData, typing.Any]]]
                                                # HTTPServerResourceData, HTTPServerEventData, 
    own_resources   : dict 
    local_objects   : Dict[str, RemoteObject]
   
    def initialize(self, client_address : str, start_time : float) -> None:
        self.client_address = client_address
        self.start_time = start_time

    async def handle_client(self) -> None:
        pass 

    def prepare_arguments(self, path_arguments : typing.Optional[typing.Dict] = None) -> Dict[str, Any]:
        arguments = {}
        for key, value in self.request.query_arguments.items():
            if len(value) == 1:
                arguments[key] = self.json_serializer.loads(value[0]) 
            else:
                arguments[key] = [self.json_serializer.loads(val) for val in value]
        if len(self.request.body) > 0:
            arguments.update(self.json_serializer.loads(self.request.body))
        if path_arguments is not None:
            arguments.update(path_arguments)
        print(arguments)
        return arguments

    async def handle_func(self, instruction : Tuple[Callable, bool], arguments):
        func, iscoroutine = instruction, instruction.scada_info.iscoroutine
        if iscoroutine:
            return self.json_serializer.dumps({
                "responseStatusCode" : 200, 
                "returnValue"        : await func(**arguments)  
            }) 
        else:
            return self.json_serializer.dumps({
                "responseStatusCode" : 200, 
                "returnValue"        : func(**arguments) 
            })
       
    async def handle_bound_method(self, info, arguments):
        instance = self.local_objects[info.instance_name]
        return self.json_serializer.dumps({
                "responseStatusCode" : 200,
                "returnValue" : await EventLoop.execute_once(info.instance_name, instance, 
                                                                    info.instruction, arguments),
                "state"       : {
                    info.instance_name : instance.state_machine.current_state if instance.state_machine is not None else None
                }
            })
            
    async def handle_instruction(self, info, path_arguments : typing.Optional[typing.Dict] = None) -> None:
        self.set_status(200)
        self.add_header("Access-Control-Allow-Origin", self.client_address)
        self.set_header("Content-Type" , "application/json")  
        try:
            arguments = self.prepare_arguments(path_arguments)
            context = dict(fetch_execution_logs = arguments.pop('fetch_execution_logs', False))
            timeout = arguments.pop('timeout', 3)
            if info.http_request_as_argument:
                arguments['request'] = self.request
            if isinstance(info.instruction, FunctionType):
                reply = await self.handle_func(info.instruction, arguments) # type: ignore
            elif info.instance_name in self.local_objects: 
                reply = await self.handle_bound_method(info, arguments)         
            elif self.zmq_client_pool is None:
                raise AttributeError("wrong resource finding logic - contact developer.")
            else:
                # let the body be decoded on the remote object side
                reply = await self.zmq_client_pool.async_execute(info.instance_name, info.instruction, arguments,
                                                            context, False, timeout) # type: ignore
        except Exception as E:
            reply = self.json_serializer.dumps({
                "responseStatusCode" : 500,
                "exception" : {
                    "message" : str(E),
                    "type"    : repr(E).split('(', 1)[0],
                    "traceback" : traceback.format_exc().splitlines(),
                    "notes"   : E.__notes__ if hasattr(E, "__notes__") else None # type: ignore
                }
            })    
        if reply:
            self.write(reply)
        self.add_header("Execution-Time", f"{((perf_counter()-self.start_time)*1000.0):.4f}")
        self.finish()

    async def handled_through_remote_object(self, info : HTTPServerRequest) -> bool:     
        data = self.resources["STATIC_ROUTES"].get(self.request.path, UnknownHTTPServerData)
        if data.what == CALLABLE or data.what == ATTRIBUTE: 
            # Cannot use 'is' operator like 'if what is CALLABLE' because the remote object from which 
            # CALLABLE string was fetched is in another process
            await self.handle_instruction(data) # type: ignore
            return True 
        if data.what == EVENT:
            return False
        
        for route in self.resources["DYNAMIC_ROUTES"].values():
            arguments = extract_path_parameters(self.request.path, route.path_regex, route.param_convertors)
            if arguments and route.what != FILE:
                await self.handle_instruction(route, arguments)
                return True                
        return False
        
    async def handled_as_datastream(self, request : HTTPServerRequest) -> bool:                             
        event_info = self.resources["STATIC_ROUTES"].get(self.request.path, UnknownHTTPServerData)
        if event_info.what == EVENT: 
            try:
                event_consumer = EventConsumer(request.path, event_info.socket_address, 
                                            f"{request.path}_HTTPEvent@"+current_datetime_ms_str())
            except Exception as E:
                reply = self.json_serializer.dumps({
                    "responseStatusCode" : 500,
                    "exception" : {
                        "message" : str(E),
                        "type"    : repr(E).split('(', 1)[0],
                        "traceback" : traceback.format_exc().splitlines(),
                        "notes"   : E.__notes__ if hasattr(E, "__notes__") else None # type: ignore
                    }
                })    
                self.set_status(404)
                self.add_header('Access-Control-Allow-Origin', self.client_address)
                self.add_header('Content-Type' , 'application/json')  
                self.write(reply)
                self.finish()
                return True 
            
            self.set_status(200)
            self.set_header('Access-Control-Allow-Origin', self.client_address)
            self.set_header("Content-Type", "text/event-stream")
            self.set_header("Cache-Control", "no-cache")
            self.set_header("Connection", "keep-alive")
            # Need to check if this helps as events with HTTP alone is not reliable
            # self.set_header("Content-Security-Policy", "connect-src 'self' http://localhost:8085;")
            data_header = b'data: %s\n\n'
            while True:
                try:
                    data = await event_consumer.receive_event()
                    if data:
                        # already JSON serialized 
                        print(f"data sent")
                        self.write(data_header % data)
                        await self.flush()
                except StreamClosedError:
                    break 
                except Exception as E:
                    print({
                        "responseStatusCode" : 500,
                        "exception" : {
                            "message" : str(E),
                            "type"    : repr(E).split('(', 1)[0],
                            "traceback" : traceback.format_exc().splitlines(),
                            "notes"   : E.__notes__ if hasattr(E, "__notes__") else None # type: ignore
                    }})
            self.finish()
            event_consumer.exit()
            return True 
        return False
    
    async def handled_as_imagestream(self, request : HTTPServerRequest) -> bool:
        event_info = self.resources["STATIC_ROUTES"].get(self.request.path, UnknownHTTPServerData)
        if event_info.what == IMAGE_STREAM: 
            try:
                event_consumer = EventConsumer(request.path, event_info.socket_address, 
                                            f"{request.path}_HTTPEvent@"+current_datetime_ms_str())
            except Exception as E:
                reply = self.json_serializer.dumps({
                    "responseStatusCode" : 500,
                    "exception" : {
                        "message" : str(E),
                        "type"    : repr(E).split('(', 1)[0],
                        "traceback" : traceback.format_exc().splitlines(),
                        "notes"   : E.__notes__ if hasattr(E, "__notes__") else None # type: ignore
                    }
                })    
                self.set_status(404)
                self.add_header('Access-Control-Allow-Origin', self.client_address)
                self.add_header('Content-Type' , 'application/json')  
                self.write(reply)
                self.finish()
                return True 
            
            self.set_status(200)
            self.set_header('Access-Control-Allow-Origin', self.client_address)
            self.set_header("Content-Type", "application/x-mpegURL")
            self.set_header("Cache-Control", "no-cache")
            self.set_header("Connection", "keep-alive")
            self.write("#EXTM3U\n")
            # Need to check if this helps as events with HTTP alone is not reliable
            delimiter = "#EXTINF:{},\n"
            data_header = b'data:image/jpeg;base64,%s\n'
            while True:
                try:
                    data = await event_consumer.receive_event()
                    if data:
                        # already JSON serialized 
                        self.write(delimiter)
                        self.write(data_header % data)
                        print(f"image data sent {data[0:100]}")
                        await self.flush()
                except StreamClosedError:
                    break 
                except Exception as E:
                    print({
                        "responseStatusCode" : 500,
                        "exception" : {
                            "message" : str(E),
                            "type"    : repr(E).split('(', 1)[0],
                            "traceback" : traceback.format_exc().splitlines(),
                            "notes"   : E.__notes__ if hasattr(E, "__notes__") else None # type: ignore
                    }})
            self.finish()
            event_consumer.exit()
            return True 
        return False


 

class GetResource(BaseRequestHandler):

    async def handled_as_filestream(self, request : HTTPServerRequest) -> bool:
        """this method is wrong and does not work"""
        for route in self.resources["DYNAMIC_ROUTES"].values():
            arguments = extract_path_parameters(self.request.path, route.path_regex, route.param_convertors)
            if arguments and route.what == FILE:
                file_handler = FileHandler(self.application, request, path=route.directory)
                # file_handler.initialize(data.directory) # type: ignore
                await file_handler.get(arguments["filename"])
                return True
        return False 

    async def get(self):
        # log_request(self.request)
        if (await self.handled_through_remote_object(self.request)):           
            return  
       
        elif (await self.handled_as_datastream(self.request)):
            return 
        
        elif (await self.handled_as_imagestream(self.request)):
            return 
        
        elif self.request.path in self.own_resources:
            func = self.own_resources[self.request.path]
            body = self.prepare_arguments()
            func(self, body)
            return

        self.set_status(404)
        self.add_header("Access-Control-Allow-Origin", self.client_address)
        self.finish()

    def paths(self, body):
        self.set_status(200)
        self.add_header("Access-Control-Allow-Origin", self.client_address)
        self.add_header("Content-Type" , "application/json")
        resources = dict(
            GET     = {
                "STATIC_ROUTES" : GetResource.resources["STATIC_ROUTES"].keys(),
                "DYNAMIC_ROUTES" : GetResource.resources["DYNAMIC_ROUTES"].keys()
            },
            POST    = {
                "STATIC_ROUTES" : PostResource.resources["STATIC_ROUTES"].keys(),
                "DYNAMIC_ROUTES" : PostResource.resources["DYNAMIC_ROUTES"].keys()
            },
            PUT     = {
                "STATIC_ROUTES" : PutResource.resources["STATIC_ROUTES"].keys(),
                "DYNAMIC_ROUTES" : PutResource.resources["DYNAMIC_ROUTES"].keys()
            }, 
            DELETE  = {
                "STATIC_ROUTES" : DeleteResource.resources["STATIC_ROUTES"].keys(),
                "DYNAMIC_ROUTES" : DeleteResource.resources["DYNAMIC_ROUTES"].keys()
            },
            OPTIONS = {
                "STATIC_ROUTES" : OptionsResource.resources["STATIC_ROUTES"].keys(),
                "DYNAMIC_ROUTES" : OptionsResource.resources["DYNAMIC_ROUTES"].keys()
            },
        ) 
        self.write(self.json_serializer.dumps(resources))
        self.finish()
        
    own_resources = {
        '/paths' : paths,
    }


              
class PostResource(BaseRequestHandler):
    
    async def post(self):      
        # log_request(self.request)
        if (await self.handled_through_remote_object(self.request)):           
            return  
        
        # elif self.request.path in self.own_resources:
        #     func = self.own_resources[self.request.path]
        #     body = self.decode_body(self.request.body)
        #     func(self, body)
        #     return

        self.set_status(404)
        self.add_header("Access-Control-Allow-Origin", self.client_address)
        self.finish()

    

class PutResource(BaseRequestHandler):
    
    async def put(self):      

        if (await self.handled_through_remote_object(self.request)):           
            return  

        self.set_status(404)
        self.add_header("Access-Control-Allow-Origin", self.client_address)
        self.finish()
 

class PatchResource(BaseRequestHandler):
    
    async def patch(self):      

        if (await self.handled_through_remote_object(self.request)):           
            return  

        self.set_status(404)
        self.add_header("Access-Control-Allow-Origin", self.client_address)
        self.finish()
 


class DeleteResource(BaseRequestHandler):
    
    async def delete(self):      

        if (await self.handled_through_remote_object(self.request)):           
            return  

        self.set_status(404)
        self.add_header("Access-Control-Allow-Origin", self.client_address)
        self.finish()



class OptionsResource(BaseRequestHandler):
    """
    this is wrong philosophically
    """

    async def options(self):        
        self.set_status(204)
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "*")
        self.set_header("Access-Control-Allow-Methods", 'GET, POST, PUT, DELETE, OPTIONS')
        self.finish()
