import os
import zmq
import zmq.asyncio
import asyncio
import logging
import typing
from collections import deque
from enum import Enum
from typing import Union, List, Any, Dict, Sequence, Iterator, Set


from .utils import (current_datetime_ms_str, create_default_logger, run_coro_somehow, run_coro_sync, wrap_text,
        raise_local_exception)
from .config import global_config
from .constants import ZMQ_PROTOCOLS
from .serializers import (JSONSerializer, PickleSerializer, BaseSerializer, SerpentSerializer, # DillSerializer, 
                          serializers)
from ..param.parameterized import Parameterized



HANDSHAKE   = b'HANDSHAKE'
INSTRUCTION = b'INSTRUCTION'
REPLY       = b'REPLY'
INVALID_MESSAGE = b'INVALID_MESSAGE'
EVENT       = b'EVENT'
EVENT_SUBSCRIPTION = b'EVENT_SUBSCRIPTION'
SUCCESS     = b'SUCCESS'
FAILURE     = b'FAILURE'
EMPTY_BYTE  = b''
EMPTY_DICT  = {}

HTTP_SERVER = b'HTTP_SERVER'
PROXY       = b'PROXY'



class ServerTypes(Enum):
    UNKNOWN_TYPE = b'UNKNOWN_TYPE'
    EVENTLOOP = b'EVENTLOOP'
    REMOTE_OBJECT = b'REMOTE_OBJECT'
    POOL = b'POOL'
       


class BaseZMQ: 
    """
    Base class for all ZMQ message brokers. `hololinked` uses ZMQ under the hood to implement a
    RPC server. All requests, either coming through a HTTP Server or an RPC client are routed via the RPC
    Server to queue them before execution. See documentation of `RPCServer` for details. 

    This class implements `create_socket()` method & logger which is common to all server and client implementations.
    """
    def __init__(self) -> None:
        # only type definition for logger
        self.logger : logging.Logger
        
    def exit(self) -> None:
        """
        Cleanup method to terminate ZMQ sockets and contexts before quitting. Called by `__del__()`
        automatically. Each subclass server/client should implement their version of exiting if necessary.
        """
        raise NotImplementedError("implement exit() to gracefully exit ZMQ in {}.".format(self.__class__))

    def __del__(self) -> None:
        self.exit()

    def create_socket(self, context : Union[zmq.asyncio.Context, zmq.Context], instance_name : str, identity : str, 
                    bind : bool = False, protocol : ZMQ_PROTOCOLS = ZMQ_PROTOCOLS.IPC, socket_type : zmq.SocketType = zmq.ROUTER, 
                    socket_address : Union[str, None] = None) -> None:
        """
        Create a socket with certain specifications

        Parameters
        ----------
        context: zmq.Context or zmq.asyncio.Context
            ZeroMQ Context object that creates the socket
        instance_name: str
            ``instance_name`` of the ``RemoteObject``. For servers, this serves as a name for the created
            ROUTER socket. For clients, for IPC or INPROC, this allows to connect to the socket with the correct name. 
            must be unique. 
        identity: str
            especially useful for clients to have a different name than the ``instance_name`` of the ``RemoteObject``.
            For servers, supply the ``instance_name`` is sufficient.
        bind: bool
            whether to bind (server) or connect (client)
        protocol: Enum
            TCP, IPC or INPROC. Message crafting/passing/routing is protocol invariant as suggested by ZeroMQ docs.
        socket_type: zmq.SocketType, default zmq.ROUTER
            Usually a ROUTER socket is implemented for both client-server and peer-to-peer communication
        socket_address: str
            applicable only for TCP socket to find the correct socket to connect. 

        Returns
        -------
        None 
        """
        self.context = context
        self.identity = identity
        self.socket = self.context.socket(socket_type)
        self.socket.setsockopt_string(zmq.IDENTITY, identity)
        if protocol == ZMQ_PROTOCOLS.IPC or protocol == "IPC":
            split_instance_name = instance_name.split('/')
            socket_dir = os.sep  + os.sep.join(split_instance_name[:-1]) if len(split_instance_name) > 1 else ''
            directory = global_config.TEMP_DIR + socket_dir
            if not os.path.exists(directory):
                os.makedirs(directory)
            # re-compute for IPC
            socket_address = "ipc://{}{}{}.ipc".format(directory, os.sep, split_instance_name[-1])
            if bind:
                self.socket.bind(socket_address)
            else:
                self.socket.connect(socket_address)
        elif protocol == ZMQ_PROTOCOLS.TCP or protocol == "TCP":
            if bind:
                for i in range(global_config.TCP_SOCKET_SEARCH_START_PORT, global_config.TCP_SOCKET_SEARCH_END_PORT):
                    socket_address = "tcp://*:{}".format(i)
                    try:
                        self.socket.bind(socket_address)
                        break 
                    except zmq.error.ZMQError as ex:
                        if not ex.strerror.startswith('Address in use'):
                            raise ex from None
            elif socket_address:
                self.socket.connect(socket_address)
            else:
                raise RuntimeError(f"Socket must be either bound or connected. No operation is being carried out for this socket {identity}")
        elif protocol == ZMQ_PROTOCOLS.INPROC or protocol == "INPROC":
            inproc_instance_name = instance_name.replace('/', '_').replace('-', '_')
            socket_address = f'inproc://{inproc_instance_name}'
            if bind:
                self.socket.bind(socket_address)
            else:
                self.socket.connect(socket_address)
        else:
            raise NotImplementedError("protocols other than IPC, TCP & INPROC are not implemented now for {}".format(self.__class__))
        self.logger = self.get_logger(self.identity, socket_address, class_ = self.__class__.__name__) # type: ignore
        self.logger.info("created socket with address {} and {}".format(socket_address, "bound" if bind else "connected"))

    @classmethod
    def get_logger(cls, identity : str, socket_address : str, level = logging.DEBUG, class_ = 'BaseZMQ') -> logging.Logger:
        if socket_address.endswith('ipc'):
            socket_address = socket_address.split('\\')[-1]
            socket_address.strip('.ipc')
        class_ = class_.split('.')[-1]
        name = '{}|{}|{}'.format(class_, identity, socket_address) 
        return create_default_logger(name, level)


class BaseAsyncZMQ(BaseZMQ):
    """
    Creates, binds/connects am async router socket with either TCP or ICP protocol. A context is create if none is supplied. 
    For IPC sockets, a file is created under TEMP_DIR of global configuration.
    """

    def create_socket(self, instance_name : str, context : Union[zmq.asyncio.Context, None], *, identity : str, bind : bool = False, 
                    protocol : str = "IPC", socket_type : zmq.SocketType = zmq.ROUTER, socket_address : Union[str, None] = None) -> None:
        context = context or zmq.asyncio.Context()
        super().create_socket(context, instance_name, identity, bind, protocol, socket_type, socket_address)
        

