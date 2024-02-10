import subprocess
import asyncio
import traceback
import importlib
import typing 
import zmq
import threading
import time
from collections import deque

from .utils import unique_id, wrap_text
from .constants import *
from .remote_parameters import TypedDict
from .exceptions import *
from .decorators import post, get
from .remote_object import *
from .zmq_message_brokers import AsyncPollingZMQServer, ZMQServerPool, ServerTypes, AsyncZMQClient
from .remote_parameter import RemoteParameter
from ..param.parameters import Boolean, ClassSelector, TypedList, List as PlainList



class Consumer:
    consumer = ClassSelector(default=None, allow_None=True, class_=RemoteObject, isinstance=False)
    args = PlainList(default=None, allow_None=True, accept_tuple=True)
    kwargs = TypedDict(default=None, allow_None=True, key_type=str)
   
    def __init__(self, consumer : typing.Type[RemoteObject], args : typing.Tuple = tuple(), **kwargs) -> None:
        if consumer is not None:
            self.consumer = consumer
        else:
            raise ValueError("consumer cannot be None, please assign a subclass of RemoteObject")
        self.args = args 
        self.kwargs = kwargs



class EventLoop(RemoteObject):
    """
    The EventLoop class implements a infinite loop where zmq ROUTER sockets listen for messages. Each consumer of the 
    event loop (an instance of RemoteObject) listen on their own ROUTER socket and execute methods or allow read and write
    of attributes upon receiving instructions. Socket listening is implemented in an async (asyncio) fashion. 
    """
    server_type = ServerTypes.EVENTLOOP

    remote_objects = TypedList(item_type=(RemoteObject, Consumer), bounds=(0,100), allow_None=True, default=None,
                        doc="""list of RemoteObjects which are being executed""")
  
    # Remote Parameters
    uninstantiated_remote_objects = TypedDict(default=None, allow_None=True, key_type=str,
                        item_type=(Consumer, str)) #, URL_path = '/uninstantiated-remote-objects')

    def __new__(cls, **kwargs):
        obj = super().__new__(cls, **kwargs)
        obj._internal_fixed_attributes.append('_message_broker_pool')
        return obj

    def __init__(self, *, instance_name : str, 
                remote_objects : typing.Union[RemoteObject, Consumer, typing.List[typing.Union[RemoteObject, Consumer]]] = list(), # type: ignore - requires covariant types
                log_level : int = logging.INFO, **kwargs) -> None:
        super().__init__(instance_name=instance_name, remote_objects=remote_objects, log_level=log_level, **kwargs)
        self._message_broker_pool : ZMQServerPool = ZMQServerPool(instance_names=None, 
                    # create empty pool as message brokers are already created
                    proxy_serializer=self.proxy_serializer, json_serializer=self.json_serializer) 
        remote_objects : typing.List[RemoteObject] = [self]
        if self.remote_objects is not None:
            for consumer in self.remote_objects:
                if isinstance(consumer, RemoteObject):
                    remote_objects.append(consumer)
                    consumer.object_info.eventloop_name = self.instance_name
                    self._message_broker_pool.register_server(consumer.message_broker)
                elif isinstance(consumer, Consumer):
                    instance = consumer.consumer(*consumer.args, **consumer.kwargs, 
                                            eventloop_name = self.instance_name)
                    self._message_broker_pool.register_server(instance.message_broker)                            
                    remote_objects.append(instance) 
        self.remote_objects = remote_objects # re-assign the instantiated objects as well
        self.uninstantiated_remote_objects = {}
      
    def __post_init__(self):
        super().__post_init__()
        self.logger.info("Event loop with name '{}' can be started using EventLoop.run().".format(self.instance_name))   
        return 

    @property 
    def message_broker_pool(self):
        return self._message_broker_pool 
     
    @get('/remote-objects')
    def servers(self):
        return {
            instance.__class__.__name__ : instance.instance_name for instance in self.remote_objects 
        }
    
    # example of overloading
    @post('/exit')
    def exit(self):
        raise BreakAllLoops
    
    @classmethod
    def import_remote_object(cls, file_name : str, object_name : str):
        module_name = file_name.split('\\')[-1]
        spec = importlib.util.spec_from_file_location(module_name, file_name) # type: ignore
        if spec is not None:
            module = importlib.util.module_from_spec(spec) # type: ignore
            spec.loader.exec_module(module)
        else:     
            module = importlib.import_module(module_name, file_name.split('\\')[0])

        consumer = getattr(module, object_name) 
        if issubclass(consumer, RemoteObject):
            return consumer 
        else:
            raise ValueError(wrap_text(f"""object name {object_name} in {file_name} not a subclass of RemoteObject. 
                            Only subclasses are accepted (not even instances). Given object : {consumer}"""))

    @post('/remote-object/import')
    def _import_remote_object(self, file_name : str, object_name : str):
        consumer = self.import_remote_object(file_name, object_name) 
        id = unique_id()
        self.uninstantiated_remote_objects[id] = consumer
        return dict(
            id = id, 
            db_params = consumer.parameters.remote_objects_webgui_info(consumer.parameters.load_at_init_objects())
        )

    @post('/remote-object/instantiate')
    def instantiate(self, file_name : str, object_name : str, kwargs : typing.Dict = {}):
        consumer = self.import_remote_object(file_name, object_name)
        instance = consumer(**kwargs, eventloop_name = self.instance_name)
        self.register_new_consumer(instance)
        
    def register_new_consumer(self, instance : RemoteObject):
        zmq_server = AsyncPollingZMQServer(instance_name=instance.instance_name, server_type=ServerTypes.USER_REMOTE_OBJECT,
                    context=self.message_broker_pool.context, json_serializer=self.json_serializer, 
                    proxy_serializer=self.proxy_serializer)
        self.message_broker_pool.register_server(zmq_server)
        instance.message_broker = zmq_server
        self.remote_objects.append(instance)
        async_loop = asyncio.get_event_loop()
        async_loop.call_soon(lambda : asyncio.create_task(self.run_single_target(instance)))

    def run(self):
        self._message_listener = threading.Thread(target=self._run_external_message_listener)
        self._message_listener.start()
        self._remote_object_executor = threading.Thread(target=self._run_remote_object_executor)
        self._remote_object_executor.start()

    def _run_external_message_listener(self):
        async_loop = asyncio.get_event_loop()
        async_loop.run_until_complete(
            asyncio.gather())
        self.logger.info("exiting event loop {}".format(self.instance_name))
        async_loop.close()
    
    def _run_remote_object_executor(self):
        async_loop = asyncio.get_event_loop()
        async_loop.run_until_complete(
            asyncio.gather(
                *[self.run_single_target(instance) 
                    for instance in self.remote_objects] 
        ))
        self.logger.info("exiting event loop {}".format(self.instance_name))
        async_loop.close()

    @classmethod
    async def run_single_target(cls, instance : RemoteObject) -> None: 
        instance_name = instance.instance_name
        while True:
            instructions = await instance.message_broker.async_recv_instructions()
            for instruction in instructions:
                client, _, client_type, _, msg_id, instruction_str, arguments, context = instruction
                plain_reply = context.pop("plain_reply", False)
                fetch_execution_logs = context.pop("fetch_execution_logs", False)
                if not plain_reply and fetch_execution_logs:
                    list_handler = ListHandler([])
                    list_handler.setLevel(logging.DEBUG)
                    list_handler.setFormatter(instance.logger.handlers[0].formatter)
                    instance.logger.addHandler(list_handler)
                try:
                    instance.logger.debug("""client {} of client type {} issued instruction {} with message id {}. 
                                starting execution""".format(client, client_type, instruction_str, msg_id))
                    return_value = await cls.execute_once(instance_name, instance, instruction_str, arguments) #type: ignore 
                    if not plain_reply:
                        return_value = {
                            "responseStatusCode" : 200,
                            "returnValue" : return_value,
                            "state"       : {
                                instance_name : instance.state()
                            }
                        }
                        if fetch_execution_logs:
                            return_value["logs"] = list_handler.log_list
                    await instance.message_broker.async_send_reply(instruction, return_value)
                    # Also catches exception in sending messages like serialization error
                except (BreakInnerLoop, BreakAllLoops):
                    instance.logger.info("Remote object {} with instance name {} exiting event loop.".format(
                                                            instance.__class__.__name__, instance_name))
                    return_value = None
                    if not plain_reply:
                        return_value = { 
                            "responseStatusCode" : 200,
                            "returnValue" : None,
                            "state"       : { 
                                instance_name : instance.state() 
                            }
                        }
                        if fetch_execution_logs:
                            return_value["logs"] = list_handler.log_list    
                                       
                    await instance.message_broker.async_send_reply(instruction, return_value)
                    return
                except Exception as E:
                    instance.logger.error("RemoteObject {} with instance name {} produced error : {}.".format(
                                                            instance.__class__.__name__, instance_name, E))
                    return_value = {
                            "message" : str(E),
                            "type"    : repr(E).split('(', 1)[0],
                            "traceback" : traceback.format_exc().splitlines(),
                            "notes"   : E.__notes__ if hasattr(E, "__notes__") else None
                        }
                    if not plain_reply:    
                        return_value = {
                            "responseStatusCode" : 500,
                            "exception" : return_value, 
                            "state"     : { 
                                instance_name : instance.state()
                            }
                        }          
                        if fetch_execution_logs:
                            return_value["logs"] = list_handler.log_list      
                    await instance.message_broker.async_send_reply(instruction, return_value)
                if fetch_execution_logs:
                    instance.logger.removeHandler(list_handler)

    @classmethod
    async def execute_once(cls, instance_name : str, instance : RemoteObject, instruction_str : str, 
                           arguments : typing.Dict[str, typing.Any]) -> typing.Dict[str, typing.Any]:
        scadapy = instance.instance_resources[instruction_str] 
        if scadapy.iscallable:      
            if scadapy.state is None or (hasattr(instance, 'state_machine') and 
                            instance.state_machine.current_state in scadapy.state):
                # Note that because we actually find the resource within __prepare_instance__, its already bound
                # and we dont have to separately bind it. 
                func = scadapy.obj
                if not scadapy.http_request_as_argument:
                    arguments.pop('request', None) 
                if scadapy.iscoroutine:
                    return await func(**arguments)
                else:
                    return func(**arguments)
            else: 
                raise StateMachineError("RemoteObject '{}' is in '{}' state, however command can be executed only in '{}' state".format(
                        instance_name, instance.state(), scadapy.state))
        
        elif scadapy.isparameter:
            action = instruction_str.split('/')[-1]
            parameter : RemoteParameter = scadapy.obj
            owner_inst : RemoteSubobject = scadapy.bound_obj
            if action == WRITE: 
                if scadapy.state is None or (hasattr(instance, 'state_machine') and  
                                        instance.state_machine.current_state in scadapy.state):
                    parameter.__set__(owner_inst, arguments["value"])
                else: 
                    raise StateMachineError("RemoteObject {} is in `{}` state, however attribute can be written only in `{}` state".format(
                        instance_name, instance.state_machine.current_state, scadapy.state))
            return parameter.__get__(owner_inst, type(owner_inst))
        raise NotImplementedError("Unimplemented execution path for RemoteObject {} for instruction {}".format(instance_name, instruction_str))


