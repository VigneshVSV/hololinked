import zmq
import zmq.asyncio
import sys 
import os
import warnings
import asyncio
import importlib
import typing 
import threading
import logging
import tracemalloc
from collections import deque
from uuid import uuid4


from ..param.parameterized import Undefined
from ..exceptions import *
from ..constants import ZMQ_TRANSPORTS
from ..utils import format_exception_as_json, get_current_async_loop, get_default_logger
from ..config import global_config
from ..protocols.zmq.message import EMPTY_BYTE, ERROR, REPLY, PreserializedData, RequestMessage, SerializableData
from ..protocols.zmq.brokers import AsyncZMQServer, BaseZMQServer, EventPublisher
from ..serializers import Serializers
from .thing import Thing, ThingMeta
from .property import Property
from .properties import Boolean, TypedDict
from .actions import BoundAction, action as remote_method
from .logger import ListHandler



if global_config.TRACE_MALLOC:
    tracemalloc.start()

def set_event_loop_policy():
    if sys.platform.lower().startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    if global_config.USE_UVLOOP:
        if sys.platform.lower() in ['linux', 'darwin', 'linux2']:
            import uvloop
            asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        else:
            warnings.warn("uvloop not supported for windows, using default windows selector loop.", RuntimeWarning)

set_event_loop_policy()



RemoteObject = Thing # reading convenience