class BaseSyncZMQ(BaseZMQ):

    def create_socket(self, instance_name : str, context : Union[zmq.Context, None], *, identity : str, bind : bool = False, 
                    protocol : str = "IPC", socket_type : zmq.SocketType = zmq.ROUTER, socket_address : Union[str, None] = None) -> None:
        context = context or zmq.Context()
        super().create_socket(context, instance_name, identity, bind, protocol, socket_type, socket_address)


class BaseZMQServer(BaseZMQ):
    """
    This class implements serializer instantiation and message handling for ZMQ servers and can be subclassed by all 
    server instances irrespective of sync or async. The messaging contract does not depend on sync or async implementation. 
    For HTTP clients, json_serializer is necessary and for other types of clients, any of the allowed serializer is possible. 
    """

    def __init__(self, server_type : Enum, json_serializer : Union[None, JSONSerializer] = None, 
                rpc_serializer : Union[str, BaseSerializer, None] = None) -> None:
        if json_serializer is None or isinstance(json_serializer, JSONSerializer):
            self.json_serializer = json_serializer or JSONSerializer()
        else:
            raise ValueError("invalid JSON serializer option for {}. Given option : {}".format(self.__class__, json_serializer))
        if isinstance(rpc_serializer, (PickleSerializer, SerpentSerializer, JSONSerializer)): # ,  DillSerializer)): 
            self.rpc_serializer = rpc_serializer 
        elif isinstance(rpc_serializer, str) or rpc_serializer is None: 
            self.rpc_serializer = serializers.get(rpc_serializer, SerpentSerializer)()
        else:
            raise ValueError("invalid proxy serializer option for {}. Given option : {}".format(self.__class__, rpc_serializer))
        self.server_type : Enum = server_type
        super().__init__()

    def parse_client_message(self, message : List[bytes]) -> Any:
        """
        client's message to server looks as follows:
        [address, bytes(), client type, message type, msg id, instruction, arguments, execution_context]
        [ 0     ,   1    ,     2      ,      3      ,   4   ,   5        ,  6       ,  7  ]
        """
        try:
            message_type = message[3]
            if message_type == INSTRUCTION:
                client_type = message[2]
                if client_type == PROXY:
                    message[5] = self.rpc_serializer.loads(message[5]) # type: ignore
                    message[6] = self.rpc_serializer.loads(message[6]) # type: ignore
                    message[7] = self.rpc_serializer.loads(message[7]) # type: ignore
                elif client_type == HTTP_SERVER:
                    message[5] = self.json_serializer.loads(message[5]) # type: ignore
                    message[6] = self.json_serializer.loads(message[6]) # type: ignore
                    message[7] = self.json_serializer.loads(message[7]) # type: ignore
                return message 
            elif message_type == HANDSHAKE:
                self.handshake(message[0])
        except Exception as E:
            self.handle_invalid_message(message, E)
    
    def craft_reply_from_arguments(self, address : bytes, message_type : bytes, message_id : bytes = b'', 
                                 data : Any = None) -> List[bytes]:
        return [
            address,
            bytes(),
            self.server_type.value,
            message_type,
            message_id,
            self.json_serializer.dumps(data)
        ] 
           
    def craft_reply_from_client_message(self, original_client_message : List[bytes], data : Any = None, **overrides) -> List[bytes]:
        """
        client's message to server looks as follows:
        [address, bytes(), client type, message type, msg id, instruction, arguments, execution_context]
        [ 0     ,   1    ,     2      ,      3      ,   4   ,   5        ,  6       ,  7  ]
        """
        client_type = original_client_message[2]
        if client_type == HTTP_SERVER:
            data = self.json_serializer.dumps(data)
        elif client_type == PROXY:
            data = self.rpc_serializer.dumps(data)
        else:
            raise ValueError("invalid client type given '{}' for preparing message to send from '{}' of type {}".format(
                                                                        client_type, self.identity, self.__class__))
        reply = [
                original_client_message[0],
                bytes(),
                self.server_type.value,
                REPLY,
                original_client_message[4],
                data
            ]
        if len(overrides) == 0:
            return reply 
        for key, value in overrides.items():
            if key == 'message_type':
                reply[3] = value 
        return reply  

    def handshake(self, address : bytes) -> None:
        run_coro_somehow(self._handshake(address))

    def handle_invalid_message(self, message : List[bytes], exception : Exception) -> None:
        run_coro_somehow(self._handle_invalid_message(message, exception))

    async def _handshake(self, address : bytes) -> None:
        raise NotImplementedError("handshake cannot be completed - implement _handshake in {} to complete handshake.".format(self.__class__))
    
    async def _handle_invalid_message(self, message : List[bytes], exception : Exception) -> None:
        raise NotImplementedError(
            wrap_text("invalid message cannot be handled - implement _handle_invalid_message in {} to handle invalid messages.".format(
            self.__class__)))


       
