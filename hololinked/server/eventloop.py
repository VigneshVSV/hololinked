import os
import subprocess
import asyncio
import traceback
import importlib
import typing 
import threading
from uuid import uuid4

from .constants import *
from .webserver_utils import format_exception_as_json
from .remote_parameters import TypedDict
from .decorators import remote_method
from .exceptions import *
from .remote_object import *
from .remote_object import RemoteObjectMeta
from .zmq_message_brokers import ServerTypes 
from .remote_parameter import RemoteParameter
from .remote_parameters import ClassSelector, TypedList, List



class Consumer:
    consumer = ClassSelector(default=None, allow_None=True, class_=RemoteObject, isinstance=False,
                            remote=False)
    args = List(default=None, allow_None=True, accept_tuple=True, remote=False)
    kwargs = TypedDict(default=None, allow_None=True, key_type=str, remote=False)
   
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
                        doc="list of RemoteObjects which are being executed", remote=False) #type: typing.List[RemoteObject]
  
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
        # self._message_broker_pool : ZMQServerPool = ZMQServerPool(instance_names=None, 
        #             # create empty pool as message brokers are already created
        #             proxy_serializer=self.proxy_serializer, json_serializer=self.json_serializer) 
        remote_objects : typing.List[RemoteObject] = [self]
        if self.remote_objects is not None:
            for consumer in self.remote_objects:
                if isinstance(consumer, RemoteObject):
                    remote_objects.append(consumer)
                    consumer.object_info.eventloop_name = self.instance_name
                    # self._message_broker_pool.register_server(consumer.message_broker)
                elif isinstance(consumer, Consumer):
                    instance = consumer.consumer(*consumer.args, **consumer.kwargs, 
                                            eventloop_name=self.instance_name)
                    # self._message_broker_pool.register_server(instance.message_broker)                            
                    remote_objects.append(instance) 
        self.remote_objects = remote_objects # re-assign the instantiated objects as well
        self.uninstantiated_remote_objects = dict()
      
    def __post_init__(self):
        super().__post_init__()
        self.logger.info("Event loop with name '{}' can be started using EventLoop.run().".format(self.instance_name))   
        return 

    # example of overloading
    @remote_method()
    def exit(self):
        """
        Stops the event loop and all its remote objects. Generally, this leads
        to exiting the program unless some code follows the ``run()`` method.  
        """
        raise BreakAllLoops
    

    @classmethod
    def _import_remote_object(cls, file_name : str, object_name : str):
        """
        import a remote object specified by ``object_name`` from its 
        script or module. 

        Parameters
        ----------
        file_name : str
            file or module path 
        object_name : str
            name of ``RemoteObject`` class to be imported
        """
        module_name = file_name.split(os.sep)[-1]
        spec = importlib.util.spec_from_file_location(module_name, file_name)
        if spec is not None:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        else:     
            module = importlib.import_module(module_name, file_name.split(os.sep)[0])
        consumer = getattr(module, object_name) 
        if issubclass(consumer, RemoteObject):
            return consumer 
        else:
            raise ValueError(f"object name {object_name} in {file_name} not a subclass of RemoteObject.", 
                            f" Only subclasses are accepted (not even instances). Given object : {consumer}")
        

    @remote_method(URL_path='/remote-objects', http_method=HTTP_METHODS.POST)
    def import_remote_object(self, file_name : str, object_name : str):
        """
        import remote object from the specified path and return the default 
        parameters to be supplied to instantiate the object. 
        """
        consumer = self._import_remote_object(file_name, object_name) # type: RemoteObjectMeta
        id = uuid4()
        self.uninstantiated_remote_objects[id] = consumer
        return dict(
            id=id, 
            db_params=consumer.parameters.webgui_info(consumer.parameters.db_init_objects)
        )
   

    @remote_method(URL_path='/remote-objects/instantiate', 
                http_method=HTTP_METHODS.POST) # remember to pass schema with mandatory instance name
    def instantiate(self, id : str, kwargs : typing.Dict = {}):      
        """
        Instantiate the remote object that was imported with given arguments 
        and add to the event loop
        """
        consumer = self.uninstantiated_remote_objects[id]
        instance = consumer(**kwargs, eventloop_name=self.instance_name) # type: RemoteObject
        self.remote_objects.append(instance)
        rpc_server = instance._rpc_server
        self.request_listener_loop.call_soon(asyncio.create_task(lambda : rpc_server.poll()))
        self.request_listener_loop.call_soon(asyncio.create_task(lambda : rpc_server.tunnel_message_to_remote_objects()))
        self.remote_object_executor_loop.call_soon(asyncio.create_task(lambda : self.run_single_target(instance)))
     

    def run(self):
        """
        start the eventloop
        """
        self._remote_object_executor = threading.Thread(target=self.run_remote_object_executor)
        self._remote_object_executor.start()
        self.run_external_message_listener()
        self._remote_object_executor.join()


    @classmethod
    def get_async_loop(cls):
        """
        get or create an asnyc loop
        """
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop
        

    def run_external_message_listener(self):
        """
        Runs ZMQ's sockets which are visible to clients.
        This method is automatically called by ``run()`` method. 
        Please dont call this method when the async loop is already running. 
        """
        self.request_listener_loop = self.get_async_loop()
        rpc_servers = [remote_object._rpc_server for remote_object in self.remote_objects]
        methods = [] #type: typing.List[asyncio.Future]
        for rpc_server in rpc_servers:
            methods.append(rpc_server.poll())
            methods.append(rpc_server.tunnel_message_to_remote_objects())
        self.logger.info("starting external message listener thread")
        self.request_listener_loop.run_until_complete(asyncio.gather(*methods))
        self.logger.info("exiting external listener event loop {}".format(self.instance_name))
        self.request_listener_loop.close()
    

    def run_remote_object_executor(self):
        """
        Run ZMQ sockets which provide queued instructions to ``RemoteObject``.
        This method is automatically called by ``run()`` method. 
        Please dont call this method when the async loop is already running. 
        """
        self.remote_object_executor_loop = self.get_async_loop()
        self.logger.info("starting remote object executor thread")
        self.remote_object_executor_loop.run_until_complete(
            asyncio.gather(
                *[self.run_single_target(instance) 
                    for instance in self.remote_objects] 
        ))
        self.logger.info("exiting event loop {}".format(self.instance_name))
        self.remote_object_executor_loop.close()


    @classmethod
    async def run_single_target(cls, instance : RemoteObject) -> None: 
        instance_name = instance.instance_name
        while True:
            instructions = await instance.message_broker.async_recv_instructions()
            for instruction in instructions:
                client, _, client_type, _, msg_id, _, instruction_str, arguments, context = instruction
                plain_reply = context.pop("plain_reply", False)
                fetch_execution_logs = context.pop("fetch_execution_logs", False)
                if not plain_reply and fetch_execution_logs:
                    list_handler = ListHandler([])
                    list_handler.setLevel(logging.DEBUG)
                    list_handler.setFormatter(instance.logger.handlers[0].formatter)
                    instance.logger.addHandler(list_handler)
                try:
                    instance.logger.debug("client {} of client type {} issued instruction {} with message id {}. \
                                starting execution".format(client, client_type, instruction_str, msg_id))
                    return_value = await cls.execute_once(instance_name, instance, instruction_str, arguments) #type: ignore 
                    if not plain_reply:
                        return_value = {
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
                            "returnValue" : None,
                            "state"       : { 
                                instance_name : instance.state() 
                            }
                        }
                        if fetch_execution_logs:
                            return_value["logs"] = list_handler.log_list    
                                       
                    await instance.message_broker.async_send_reply(instruction, return_value)
                except Exception as ex:
                    instance.logger.error("RemoteObject {} with instance name {} produced error : {}.".format(
                                                            instance.__class__.__name__, instance_name, ex))
                    if not plain_reply:    
                        return_value = {
                            "exception" : format_exception_as_json(ex), 
                            "state"     : { 
                                instance_name : instance.state()
                            }
                        }          
                        if fetch_execution_logs:
                            return_value["logs"] = list_handler.log_list      
                    await instance.message_broker.async_send_reply_with_message_type(instruction, 
                                                                    b'EXCEPTION', return_value)
                if not plain_reply and fetch_execution_logs:
                    instance.logger.removeHandler(list_handler)

    @classmethod
    async def execute_once(cls, instance_name : str, instance : RemoteObject, instruction_str : str, 
                           arguments : typing.Dict[str, typing.Any]) -> typing.Dict[str, typing.Any]:
        resource = instance.instance_resources[instruction_str] 
        if resource.iscallable:      
            if resource.state is None or (hasattr(instance, 'state_machine') and 
                            instance.state_machine.current_state in resource.state):
                # Note that because we actually find the resource within __prepare_instance__, its already bound
                # and we dont have to separately bind it. 
                func = resource.obj
                args = arguments.pop('__args__', tuple())
                if resource.iscoroutine:
                    return await func(*args, **arguments)
                else:
                    return func(*args, **arguments)
            else: 
                raise StateMachineError("RemoteObject '{}' is in '{}' state, however command can be executed only in '{}' state".format(
                        instance_name, instance.state(), resource.state))
        
        elif resource.isparameter:
            action = instruction_str.split('/')[-1]
            parameter = resource.obj # type: RemoteParameter
            owner_inst = resource.bound_obj # type: RemoteObject
            if action == ResourceOperations.PARAMETER_WRITE: 
                if resource.state is None or (hasattr(instance, 'state_machine') and  
                                        instance.state_machine.current_state in resource.state):
                    return parameter.__set__(owner_inst, arguments["value"])
                else: 
                    raise StateMachineError("RemoteObject {} is in `{}` state, however attribute can be written only in `{}` state".format(
                        instance_name, instance.state_machine.current_state, resource.state))
            elif action == ResourceOperations.PARAMETER_READ:
                return parameter.__get__(owner_inst, type(owner_inst))             
        raise NotImplementedError("Unimplemented execution path for RemoteObject {} for instruction {}".format(instance_name, instruction_str))


def fork_empty_eventloop(instance_name : str, logfile : typing.Union[str, None] = None, python_command : str = 'python',
                        condaenv : typing.Union[str, None] = None, prefix_command : typing.Union[str, None] = None):
    command_str = '{}{}{}-c "from hololinked.server import EventLoop; E = EventLoop({}); E.run();"'.format(
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