def fork_empty_eventloop(instance_name : str, logfile : typing.Union[str, None] = None, python_command : str = 'python',
                        condaenv : typing.Union[str, None] = None, prefix_command : typing.Union[str, None] = None):
    command_str = '{}{}{}-c "from scadapy.server import EventLoop; E = EventLoop({}); E.run();"'.format(
        f'{prefix_command} ' if prefix_command is not None else '',
        f'call conda activate {condaenv} && ' if condaenv is not None else '',
        f'{python_command} ',
        f"instance_name = '{instance_name}', logfile = '{logfile}'"
    )
    print(f"command to invoke : {command_str}")
    subprocess.Popen(
        command_str, 
        shell = True
    )


# class ForkedEventLoop:

#     def __init__(self, instance_name : str, remote_objects : Union[RemoteObject, Consumer, List[Union[RemoteObject, Consumer]]], 
#                 log_level : int = logging.INFO, **kwargs):
#         self.subprocess = Process(target = forked_eventloop, kwargs = dict(
#                         instance_name = instance_name, 
#                         remote_objects = remote_objects, 
#                         log_level = log_level,
#                         **kwargs
#                     ))
    
#     def start(self):
#         self.Process.start()



__all__ = ['EventLoop', 'Consumer', 'fork_empty_eventloop']