class AsyncZMQServer(BaseZMQServer, BaseAsyncZMQ):
    """
    ZMQ Server to be used by remote objects, this server will handle handshakes, event subscription notifications, 
    & instructions. 

    message from client to server :

    [address, bytes(), client type, message type, msg id, instruction, arguments]
    [ 0     ,   1    ,     2      ,      3      ,   4   ,    5       ,     6    ]

    Handshake - [client address, bytes, client_type, HANDSHAKE]
    """

    def __init__(self, instance_name : str, server_type : Enum, context : Union[zmq.asyncio.Context, None] = None, 
                protocol : ZMQ_PROTOCOLS = ZMQ_PROTOCOLS.IPC, socket_type : zmq.SocketType = zmq.ROUTER, **kwargs) -> None:
        BaseZMQServer.__init__(self, server_type, json_serializer=kwargs.get('json_serializer', None), 
                               rpc_serializer=kwargs.get('rpc_serializer', None))
        BaseAsyncZMQ.__init__(self)
        self.instance_name = instance_name
        self.create_socket(instance_name, context, identity=instance_name, bind=True, protocol=protocol, socket_type=socket_type,
                        socket_address=kwargs.get("socket_address", None)) 
        self._terminate_context = context == None # terminate if it was created by instance

    async def _handshake(self, address : bytes) -> None:
        await self.socket.send_multipart(self.craft_reply_from_arguments(address, HANDSHAKE))
        self.logger.info("sent handshake to client '{}'".format(address))
            
    async def _handle_invalid_message(self, original_client_message : List[bytes], exception : Exception) -> None:
        await self.socket.send_multipart(self.craft_reply_from_client_message(original_client_message, exception, 
                                                            message_type=INVALID_MESSAGE))
        self.logger.info("sent exception message to client '{}' : '{}'".format(original_client_message[0], str(exception)))
            
    async def async_recv_instruction(self) -> Any:
        while True:
            instruction = self.parse_client_message(await self.socket.recv_multipart())
            if instruction:
                self.logger.debug("received instruction from client '{}' with msg-ID '{}'".format(instruction[0], 
                                                                                                instruction[4]))
                return instruction
        
    async def async_recv_instructions(self, strip_delimiter = False) -> List[Any]:
        instructions = [await self.async_recv_instruction()]
        while True:
            try:
                instruction = self.parse_client_message(await self.socket.recv_multipart(zmq.NOBLOCK))
                if instruction:
                    self.logger.debug("received instruction from client '{}' with msg-ID '{}'".format(instruction[0], 
                                                                                                instruction[4]))
                    instructions.append(instruction)
            except zmq.Again: 
                break 
        return instructions
    
    async def async_send_reply(self, original_client_message : List[bytes], data : Any) -> None:
        reply = self.craft_reply_from_client_message(original_client_message, data)
        await self.socket.send_multipart(reply)
        self.logger.debug("sent reply to client '{}' with msg-ID '{}'".format(reply[0], reply[4]))
                
    async def async_send_event_subscription(self, consumer : str) -> None:
        await self.socket.send_multipart([consumer, bytes(), EVENT_SUBSCRIPTION])

    def exit(self) -> None:
        try:
            self.socket.close(0)
            self.logger.info("terminated socket of server '{}' of type '{}'".format(self.identity, self.__class__))
        except Exception as E:
            self.logger.warn("could not properly terminate socket or attempted to terminate an already terminated socket '{}'of type '{}'. Exception message : {}".format(
                self.identity, self.__class__, str(E)))
        try:
            if self._terminate_context:
                self.context.term()
                self.logger.info("terminated context of socket '{}' of type '{}'".format(self.identity, self.__class__))
        except Exception as E:
            self.logger.warn("could not properly terminate context or attempted to terminate an already terminated context '{}'. Exception message : {}".format(
                self.identity, str(E)))

    

class AsyncPollingZMQServer(AsyncZMQServer):
    """
    Identical to AsyncZMQServer, except that it can be stopped from server side.
    This is achieved by polling the socket instead of waiting indefinitely on the socket. 
    """

    def __init__(self, instance_name : str, *, server_type : Enum, context : Union[zmq.asyncio.Context, None] = None, 
                socket_type : zmq.SocketType = zmq.ROUTER, protocol : ZMQ_PROTOCOLS = ZMQ_PROTOCOLS.IPC, 
                poll_timeout = 25, **kwargs) -> None:
        super().__init__(instance_name, server_type, context, socket_type, protocol=protocol, **kwargs)
        self.poller = zmq.asyncio.Poller()
        self._instructions = []
        self.poller.register(self.socket, zmq.POLLIN)
        self.poll_timeout = poll_timeout

    @property
    def poll_timeout(self) -> int:
        return self._poll_timeout

    @poll_timeout.setter
    def poll_timeout(self, value) -> None:
        if not isinstance(value, int) or value < 0:
            raise ValueError("polling period must be an integer greater than 0, not {}. Value is considered in milliseconds.".format(value))
        self._poll_timeout = value 

    async def poll_instructions(self) -> List[List[bytes]]:
        self.stop_poll = False
        instructions = []
        while not self.stop_poll:
            sockets = await self.poller.poll(self.poll_timeout) # type hints dont work in this line
            for socket, _ in sockets:
                while True:
                    try:
                        instruction = self.parse_client_message(await socket.recv_multipart(zmq.NOBLOCK))
                    except zmq.Again:
                        break
                    else:
                        if instruction:
                            self.logger.debug("received instruction from client '{}' with msg-ID '{}'".format(instruction[0], 
                                                                                                                instruction[4]))
                            instructions.append(instruction)
        return instructions

    def stop_polling(self) -> None:
        self.stop_poll = True 

    def exit(self) -> None:
        self.poller.unregister(self.socket)
        return super().exit()
        


class ZMQServerPool(BaseZMQServer):
    """
    Implements pool of sockets
    """

    def __init__(self, instance_names : Union[List[str], None] = None, **kwargs) -> None:
        self.context = zmq.asyncio.Context()
        self.pool : Dict[str, Union[AsyncZMQServer, AsyncPollingZMQServer]] = dict() 
        self.poller = zmq.asyncio.Poller()
        if instance_names:
            for instance_name in instance_names:
                self.pool[instance_name] = AsyncZMQServer(instance_name, ServerTypes.UNKNOWN_TYPE, self.context, 
                                                        **kwargs)
            for server in self.pool.values():
                self.poller.register(server.socket, zmq.POLLIN)
        super().__init__(server_type = ServerTypes.POOL, json_serializer = kwargs.get('json_serializer'), 
                    rpc_serializer = kwargs.get('rpc_serializer', None))

    def register_server(self, server : Union[AsyncZMQServer, AsyncPollingZMQServer]) -> None:
        self.pool[server.instance_name] = server 
        self.poller.register(server.socket, zmq.POLLIN)

    def deregister_server(self, server : Union[AsyncZMQServer, AsyncPollingZMQServer]) -> None:
        self.poller.unregister(server.socket)
        self.pool.pop(server.instance_name)

    @property
    def poll_timeout(self) -> int:
        return self._poll_timeout

    @poll_timeout.setter
    def poll_timeout(self, value) -> None:
        if not isinstance(value, int) or value < 0:
            raise ValueError("polling period must be an integer greater than 0, not {}. Value is considered in milliseconds.".format(value))
        self._poll_timeout = value 

    async def async_recv_instruction(self, instance_name : str) -> Any:
        return await self.pool[instance_name].async_recv_instruction()
     
    async def async_recv_instructions(self, instance_name : str) -> Any:
        return await self.pool[instance_name].async_recv_instructions()
   
    async def async_send_reply(self, instance_name : str, original_client_message : List[bytes],  data : Any) -> None:
        await self.pool[instance_name].async_send_reply(original_client_message, data)
    
    async def poll(self, strip_delimiter : bool = False) -> List[Any]:
        self.stop_poll = False
        instructions = []
        while not self.stop_poll:
            sockets = await self.poller.poll(self.poll_timeout) 
            for socket, _ in sockets:
                while True:
                    try:
                        instruction = self.parse_client_message(await socket.recv_multipart(zmq.NOBLOCK))
                    except zmq.Again:
                        break
                    else:
                        if instruction:
                            instructions.append(instruction)
        return instructions
        
    def stop_polling(self) -> None:
        self.stop_poll = True 
    
    def exit(self) -> None:
        for server in self.pool.values():
            self.poller.unregister(server.socket)
            server.exit()
        try:
            self.context.term()
            self.logger.info("context terminated for {}".format(self.__class__))
        except Exception as E:
            self.logger.warn("could not properly terminate context or attempted to terminate an already terminated context '{}'. Exception message : {}".format(
                self.identity, str(E)))

    def __getitem__(self, key) -> Union[AsyncZMQServer, AsyncPollingZMQServer]:
        return self.pool[key]
    
    def __iter__(self) -> Iterator[str]:
        return self.pool.__iter__()
    
    def __contains__(self, name : str) -> bool:
        return name in self.pool.keys()
    