class RPCServer(BaseZMQServer):
    """
    The EventLoop class implements a infinite loop where zmq ROUTER sockets listen for messages. Each consumer of the 
    event loop (an instance of Thing) listen on their own ROUTER socket and execute methods or allow read and write
    of attributes upon receiving instructions. Socket listening is implemented in an async (asyncio) fashion. 
  
    Top level ZMQ RPC server used by ``Thing`` and ``Eventloop``. 

    Parameters
    ----------
    id: str
        ``id`` of the server
    server_type: str
        server type metadata
    context: Optional, zmq.asyncio.Context
        ZeroMQ async Context object to use. All sockets except those created by event publisher share this context. 
        Automatically created when None is supplied.
    **kwargs:
        tcp_socket_address: str
            address of the TCP socket, if not given, a random port is chosen
    """
    
    expose = Boolean(default=True, remote=False,
                    doc="""set to False to use the object locally to avoid alloting network resources 
                        of your computer for this object""")

    things = TypedDict(key_type=(str,), item_type=(Thing,), bounds=(0,100), allow_None=True, default=None,
                    doc="list of Things which are being executed", remote=False) # type: typing.Dict[str, Thing]
    
    threaded = Boolean(default=False, remote=False, 
                    doc="set True to run each thing in its own thread")
  

    def __init__(self, *, 
                id: str, 
                things: typing.List[Thing],
                context: zmq.asyncio.Context | None = None, 
                transport: ZMQ_TRANSPORTS = ZMQ_TRANSPORTS.INPROC,
                **kwargs
            ) -> None:
        """
        Parameters
        ----------
        id: str
            instance name of the event loop
        things: List[Thing]
            things to be run/served
        log_level: int
            log level of the event loop logger
        """
        super().__init__(id=id, **kwargs)
        self.uninstantiated_things = dict()
        self.things = dict() 
        for thing in things:
            self.things[thing.id] = thing

        if self.logger is None:
            self.logger =  get_default_logger('{}|{}|{}|{}'.format(self.__class__.__name__, 
                                                'RPC', 'MIXED', self.id), kwargs.get('log_level', logging.INFO))
            kwargs['logger'] = self.logger
        # contexts and poller
        self._run = False # flag to stop all the
        self._terminate_context = context is None
        self.context = context or zmq.asyncio.Context()
        
       
        self.req_rep_server = AsyncZMQServer(
                                id=self.id, 
                                context=self.context, 
                                transport=transport, 
                                poll_timeout=1000,
                                **kwargs
                            )        
        self.event_publisher = EventPublisher(
                                id=f'{self.id}/event-publisher',
                                transport=transport,
                                **kwargs
                            )        
        
        self.schedulers = dict()
        self.schedulers_per_objekt = dict()
        
        # message serializing deque
        for instance in self.things.values():
            instance.rpc_server = self
            instance.event_publisher = self.event_publisher 
            # instance._prepare_resources()
     
    
    schedulers: typing.Dict[str, "Scheduler"]
    schedulers_per_objekt = typing.Dict[str, typing.Type["Scheduler"]]

    def __post_init__(self):
        super().__post_init__()
        self.logger.info("Server with name '{}' can be started using run().".format(self.id))   
        
        
    async def recv_and_dispatch_requests(self, server: AsyncZMQServer) -> None:
        """
        Continuously keeps receiving messages from different clients and appends them to a deque to be processed 
        sequentially. Also handles messages that dont need to be queued like HANDSHAKE, EXIT, invokation timeouts etc.
        """
        eventloop = asyncio.get_event_loop()

        while self._run:
            try:
                request_messages = await server.poll_requests() 
                # when stop poll is set, this will exit with an empty list
            except BreakLoop:
                break
            
            for request_message in request_messages:
                try:
                    # handle invokation timeout
                    invokation_timeout = request_message.server_execution_context.get("invokation_timeout", None)

                    ready_to_process_event = None
                    timeout_task = None
                    if invokation_timeout is not None:
                        ready_to_process_event = asyncio.Event()
                        timeout_task = asyncio.create_task(
                                                self.process_timeouts(
                                                    request_message=request_message, 
                                                    ready_to_process_event=ready_to_process_event, 
                                                    timeout=invokation_timeout, 
                                                    origin_server=server, 
                                                    timeout_type='invokation'
                                                )
                                            )
                        eventloop.call_soon(lambda : timeout_task)
                   
                    # check object level scheduling requirements and schedule the message
                    # append to messages list - message, event, timeout task, origin socket
                    operation = (request_message, ready_to_process_event, timeout_task, server)
                    if request_message.qualified_operation in self.schedulers_per_objekt:
                        scheduler = self.schedulers_per_objekt[request_message.qualified_operation](self.things[request_message.thing_id], self)
                        scheduler.dispatch_operation(operation)
                    else:
                        self.schedulers[request_message.thing_id].append(operation)
                
                    # scheduler = Scheduler(self.things[request_message.thing_id], self, mode='async', one_shot=True)
                    # scheduler.dispatch_operation(operation)
                    # self.schedulers[request_message.id] = scheduler
                except Exception as ex:
                    # handle invalid message
                    self.logger.error(f"exception occurred for message id '{request_message.id}' - {str(ex)}")
                    invalid_message_task = asyncio.create_task(
                                                    server._handle_invalid_message(
                                                        request_message=request_message,        
                                                        exception=ex
                                                    )
                                                )      
                    eventloop.call_soon(lambda: invalid_message_task)

        self.stop()
        self.logger.info(f"stopped polling for server '{server.id}' {server.socket_address.split(':')[0].upper()}")

    
    async def tunnel_message_to_things(self, scheduler: "Scheduler") -> None:
        """
        message tunneler between external sockets and interal inproc client
        """
        eventloop = get_current_async_loop()
        while self._run and scheduler._run:
            # wait for message first
            if len(scheduler.queue) == 0:
                await scheduler.wait_for_execution_queueing()
                # this means in next loop it wont be in this block as a message arrived  
                continue

            # retrieve from messages list - message, execution context, event, timeout task, origin socket
            request_message, ready_to_process_event, timeout_task, origin_server = scheduler.pop_queue_FIFO()
            server_execution_context = request_message.server_execution_context
            
            # handle invokation timeout
            invokation_timed_out = True 
            if ready_to_process_event is not None: 
                ready_to_process_event.set() # releases timeout task 
                invokation_timed_out = await timeout_task
            if ready_to_process_event is not None and invokation_timed_out:
                # drop call to thing, timeout message was already sent in process_timeouts()
                continue 
            
            # handle execution through thing
            scheduler.last_operation_request = scheduler.extract_operation_tuple_from_request(request_message)
                    
            # schedule an execution timeout
            execution_timeout = server_execution_context.get("execution_timeout", None)
            execution_completed_event = None 
            execution_timeout_task = None
            execution_timed_out = True
            if execution_timeout is not None:
                execution_completed_event = asyncio.Event()
                execution_timeout_task = asyncio.create_task(
                                                    self.process_timeouts(
                                                        request_message=request_message, 
                                                        ready_to_process_event=execution_completed_event,
                                                        timeout=execution_timeout,
                                                        origin_server=origin_server,
                                                        timeout_type='execution'
                                                    )
                                                )
                eventloop.call_soon(lambda : execution_timeout_task)

            # always wait for reply from thing, since this loop is asyncio task (& in its own thread in RPC server), 
            # timeouts always reach client without truly blocking by the GIL. If reply does not arrive, all other requests
            # get invokation timeout.            
            # await eventloop.run_in_executor(None, scheduler.wait_for_reply)
            await scheduler.wait_for_reply(eventloop)
            # check if reply is never undefined, Undefined is a sensible placeholder for NotImplemented singleton
            if scheduler.last_operation_reply is Undefined:
                # this is a logic error, as the reply should never be undefined
                await origin_server._handle_error_message(
                            request_message=request_message, 
                            exception=RuntimeError("No reply from thing - logic error")
                        )
                continue
            payload, preserialized_payload, reply_message_type = scheduler.last_operation_reply
            scheduler.reset_operation_reply()

            # check if execution completed within time
            if execution_completed_event is not None:
                execution_completed_event.set() # releases timeout task
                execution_timed_out = await execution_timeout_task
            if execution_timeout_task is not None and execution_timed_out:
                # drop reply to client as timeout was already sent
                continue
            if server_execution_context.get("oneway", False):
                # drop reply if oneway
                continue 

            # send reply to client            
            await origin_server.async_send_response_with_message_type(
                request_message=request_message,
                message_type=reply_message_type,
                payload=payload,
                preserialized_payload=preserialized_payload
            ) 

        scheduler.cleanup()
        self.logger.info("stopped tunneling messages to things")


    async def run_thing_instance(self, instance: Thing, scheduler: typing.Optional["Scheduler"] = None) -> None: 
        """
        run a Thing instance in an infinite loop by allowing the scheduler to schedule operations on it.

        Parameters
        ----------
        instance: Thing
            instance of the thing
        scheduler: Optional[Scheduler]
            scheduler that schedules operations on the thing instance, a default is always available. 
        """
        self.logger.info("starting to run operations on thing {} of class {}".format(instance.id, instance.__class__.__name__))
        if self.logger.level >= logging.ERROR:
            # sleep added to resolve some issue with logging related IO bound tasks in asyncio - not really clear what it is.
            # This loop crashes for log levels above ERROR without the following statement
            await asyncio.sleep(0.001) 
        scheduler = scheduler or self.schedulers[instance.id]
        eventloop = get_current_async_loop()
        
        while self._run and scheduler._run:
            # print("starting to serve thing {}".format(instance.id))
            await scheduler.wait_for_operation(eventloop)
            # await scheduler.wait_for_operation()
            if scheduler.last_operation_request is Undefined:
                instance.logger.warning("No operation request found in thing '{}'".format(instance.id))
                continue
           
            try:
                # fetch operation_request which is a tuple of 
                # (thing_id, objekt, operation, payload, preserialized_payload, execution_context)
                thing_id, objekt, operation, payload, preserialized_payload, execution_context = scheduler.last_operation_request 

                # deserializing the payload required to execute the operation
                payload = payload.deserialize() 
                preserialized_payload = preserialized_payload.value
                instance.logger.debug(f"thing {instance.id} with {thing_id} starting execution of operation {operation} on {objekt}")
                
                # start activities related to thing execution context
                fetch_execution_logs = execution_context.pop("fetch_execution_logs", False)
                if fetch_execution_logs:
                    list_handler = ListHandler([])
                    list_handler.setLevel(logging.DEBUG)
                    list_handler.setFormatter(instance.logger.handlers[0].formatter)
                    instance.logger.addHandler(list_handler)

                # execute the operation
                return_value = await self.execute_operation(instance, objekt, operation, payload, preserialized_payload) 

                # handle return value
                if isinstance(return_value, tuple) and len(return_value) == 2 and (
                    isinstance(return_value[1], bytes) or 
                    isinstance(return_value[1], PreserializedData) 
                ):  
                    if fetch_execution_logs:
                        return_value[0] = {
                            "return_value" : return_value[0],
                            "execution_logs" : list_handler.log_list
                        }
                    payload = SerializableData(return_value[0], Serializers.for_object(thing_id, instance.__class__.__name__, objekt))
                    if isinstance(return_value[1], bytes):
                        preserialized_payload = PreserializedData(return_value[1])
                # elif isinstance(return_value, PreserializedData):
                #     if fetch_execution_logs:
                #         return_value = {
                #             "return_value" : return_value.value,
                #             "execution_logs" : list_handler.log_list
                #         }
                #     payload = SerializableData(return_value.value, content_type='application/json')
                #     preserialized_payload = return_value

                elif isinstance(return_value, bytes):
                    payload = SerializableData(None, content_type='application/json')
                    preserialized_payload = PreserializedData(return_value)
                else:
                     # complete thing execution context
                    if fetch_execution_logs:
                        return_value = {
                            "return_value" : return_value,
                            "execution_logs" : list_handler.log_list
                        }
                    payload = SerializableData(return_value, Serializers.for_object(thing_id, instance.__class__.__name__, objekt))
                    preserialized_payload = PreserializedData(EMPTY_BYTE, content_type='text/plain')
                # set reply
                scheduler.last_operation_reply = (payload, preserialized_payload, REPLY)
            except BreakInnerLoop:
                # exit the loop and stop the thing
                instance.logger.info("Thing {} with instance name {} exiting event loop.".format(
                                                            instance.__class__.__name__, instance.id))
                return_value = None
                if fetch_execution_logs:
                    return_value = { 
                        "return_value" : None,
                        "execution_logs" : list_handler.log_list
                    }
                scheduler.last_operation_reply = (
                    SerializableData(return_value, content_type='application/json'), 
                    PreserializedData(EMPTY_BYTE, content_type='text/plain'),
                    None
                )
                return 
            except Exception as ex:
                # error occurred while executing the operation
                instance.logger.error("Thing {} with ID {} produced error : {} - {}.".format(
                                                        instance.__class__.__name__, instance.id, type(ex), ex))
                return_value = dict(exception=format_exception_as_json(ex))                
                if fetch_execution_logs:
                    return_value["execution_logs"] = list_handler.log_list
                scheduler.last_operation_reply = (
                    SerializableData(return_value, content_type='application/json'), 
                    PreserializedData(EMPTY_BYTE, content_type='text/plain'),
                    ERROR
                )
            finally:
                # cleanup
                if fetch_execution_logs:
                    instance.logger.removeHandler(list_handler)
                instance.logger.debug("thing {} with instance name {} completed execution of operation {} on {}".format(
                                                            instance.__class__.__name__, instance.id, operation, objekt))
        self.logger.info("stopped running thing {}".format(instance.id))


    @classmethod
    async def execute_operation(cls, 
                        instance: Thing, 
                        objekt: str, 
                        operation: str,
                        payload: typing.Any,
                        preserialized_payload: bytes
                    ) -> typing.Any:
        """
        Execute a given operation on a thing instance. 

        Parameters
        ----------
        instance: Thing
            instance of the thing
        objekt: str
            name of the property, action or event
        operation: str
            operation to be executed on the property, action or event
        payload: Any
            payload to be used for the operation 
        preserialized_payload: bytes
            preserialized payload to be used for the operation
        """
        if operation == 'readProperty':
            prop = instance.properties[objekt] # type: Property
            return getattr(instance, prop.name) 
        elif operation == 'writeProperty':
            prop = instance.properties[objekt] # type: Property
            if preserialized_payload != EMPTY_BYTE:
                prop_value = preserialized_payload
            else:
                prop_value = payload
            return prop.external_set(instance, prop_value)
        elif operation == 'deleteProperty':
            prop = instance.properties[objekt] # type: Property
            del prop # raises NotImplementedError when deletion is not implemented which is mostly the case
        elif operation == 'invokeAction':
            action = instance.actions[objekt] # type: BoundAction
            args = payload.pop('__args__', tuple())
            # payload then become kwargs
            if preserialized_payload != EMPTY_BYTE:
                args = (preserialized_payload,) + args
            if action.execution_info.iscoroutine:
                # the actual scheduling as a purely async task is done by the scheduler, not here, 
                # this will be a blocking call
                return await action.external_call(*args, **payload)
            return action.external_call(*args, **payload) 
        elif operation == 'readMultipleProperties' or operation == 'readAllProperties':
            if objekt is None:
                return instance._get_properties()
            return instance._get_properties(names=objekt)
        elif operation == 'writeMultipleProperties' or operation == 'writeAllProperties':
            return instance._set_properties(payload)
        raise NotImplementedError("Unimplemented execution path for Thing {} for operation {}".format(
                                                                            instance.id, operation))


    async def process_timeouts(self, 
                            request_message: RequestMessage, 
                            ready_to_process_event: asyncio.Event,
                            origin_server: AsyncZMQServer,
                            timeout: float | int | None, 
                            timeout_type : str
                        ) -> bool:
        """
        replies timeout to client if timeout occured and prevents the message from being executed. 
        """
        try:
            await asyncio.wait_for(ready_to_process_event.wait(), timeout)
            return False 
        except TimeoutError:    
            await origin_server._handle_timeout(request_message, timeout_type)
            return True


    def run_external_message_listener(self):
        """
        Runs ZMQ's sockets which are visible to clients.
        This method is automatically called by ``run()`` method. 
        Please dont call this method when the async loop is already running. 
        """
        self.logger.info("starting external message listener thread")
        self._run = True
        eventloop = get_current_async_loop()
        existing_tasks = asyncio.all_tasks(eventloop)
        eventloop.run_until_complete(
            asyncio.gather(
                self.recv_and_dispatch_requests(self.req_rep_server),
                *[self.tunnel_message_to_things(scheduler) for scheduler in self.schedulers.values()],
                *existing_tasks
            )
        )
        self.logger.info("exiting external listener event loop {}".format(self.id))
        eventloop.close()
    

    def run_things_executor(self, things: typing.List[Thing]):
        """
        Run ZMQ sockets which provide queued instructions to ``Thing``.
        This method is automatically called by ``run()`` method. 
        Please dont call this method when the async loop is already running. 
        """
        thing_executor_loop = get_current_async_loop()
        self.logger.info(f"starting thing executor loop in thread {threading.get_ident()} for {[obj.id for obj in things]}")
        thing_executor_loop.run_until_complete(
            asyncio.gather(*[self.run_thing_instance(instance) for instance in things])
        )
        self.logger.info(f"exiting event loop in thread {threading.get_ident()}")
        thing_executor_loop.close()


    def run(self):
        """
        start the eventloop
        """
        self.logger.info("starting server")
        for thing in self.things.values():
            self.schedulers[thing.id] = Scheduler(thing, self, mode='threaded', one_shot=False) 
        if not self.threaded:
            _thing_executor = threading.Thread(target=self.run_things_executor, args=(list(self.things.values()),))
            _thing_executor.start()
        else: 
            for thing in self.things.values():
                _thing_executor = threading.Thread(target=self.run_things_executor, args=([thing],))
                _thing_executor.start()
        self.run_external_message_listener()
        if not self.threaded:
            _thing_executor.join()       
        self.logger.info("server stopped")


    def stop(self):
        """
        stop polling method ``poll()``
        """
        self._run = False
        self.req_rep_server.stop_polling()
        for scheduler in self.schedulers.values():
            scheduler.cleanup()
        

    def exit(self):
        try:
            self.stop()
            if self.req_rep_server is not None:
                self.req_rep_server.exit()
            if self.event_publisher is not None:
                self.event_publisher.exit()
        except:
            pass 
        if self._terminate_context:
            self.context.term()
        self.logger.info("terminated context of socket '{}' of type '{}'".format(self.id, self.__class__))


   
    uninstantiated_things = TypedDict(default=None, allow_None=True, key_type=str,
                                            item_type=str)
    
    
    @classmethod
    def _import_thing(cls, file_name : str, object_name : str):
        """
        import a thing specified by ``object_name`` from its 
        script or module. 

        Parameters
        ----------
        file_name : str
            file or module path 
        object_name : str
            name of ``Thing`` class to be imported
        """
        module_name = file_name.split(os.sep)[-1]
        spec = importlib.util.spec_from_file_location(module_name, file_name)
        if spec is not None:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        else:     
            module = importlib.import_module(module_name, file_name.split(os.sep)[0])
        consumer = getattr(module, object_name) 
        if issubclass(consumer, Thing):
            return consumer 
        else:
            raise ValueError(f"object name {object_name} in {file_name} not a subclass of Thing.", 
                            f" Only subclasses are accepted (not even instances). Given object : {consumer}")
        

    @remote_method()
    def import_thing(self, file_name : str, object_name : str):
        """
        import thing from the specified path and return the default 
        properties to be supplied to instantiate the object. 
        """
        consumer = self._import_thing(file_name, object_name) # type: ThingMeta
        id = uuid4()
        self.uninstantiated_things[id] = consumer
        return id
           

    @remote_method() # remember to pass schema with mandatory instance name
    def instantiate(self, id : str, kwargs : typing.Dict = {}):      
        """
        Instantiate the thing that was imported with given arguments 
        and add to the event loop
        """
        consumer = self.uninstantiated_things[id]
        instance = consumer(**kwargs, eventloop_name=self.id) # type: Thing
        self.things.append(instance)
        rpc_server = instance.rpc_server
        self.request_listener_loop.call_soon(asyncio.create_task(lambda : rpc_server.poll()))
        self.request_listener_loop.call_soon(asyncio.create_task(lambda : rpc_server.tunnel_message_to_things()))
        if not self.threaded:
            self.thing_executor_loop.call_soon(asyncio.create_task(lambda : self.run_single_target(instance)))
        else: 
            _thing_executor = threading.Thread(target=self.run_things_executor, args=([instance],))
            _thing_executor.start()