class RPCServer:

    def __init__(self, instance_name : str, *, server_type : Enum, context : Union[zmq.asyncio.Context, None] = None, 
                protocols : typing.List[ZMQ_PROTOCOLS] = ZMQ_PROTOCOLS.IPC, poll_timeout = 25, **kwargs) -> None:
        context = zmq.asyncio.Context()
        if ZMQ_PROTOCOLS.TCP in protocols:
            self.tcp_server = AsyncPollingZMQServer(instance_name=instance_name, context=context, 
                                    protocol=ZMQ_PROTOCOLS.TCP, **kwargs)
        if ZMQ_PROTOCOLS.IPC in protocols: 
            self.ipc_server = AsyncPollingZMQServer(instance_name=instance_name, context=context, 
                                    protocol=ZMQ_PROTOCOLS.IPC, **kwargs)
        if ZMQ_PROTOCOLS.INPROC in protocols: 
            self.inproc_server = AsyncPollingZMQServer(instance_name=instance_name, context=context, 
                                    protocol=ZMQ_PROTOCOLS.INPROC, **kwargs)
        self.inproc_client = AsyncZMQClient(server_instance_name=instance_name, identity='', client_type='', 
                                context=context, protocol=ZMQ_PROTOCOLS.INPROC)
        self._instructions = deque() # type: typing.Iterable[typing.Tuple[typing.Any, asyncio.Event, asyncio.Future]]
        self._replies = deque()
        self.poll_timeout = poll_timeout
        self.poller = zmq.Poller()
        self.poller.register(self.ipc_server)
        self.poller.register(self.tcp_server)
        self.poller.register(self.inproc_server)
        self._socket_to_server_map = {
            self.tcp_server.socket : self.tcp_server,
            self.ipc_server.socket : self.ipc_server,
            self.inproc_server.socket : self.inproc_server
        }

    def prepare(self):
        """
        registers socket polling method and message tunnelling methods to the running 
        asyncio event loop
        """
        eventloop = asyncio.get_running_loop()
        eventloop.call_soon(self.poll)
        eventloop.call_soon(self.tunnel_message_to_remote_objects)
           

    async def poll(self):
        self.stop_poll = False
        while not self.stop_poll:
            sockets = await self.poller.poll(self.poll_timeout) 
            for socket, _ in sockets:
                while True:
                    try:
                        instruction = self.parse_client_message(await socket.recv_multipart(zmq.NOBLOCK))
                    except zmq.Again:
                        break
                    else:
                        timeout = instruction[7].get("timeout", None)
                        ready_to_process_event = asyncio.Event()
                        self._instructions.append((instruction, ready_to_process_event, 
                                    asyncio.create_task(self.process_timeouts(ready_to_process_event, timeout)),
                                    socket                                  
                                    ))
           

    async def tunnel_message_to_remote_objects(self, origin_socket : zmq.Context.socket):
        """
        client's message to server looks as follows:
        [address, bytes(), client type, message type, msg id, instruction, arguments, execution_context]
        [ 0     ,   1    ,     2      ,      3      ,   4   ,   5        ,  6       ,  7  ]
        """
        while not self.stop_poll:
            message, timeout_event, timeout_future = self._instructions.popleft()
            await timeout_event.set()
            if not timeout_future.done(): 
                await asyncio.wait(timeout_future)
            if timeout_future.result():
                await self.inproc_client.socket.send_multipart(message)
                reply = await self.inproc_client.async_recv_reply()
                await origin_socket.send_multipart(reply)
        

    async def process_timeouts(self, ready_to_process_event : asyncio.Event, origin_socket : zmq.Socket,
                            original_message : typing.List, timeout : typing.Optional[float] = None) -> bool:
        try:
            await asyncio.wait_for(ready_to_process_event.wait(), timeout)
            return True 
        except TimeoutError:    
            await self._socket_to_server_map[origin_socket].async_send_reply(original_message, 'TIMEOUT')
            return False

    
       
class BaseZMQClient(BaseZMQ):
    """    
    Server to client: 

        [address, bytes(), message_type, msg id, content]

        Reply - [client address, bytes, REPLY, msg id, content]

    Execution Context Definitions:
        "plain_reply"
        "fetch_execution_logs"
    """

    def __init__(self, server_address : Union[bytes, None], server_instance_name : Union[str, None], 
                client_type : bytes, **kwargs) -> None:
        if client_type in [PROXY, HTTP_SERVER]: 
            self.client_type = client_type
        else:
            raise ValueError("invalid client type for {}. Given option {}".format(self.__class__, client_type)) 
        self.rpc_serializer = None
        self.json_serializer = None
        if client_type == HTTP_SERVER:
            json_serializer = kwargs.get("json_serializer", None)
            if json_serializer is None or isinstance(json_serializer, JSONSerializer):
                self.json_serializer = json_serializer or JSONSerializer()
            else:
                raise ValueError("invalid JSON serializer option for {}. Given option {}".format(self.__class__, json_serializer))
        else: 
            rpc_serializer = kwargs.get("rpc_serializer", None)
            if rpc_serializer is None or isinstance(rpc_serializer, (PickleSerializer, SerpentSerializer, 
                                                                            JSONSerializer)):#, DillSerializer)): 
                self.rpc_serializer = rpc_serializer or SerpentSerializer()
            elif isinstance(rpc_serializer, str) and rpc_serializer in serializers.keys():
                self.rpc_serializer = serializers[rpc_serializer]()
            else:
                raise ValueError("invalid proxy serializer option for {}. Given option {}".format(self.__class__, rpc_serializer))
        self.server_address = server_address
        self.server_instance_name = server_instance_name
        self.server_type = ServerTypes.UNKNOWN_TYPE
        super().__init__()


    def parse_server_message(self, message : List[bytes]) -> Any:
        """
        Server to client: 

        [address, bytes(), message_type, msg id, content or response or reply]
        [0          1    ,    2        ,   3   ,    4   ]
        """
        message_type = message[3]
        if message_type == REPLY:
            if self.client_type == HTTP_SERVER:
                message[5] = self.json_serializer.loads(message[5])  # type: ignore
            elif self.client_type == PROXY:
                message[5] = self.rpc_serializer.loads(message[5]) # type: ignore
            return message 
        elif message_type == HANDSHAKE:
            self.logger.debug("""handshake messages arriving out of order are silently dropped as receiving this message 
            means handshake was successful before. Received hanshake from {}""".format(message[0]))
        elif message_type == INVALID_MESSAGE:
            raise Exception("Invalid message sent")
        elif message_type == EVENT_SUBSCRIPTION:
            return message[0], message[3], message[4]
        else:
            raise NotImplementedError("Unknown message type {} received. This message cannot be dealt.".format(message_type))

    def craft_instruction_from_arguments(self, instruction : str, arguments : Dict[str, Any], # type: ignore
                          context : Dict[str, Any]) -> List[bytes]:  # type: ignore
        """
        message from client to server :

        [address, bytes(), client type, message type, msg id, instruction, arguments]
        [ 0     ,   1    ,     2      ,      3      ,   4   ,    5       ,     6    ]

        Handshake - [client address, bytes, client_type, HANDSHAKE]
        """
        message_id = bytes(str(hash(instruction + current_datetime_ms_str())), encoding='utf-8')
        if self.client_type == HTTP_SERVER:
            instruction : bytes = self.json_serializer.dumps(instruction)
            context : bytes = self.json_serializer.dumps(context)
            if arguments == b'':
                arguments : bytes = self.json_serializer.dumps({}) 
            elif not isinstance(arguments, bytes):
                arguments : bytes = self.json_serializer.dumps(arguments) 
        else:
            instruction : bytes = self.rpc_serializer.dumps(instruction)
            context : bytes = self.rpc_serializer.dumps(context)
            arguments : bytes = self.rpc_serializer.dumps(arguments) 
        return [
            self.server_address, 
            EMPTY_BYTE,
            self.client_type,
            INSTRUCTION,
            message_id,
            instruction,
            arguments,
            context
        ]

    def craft_message(self, message_type : bytes):
        return [
            self.server_address, 
            EMPTY_BYTE,
            self.client_type,
            message_type,
            EMPTY_BYTE,
            EMPTY_BYTE,
            EMPTY_BYTE,
            EMPTY_BYTE
        ]


class SyncZMQClient(BaseZMQClient, BaseSyncZMQ):

    def __init__(self, server_instance_name : str, identity : str, client_type = HTTP_SERVER, 
                handshake : bool = True, protocol : str = "IPC", context : Union[zmq.asyncio.Context, None] = None, 
                **serializer) -> None:
        BaseZMQClient.__init__(self, server_address =  bytes(server_instance_name, encoding='utf-8'),
                            server_instance_name=server_instance_name, client_type=client_type, **serializer)
        BaseSyncZMQ.__init__(self)
        self.create_socket(context or zmq.Context(), server_instance_name, identity)
        self._terminate_context = context == None
        if handshake:
            self.handshake()
    
    def send_instruction(self, instruction : str, arguments : Dict[str, Any] = EMPTY_DICT, context : Dict[str, Any] = EMPTY_DICT) -> bytes:
        message = self.craft_instruction_from_arguments(instruction, arguments, context)
        self.socket.send_multipart(message)
        self.logger.debug("sent instruction '{}' to server '{}' with msg-id {}".format(instruction, self.server_instance_name, 
                                                                                        message[4]))
        return message[4]
    
    def recv_reply(self,  raise_client_side_exception : bool = False) -> Sequence[Union[bytes, Dict[str, Any]]]:
        while True:
            reply = self.parse_server_message(self.socket.recv_multipart()) # type: ignore
            if reply:
                self.logger.debug("received reply with msg-id {}".format(reply[3]))
                if reply[5].get('exception', None) is not None and raise_client_side_exception:
                    raise_local_exception(reply[5]['exception'])
                return reply
                
    def execute(self, instruction : str, arguments : Dict[str, Any] = EMPTY_DICT, context : Dict[str, Any] = EMPTY_DICT,
                        raise_client_side_exception : bool = False) -> Any:
        self.send_instruction(instruction, arguments, context)
        return self.recv_reply(raise_client_side_exception)
    
    def read_attribute(self, attribute_url : str, context : Dict[str, Any] = EMPTY_DICT, 
                       raise_client_side_exception : bool = False) -> Any:
        return self.execute(attribute_url+'/read', EMPTY_DICT, context, raise_client_side_exception)
    
    def write_attribute(self, attribute_url : str, value : Any, context : Dict[str, Any] = EMPTY_DICT, 
                       raise_client_side_exception : bool = False) -> Any:
        return self.execute(attribute_url+'/read', {"value" : value}, context, raise_client_side_exception)

    def handshake(self) -> None: 
        poller = zmq.Poller()
        poller.register(self.socket, zmq.POLLIN)
        while True:
            self.socket.send_multipart(self.craft_message(HANDSHAKE))
            self.logger.debug("sent Handshake to server '{}'".format(self.server_instance_name))
            if poller.poll(500):
                try:
                    message = self.socket.recv_multipart(zmq.NOBLOCK)
                except zmq.Again:
                    pass 
                else:
                    if message[3] == HANDSHAKE:  # type: ignore
                        self.logger.info("client '{}' handshook with server '{}'".format(self.identity,
                                                                                         self.server_instance_name))
                        self.server_type = ServerTypes._value2member_map_[message[2]] # type: ignore
                        break
                    else:
                        raise ValueError('Handshake cannot be done. Another message arrived before handshake complete.')
        poller.unregister(self.socket)
        del poller 

    def exit(self) -> None:
        try:
            self.socket.close(0)
            self.logger.info("terminated socket of server '{}' of type '{}'".format(self.identity, self.__class__))
        except Exception as E:
            self.logger.warn("could not properly terminate socket or attempted to terminate an already terminated socket '{}'of type '{}'. Exception message : {}".format(
                self.identity, self.__class__, str(E)))
        try:
            if self._terminate_context:
                self.context.term()
                self.logger.info("terminated context of socket '{}' of type '{}'".format(self.identity, self.__class__))
        except Exception as E:
            self.logger.warn("could not properly terminate context or attempted to terminate an already terminated context '{}'. Exception message : {}".format(
                self.identity, str(E)))
      
        