class Scheduler:
    """
    Scheduler class to schedule the operations of a thing either in queued mode, or a one-shot mode in either 
    async or threaded loops. 
    """

    OperationRequest = typing.Tuple[str, str, str, SerializableData, PreserializedData, typing.Dict[str, typing.Any]]
    OperationReply = typing.Tuple[SerializableData, PreserializedData, str]

    def __init__(self, instance: Thing, rpc_server: RPCServer, mode: str = 'async', one_shot: bool = True) -> None:
        self.instance = instance # type: Thing
        self.rpc_server = rpc_server # type: RPCServer
        self.queue = deque() # type: typing.Deque[Scheduler.OperationRequest]
        self._run = True
        self._one_shot = False
        self._last_operation_request = Undefined
        self._last_operation_reply = Undefined
        self._message_queued_event = asyncio.Event()
        if mode == 'threaded':
            self._operation_execution_ready_event = threading.Event()
            self._operation_execution_complete_event = threading.Event()
        elif mode == 'async':
            self._operation_execution_ready_event = asyncio.Event()
            self._operation_execution_complete_event = asyncio.Event()
        else:
            raise ValueError("mode can only be 'threaded' or 'async'")
        self.mode = mode 

    def append(self, item: typing.Tuple[RequestMessage, asyncio.Event, asyncio.Task, AsyncZMQServer]) -> None:
        """
        append a request message to the queue after ticking the invokation timeout clock
        
        Parameters
        ----------
        item: Tuple[RequestMessage, asyncio.Event, asyncio.Task, AsyncZMQServer]
            tuple of request message, event to indicate if request message can be executed, invokation timeout task 
            and originating server of the request
        """
        self.queue.append(item)
        self._message_queued_event.set()

    async def wait_for_execution_queueing(self) -> None:
        await self._message_queued_event.wait()
        self._message_queued_event.clear()

    def pop_queue_FIFO(self) -> typing.Tuple[RequestMessage, asyncio.Event, asyncio.Task, AsyncZMQServer]:
        return self.queue.popleft()
    
    @property
    def last_operation_request(self) -> OperationRequest:
        return self._last_operation_request
    
    @last_operation_request.setter
    def last_operation_request(self, value: OperationRequest):
        self._last_operation_request = value
        self._operation_execution_ready_event.set()

    def reset_operation_request(self):
        self._last_operation_request = Undefined

    @property
    def last_operation_reply(self) -> OperationReply:
        return self._last_operation_reply
    
    @last_operation_reply.setter
    def last_operation_reply(self, value: OperationReply):
        self._last_operation_request = Undefined
        self._last_operation_reply = value
        self._operation_execution_complete_event.set()
        if self._one_shot:
            self._run = False

    def reset_operation_reply(self):
        self._last_operation_reply = Undefined

    async def wait_for_operation(self, eventloop: asyncio.AbstractEventLoop | None) -> None:
        # assert isinstance(self._operation_execution_ready_event, threading.Event), "not a threaded scheduler"
        if isinstance(self._operation_execution_ready_event, threading.Event):
            await eventloop.run_in_executor(None, self._operation_execution_ready_event.wait)
        else:
            await self._operation_execution_ready_event.wait()
        self._operation_execution_ready_event.clear()

    async def wait_for_reply(self, eventloop: asyncio.AbstractEventLoop | None) -> None:
        if isinstance(self._operation_execution_complete_event, threading.Event):
            await eventloop.run_in_executor(None, self._operation_execution_complete_event.wait)
        else:
            await self._operation_execution_complete_event.wait()
        self._operation_execution_complete_event.clear()

    def dispatch_operation(self, operation: OperationRequest) -> None:
        self.queue.append(operation)
        eventloop = get_current_async_loop()
        eventloop.call_soon(lambda: asyncio.create_task(self.rpc_server.tunnel_message_to_things(self)))
        if self.mode == 'async': 
            eventloop.call_soon(lambda: asyncio.create_task(self.rpc_server.run_thing_instance(self.instance, self)))
        else:
            threading.Thread(target=asyncio.run, args=(self.rpc_server.run_thing_instance(self.instance, self),)).start()

    def cleanup(self):
        self._run = False
        self._message_queued_event.set()
        self._operation_execution_ready_event.set()
        self._operation_execution_complete_event.set()
        self.queue.clear()
            
    @classmethod
    def extract_operation_tuple_from_request(self, request_message: RequestMessage) -> OperationRequest:
        """thing execution info"""
        return (request_message.header['thingID'], request_message.header['objekt'], request_message.header['operation'], 
            request_message.body[0], request_message.body[1], request_message.header['thingExecutionContext'])
    
    @classmethod
    def format_reply_tuple(self, return_value: typing.Any) -> OperationReply:
        pass
    


    
__all__ = [
    RPCServer.__name__
]