class AsyncZMQClient(BaseZMQClient, BaseAsyncZMQ):

    """ 
    Asynchronous client to talk to a ZMQ server where the server is identified by the instance name. The identity 
    of the client needs to be different from the server, unlike the ZMQ Server. The client will also perform handshakes 
    if necessary.
    """

    def __init__(self, server_instance_name : str, identity : str, client_type = HTTP_SERVER, 
                handshake : bool = True, protocol : str = "IPC", context : Union[zmq.asyncio.Context, None] = None, 
                **serializer) -> None:
        BaseZMQClient.__init__(self, server_address =  bytes(server_instance_name, encoding='utf-8'),
                    server_instance_name = server_instance_name, client_type = client_type, **serializer)
        BaseAsyncZMQ.__init__(self)
        self.create_socket(context, server_instance_name, identity)
        self._terminate_context = context == None
        self.handshake_event = asyncio.Event()
        if handshake:
            self.handshake()
    
    def handshake(self) -> None:
        run_coro_somehow(self._handshake())

    async def _handshake(self) -> None:
        self.handshake_event.clear()
        poller = zmq.asyncio.Poller()
        poller.register(self.socket, zmq.POLLIN)
        while True:
            await self.socket.send_multipart(self.craft_message(HANDSHAKE))
            self.logger.debug("sent Handshake to server '{}'".format(self.server_instance_name))
            if await poller.poll(500):
                try:
                    msg = await self.socket.recv_multipart(zmq.NOBLOCK)
                except zmq.Again:
                    pass 
                else:
                    if msg[3] == HANDSHAKE: 
                        self.logger.info("client '{}' handshook with server '{}'".format(self.identity,self.server_instance_name))
                        self.server_type = ServerTypes._value2member_map_[msg[2]]
                        break
                    else:
                        self.logger.info("handshake cannot be done with server '{}'. another message arrived before handshake complete.".format(self.server_instance_name))
        self.handshake_event.set()
        poller.unregister(self.socket)
        del poller
    
    async def handshake_complete(self):
        await self.handshake_event.wait()
       
    async def async_send_instruction(self, instruction : str, arguments : Dict[str, Any] = EMPTY_DICT, 
                                    context : Dict[str, Any] = EMPTY_DICT) -> bytes:
        message = self.craft_instruction_from_arguments(instruction, arguments, context) 
        await self.socket.send_multipart(message)
        self.logger.debug("sent instruction '{}' to server '{}' with msg-id {}".format(instruction, self.server_instance_name, 
                                                                                       message[3]))
        return message[4]
    
    async def async_recv_reply(self, raise_client_side_exception) -> Sequence[Union[bytes, Dict[str, Any]]]:
        while True:
            reply = self.parse_server_message(await self.socket.recv_multipart())# [2] # type: ignore
            if reply:
                self.logger.debug("received reply with message-id {}".format(reply[3]))
                if reply[5].get('exception', None) is not None and raise_client_side_exception:
                    exc_info = reply[5]['exception']
                    raise Exception("traceback : {},\nmessage : {},\ntype : {}".format('\n'.join(exc_info["traceback"]), 
                                                                        exc_info['message'], exc_info["type"]))
                return reply
            
    async def async_execute(self, instruction : str, arguments : Dict[str, Any] = EMPTY_DICT, context : Dict[str, Any] = EMPTY_DICT,
                       raise_client_side_exception = False): 
        await self.async_send_instruction(instruction, arguments, context)
        return await self.async_recv_reply(raise_client_side_exception)
    
    async def read_attribute(self, attribute_url : str, context : Dict[str, Any] = EMPTY_DICT, 
                       raise_client_side_exception : bool = False) -> Any:
        return await self.async_execute(attribute_url+'/read', EMPTY_DICT, context, raise_client_side_exception)
    
    async def write_attribute(self, attribute_url : str, value : Any, context : Dict[str, Any] = EMPTY_DICT, 
                       raise_client_side_exception : bool = False) -> Any:
        return self.async_execute(attribute_url+'/write', {"value" : value}, context, raise_client_side_exception)

    def exit(self) -> None:
        try:
            self.socket.close(0)
            self.logger.info("terminated socket of server '{}' of type '{}'".format(self.identity, self.__class__))
        except Exception as E:
            self.logger.warn("could not properly terminate socket or attempted to terminate an already terminated socket '{}'of type '{}'. Exception message : {}".format(
                self.identity, self.__class__, str(E)))
        try:
            if self._terminate_context:
                self.context.term()
                self.logger.info("terminated context of socket '{}' of type '{}'".format(self.identity, self.__class__))
        except Exception as E:
            self.logger.warn("could not properly terminate context or attempted to terminate an already terminated context '{}'. Exception message : {}".format(
                self.identity, str(E)))

    

class AsyncZMQClientPool(BaseZMQClient):

    def __init__(self, server_instance_names : List[str], identity : str, client_type = HTTP_SERVER, 
                protocol : str = 'IPC', **serializer) -> None:
        self.identity = identity
        self.context = zmq.asyncio.Context()
        self.pool : Dict[str, AsyncZMQClient] = dict()
        for instance_name in server_instance_names:
            self.pool[instance_name] = AsyncZMQClient(server_instance_name = instance_name,
                identity = identity, client_type = client_type, handshake = True, protocol = protocol, 
                context = self.context, **serializer)
        self.poller = zmq.asyncio.Poller()
        for client in self.pool.values():
            self.poller.register(client.socket, zmq.POLLIN)
        self.logger = self.get_logger(identity, 'pooled', logging.DEBUG)
        # Both the client pool as well as the individual client get their serializers and client_types
        # This is required to implement pool level sending and receiving messages like polling of pool of sockets
        super().__init__(server_address = None, server_instance_name = None, client_type = client_type, **serializer)
  
    async def poll(self) -> None :
        raise NotImplementedError("implement poll function for AsyncZMQClientPool subclass {}".format(self.__class__)) 

    def register_client(self, instance_name : str, protocol : str = 'IPC'):
        if instance_name not in self.pool.keys():
            self.pool[instance_name] = AsyncZMQClient(server_instance_name = instance_name,
                identity = self.identity, client_type = self.client_type, handshake = True, protocol = protocol, 
                context = self.context, rpc_serializer = self.rpc_serializer, json_serializer = self.json_serializer)
        else: 
            raise ValueError("client already present in pool")
        
    def __contains__(self, name : str) -> bool:
        return name in self.pool

    def __getitem__(self, key) ->AsyncZMQClient:
        return self.pool[key]
    
    def __iter__(self) -> Iterator[AsyncZMQClient]:
        return iter(self.pool.values())
    
    def exit(self) -> None:
        for client in self.pool.values():
            self.poller.unregister(client.socket)
            client.exit()
        self.logger.info("all client socket unregistered from pool for '{}'".format(self.__class__))
        try:
            self.context.term()
            self.logger.info("context terminated for '{}'".format(self.__class__))        
        except:
            pass 
    
    

class MessageMappedZMQClientPool(AsyncZMQClientPool):
    """
    Pool of clients where message ID can track the replies irrespective of order of arrival. 
    """

    def __init__(self, instance_names: List[str], identity: str, poll_timeout = 25, protocol : str = 'IPC',
                client_type = HTTP_SERVER, **serializer) -> None:
        super().__init__(instance_names, identity, client_type = client_type, protocol = protocol, **serializer)
        self.event_pool = EventPool(len(instance_names))
        self.message_to_event_map : Dict[bytes, asyncio.Event] = dict()
        self.shared_message_map = dict()
        self.poll_timeout = poll_timeout
        self.stop_poll = False 
        self.cancelled_messages = []

    @property
    def poll_timeout(self) -> int:
        return self._poll_timeout

    @poll_timeout.setter
    def poll_timeout(self, value) -> None:
        if not isinstance(value, int) or value < 0:
            raise ValueError("polling period must be an integer greater than 0, not {}. Value is considered in milliseconds".format(value))
        self._poll_timeout = value 

    async def poll(self) -> None:
        self.logger.info("client polling started for sockets for {}".format(list(self.pool.keys())))
        self.stop_poll = False 
        event_loop = asyncio.get_event_loop()
        while not self.stop_poll:
            sockets = await self.poller.poll(self.poll_timeout) # type hints dont work in this line
            for socket, _ in sockets:
                while True:
                    try:
                        reply = self.parse_server_message(await socket.recv_multipart(zmq.NOBLOCK))
                    except zmq.Again:
                        break
                        """
                        errors in handle_message should reach the client. 
                        """
                    if reply:
                        address, _, server_type, message_type, message_id, response = reply
                        self.logger.debug("received reply from server '{}' with message ID {}".format(address, message_id))
                        if message_id in self.cancelled_messages:
                            self.cancelled_messages.remove(message_id)
                            self.logger.debug(f'message_id {message_id} cancelled')
                            continue
                        try:
                            event = self.message_to_event_map[message_id] # type: ignore
                        except KeyError:
                            event_loop.call_soon(lambda: asyncio.create_task(self.resolve_reply(message_id, response)))
                        else:    
                            self.shared_message_map[message_id] = response
                            event.set()

    async def resolve_reply(self, message_id, return_value):
        max_number_of_retries = 100
        for i in range(max_number_of_retries):
            await asyncio.sleep(0.1)
            try:
                event = self.message_to_event_map[message_id] # type: ignore
            except KeyError:
                if message_id in self.cancelled_messages:
                    # Only for safety, likely should never reach here
                    self.cancelled_messages.remove(message_id)
                    self.logger.debug(f'message_id {message_id} cancelled')
                    return 
                if i >= max_number_of_retries - 1:
                    self.logger.error("unknown message id {} without corresponding event object".format(message_id)) 
                    print(return_value)
                    return
            else:    
                self.shared_message_map[message_id] = return_value
                event.set()
                break

    async def async_send_instruction(self, instance_name : str, instruction : str, arguments : Dict[str, Any] = EMPTY_DICT,
                                    context : Dict[str, Any] = EMPTY_DICT) -> bytes:
        message_id = await self.pool[instance_name].async_send_instruction(instruction, arguments, context)
        event = self.event_pool.pop()
        self.message_to_event_map[message_id] = event 
        return message_id

    async def async_recv_reply(self, message_id : bytes, plain_reply : bool = False, raise_client_side_exception = False,
                                timeout : typing.Optional[int] = 3) -> Dict[str, Any]:
        event = self.message_to_event_map[message_id]
        try:
            await asyncio.wait_for(event.wait(), timeout if (timeout and timeout > 0) else None)
        except TimeoutError:
            self.cancelled_messages.append(message_id)
            self.logger.debug(f'message_id {message_id} added to list of cancelled messages')
        else:
            self.message_to_event_map.pop(message_id)
            reply = self.shared_message_map.pop(message_id)
            self.event_pool.completed(event)
            if not plain_reply and reply.get('exception', None) is not None and raise_client_side_exception:
                exc_info = reply['exception']
                raise Exception("traceback : {},\nmessage : {},\ntype : {}".format (
                                '\n'.join(exc_info["traceback"]), exc_info['message'], exc_info["type"]))
            return reply
        raise TimeoutError(f"Execution not completed within {timeout} seconds")

    async def async_execute(self, instance_name : str, instruction : str, arguments : Dict[str, Any] = EMPTY_DICT, 
                    context : Dict[str, Any] = EMPTY_DICT, raise_client_side_exception = False, 
                    timeout : typing.Optional[int] = 3) -> Dict[str, Any]:
        message_id = await self.async_send_instruction(instance_name, instruction, arguments, context)
        return await self.async_recv_reply(message_id, context.get('plain_reply', False), raise_client_side_exception,
                                        timeout)

    def start_polling(self) -> None:
        event_loop = asyncio.get_event_loop()
        event_loop.call_soon(lambda: asyncio.create_task(self.poll()))

    async def stop_polling(self):
        self.stop_poll = True

    async def ping_all_servers(self):
        replies : List[Dict[str, Any]] = await asyncio.gather(*[
            self.async_execute(instance_name, '/ping') for instance_name in self.pool.keys()])
        sorted_reply = dict() 
        for reply, instance_name in zip(replies, self.pool.keys()):
            sorted_reply[instance_name] = reply.get("returnValue", False if reply.get("exception", None) is None else True)  # type: ignore
        return sorted_reply

    def organised_gathered_replies(self, instance_names : List[str], gathered_replies : List[Any], context : Dict[str, Any] = EMPTY_DICT):
        """
        First thing tomorrow
        """
        plain_reply = context.pop('plain_reply', False)
        if not plain_reply:
            replies = dict(
                returnValue = dict(),
                state = dict()
            )
            for  instance_name, reply in zip(instance_names, gathered_replies):
                replies["state"].update(reply["state"])
                replies["returnValue"][instance_name] = reply.get("returnValue", reply.get("exception", None))
        else: 
            replies = {}
            for instance_name, reply in zip(instance_names, gathered_replies):
                replies[instance_name] = reply
        return replies  

    async def async_execute_in_all(self, instruction : str, arguments : Dict[str, Any] = EMPTY_DICT, 
                        context : Dict[str, Any] = EMPTY_DICT, raise_client_side_exception = False) -> Dict[str, Any]:
        instance_names = self.pool.keys()
        gathered_replies = await asyncio.gather(*[
            self.async_execute(instance_name, instruction, arguments, context, raise_client_side_exception) for instance_name in instance_names])
        return self.organised_gathered_replies(instance_names, gathered_replies, context)
    
    async def async_execute_in_all_remote_objects(self, instruction : str, arguments : Dict[str, Any] = EMPTY_DICT,
                                context : Dict[str, Any] = EMPTY_DICT, raise_client_side_exception = False) -> Dict[str, Any]:
        instance_names = [instance_name for instance_name, client in self.pool.items() if client.server_type == ServerTypes.USER_REMOTE_OBJECT]
        gathered_replies = await asyncio.gather(*[
            self.async_execute(instance_name, instruction, arguments, context, raise_client_side_exception) for instance_name in instance_names])
        return self.organised_gathered_replies(instance_names, gathered_replies, context)
    
    async def async_execute_in_all_eventloops(self, instruction : str, arguments : Dict[str, Any] = EMPTY_DICT, 
                        context : Dict[str, Any] = EMPTY_DICT, raise_client_side_exception = False) -> Dict[str, Any]:
        instance_names = [instance_name for instance_name, client in self.pool.items() if client.server_type == ServerTypes.EVENTLOOP]
        gathered_replies = await asyncio.gather(*[
            self.async_execute(instance_name, instruction, arguments, context, raise_client_side_exception) for instance_name in instance_names])
        return self.organised_gathered_replies(instance_names, gathered_replies, context)


class EventPool:
    """
    creates a pool of asyncio Events to be used as a synchronisation object for MessageMappedClientPool
    """

    def __init__(self, initial_number_of_events : int) -> None:
        self.pool = [asyncio.Event() for i in range(initial_number_of_events)] 
        self.size = initial_number_of_events

    def pop(self) -> asyncio.Event:
        try:
            event = self.pool.pop(0)
        except IndexError:
            self.size += 1
            event = asyncio.Event()
        event.clear()
        return event

    def completed(self, event : asyncio.Event) -> None:
        self.pool.append(event)



class Event:

    def __init__(self, name : str, URL_path : typing.Optional[str] = None) -> None:
        self.name = name 
        # self.name_bytes = bytes(name, encoding = 'utf-8')
        self.URL_path = URL_path or '/' + name
        self._unique_event_name = None # type: typing.Optional[str]
        self._owner = None  # type: typing.Optional[Parameterized]

    @property
    def owner(self):
        return self._owner        
        
    @property
    def publisher(self) -> "EventPublisher": 
        return self._publisher
    
    @publisher.setter
    def publisher(self, value : "EventPublisher") -> None:
        if not hasattr(self, '_publisher'):
            self._publisher = value
            self._publisher.register_event(self)
        else:
            raise AttributeError("cannot reassign publisher attribute of event {}".format(self.name)) 

    def push(self, data : typing.Any = None, serialize : bool = True):
        self.publisher.publish_event(self._unique_event_name, data, serialize)



class CriticalEvent(Event):

    def __init__(self, name : str, message_broker : BaseZMQServer, acknowledgement_timeout : float = 3, 
                URL_path : typing.Optional[str] = None) -> None:
        super().__init__(name, URL_path)
        self.message_broker = message_broker
        self.aknowledgement_timeout = acknowledgement_timeout

    def push(self, data : typing.Any = None):
        super().push(data)
        self.message_broker.receive_acknowledgement()



class EventPublisher(BaseZMQServer):

    def __init__(self,  identity : str, context : Union[zmq.Context, None] = None, **serializer) -> None:
        super().__init__(server_type = ServerTypes.UNKNOWN_TYPE, **serializer)
        self.context = context or zmq.Context()
        self.identity = identity
        self.socket = self.context.socket(zmq.PUB)
        for i in range(1000, 65535):
            try:
                self.socket_address = "tcp://127.0.0.1:{}".format(i)
                self.socket.bind(self.socket_address)
            except zmq.error.ZMQError as ex:
                if ex.strerror.startswith('Address in use'):
                    pass 
                else:
                    print("Following error while atttempting to bind to socket address : {}".format(self.socket_address))
                    raise ex from None
            else:
                self.logger = self.get_logger(identity, self.socket_address, logging.DEBUG, self.__class__.__name__)
                self.logger.info("created event publishing socket at {}".format(self.socket_address))
                break
        self.events : Set[Event] = set() 
        self.event_ids : Set[bytes] = set()

    def register_event(self, event : Event) -> None:
        # unique_str_bytes = bytes(unique_str, encoding = 'utf-8') 
        if event._event_unique_str in self.events:
            raise AttributeError(wrap_text(
                """event {} already found in list of events, please use another name. 
                Also, Remotesubobject and RemoteObject cannot share event names.""".format(event.name))
            )
        self.event_ids.add(event._event_unique_str)
        self.events.add(event) 
        self.logger.info("registered event '{}' serving at PUB socket with address : {}".format(event.name, self.socket_address))
               
    def publish_event(self, unique_str : bytes, data : Any, serialize : bool = True) -> None: 
        if unique_str in self.event_ids:
            self.socket.send_multipart([unique_str, self.json_serializer.dumps(data) if serialize else data])
        else:
            raise AttributeError("event name {} not yet registered with socket {}".format(unique_str, self.socket_address))
        
    def exit(self):
        try:
            self.socket.close()
            self.logger.info("terminated event publishing socket with address '{}'".format(self.socket_address))
        except Exception as E:
            self.logger.warn("could not properly terminate context or attempted to terminate an already terminated context at address '{}'. Exception message : {}".format(
                self.socket_address, str(E)))
        try:
            self.context.term()
            self.logger.info("terminated context of event publishing socket with address '{}'".format(self.socket_address)) 
        except Exception as E: 
            self.logger.warn("could not properly terminate socket or attempted to terminate an already terminated socket of event publishing socket at address '{}'. Exception message : {}".format(
                self.socket_address, str(E)))
      

class EventConsumer(BaseZMQClient):

    def __init__(self, event_URL : str, socket_address : str, identity : str, client_type = HTTP_SERVER, **kwargs) -> None:
        super().__init__(server_address=b'unknown', server_instance_name='unkown', client_type=client_type, **kwargs)
        # Prepare our context and publisher
        self.event_URL = bytes(event_URL, encoding = 'utf-8')
        self.socket_address = socket_address
        self.identity = identity
        self.context = zmq.asyncio.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.connect(socket_address)
        self.socket.setsockopt(zmq.SUBSCRIBE, self.event_URL)
        self.logger = self.get_logger(identity, self.socket_address, logging.DEBUG, self.__class__.__name__)
        self.logger.info("connected event consuming socket to address {}".format(self.socket_address))
      
    async def receive_event(self, deserialize = False):
        _, contents = await self.socket.recv_multipart()
        if not deserialize: 
            return contents
        return self.json_serializer.loads(contents)
    
    def exit(self):
        try:
            self.socket.close()
            self.logger.info("terminated event consuming socket with address '{}'".format(self.socket_address))
        except Exception as E:
            self.logger.warn("could not properly terminate context or attempted to terminate an already terminated context at address '{}'. Exception message : {}".format(
                self.socket_address, str(E)))
        try:
            self.context.term()
            self.logger.info("terminated context of event consuming socket with address '{}'".format(self.socket_address)) 
        except Exception as E: 
            self.logger.warn("could not properly terminate socket or attempted to terminate an already terminated socket of event consuming socket at address '{}'. Exception message : {}".format(
                self.socket_address, str(E)))
            


__all__ = ['ServerTypes', 'AsyncZMQServer', 'AsyncPollingZMQServer', 'ZMQServerPool', 'SyncZMQClient', 
           'AsyncZMQClient', 'AsyncZMQClientPool', 'MessageMappedZMQClientPool', 'Event', 'CriticalEvent']