import builtins
import os
from typing import List
import zmq
import zmq.asyncio
import asyncio
import logging
import typing
from uuid import uuid4
from collections import deque
from enum import Enum


from .utils import create_default_logger, run_method_somehow, wrap_text
from .config import global_config
from .constants import ZMQ_PROTOCOLS
from .serializers import (JSONSerializer, PickleSerializer, BaseSerializer, SerpentSerializer, # DillSerializer, 
                        serializers)
from ..param.parameterized import Parameterized



# message types
HANDSHAKE   = b'HANDSHAKE'
INVALID_MESSAGE = b'INVALID_MESSAGE'
TIMEOUT = b'TIMEOUT'
INSTRUCTION = b'INSTRUCTION'
REPLY       = b'REPLY'

EVENT       = b'EVENT'
EVENT_SUBSCRIPTION = b'EVENT_SUBSCRIPTION'
SUCCESS     = b'SUCCESS'

# empty data
EMPTY_BYTE  = b''
EMPTY_DICT  = {}

FAILURE     = b'FAILURE'

# client types
HTTP_SERVER = b'HTTP_SERVER'
PROXY = b'PROXY'
TUNNELER = b'TUNNELER' # message passer from inproc client to inrproc server within RPC


"""
Message indices 

client's message to server: |br|
[address, bytes(), client type, message type, message id, timeout, instruction, arguments, execution_context] |br|
[ 0     ,   1    ,     2      ,      3      ,   4   ,   5        ,    6       ,     7    ,        8         ] |br|

[address, bytes(), server_type, message_type, message id, data]|br|
[   0   ,   1    ,    2       ,      3      ,      4    ,  5  ]|br|
"""
# CM = Client Message
CM_INDEX_ADDRESS = 0
CM_INDEX_CLIENT_TYPE = 2
CM_INDEX_MESSAGE_TYPE = 3
CM_INDEX_MESSAGE_ID = 4
CM_INDEX_TIMEOUT = 5
CM_INDEX_INSTRUCTION = 6
CM_INDEX_ARGUMENTS = 7
CM_INDEX_EXECUTION_CONTEXT = 8

# SM = Server Message
SM_INDEX_ADDRESS = 0
SM_INDEX_SERVER_TYPE = 2
SM_INDEX_MESSAGE_TYPE = 3
SM_INDEX_MESSAGE_ID = 4
SM_INDEX_DATA = 5

# Server types - currently useless metadata
class ServerTypes(Enum):
    UNKNOWN_TYPE = b'UNKNOWN_TYPE'
    EVENTLOOP = b'EVENTLOOP'
    REMOTE_OBJECT = b'REMOTE_OBJECT'
    POOL = b'POOL'
       


class BaseZMQ: 
    """
    Base class for all ZMQ message brokers. Implements `create_socket()` method & logger which is common to 
    all server and client implementations. 
    """
    def __init__(self) -> None:
        # only type definition for logger
        self.logger : logging.Logger
        
    def exit(self) -> None:
        """
        Cleanup method to terminate ZMQ sockets and contexts before quitting. Called by `__del__()`
        automatically. Each subclass server/client should implement their version of exiting if necessary.
        """
        raise NotImplementedError("Implement exit() to gracefully exit ZMQ in {}.".format(self.__class__))

    def create_socket(self, context : typing.Union[zmq.asyncio.Context, zmq.Context], instance_name : str, 
                    identity : str, bind : bool = False, protocol : ZMQ_PROTOCOLS = ZMQ_PROTOCOLS.IPC, 
                    socket_type : zmq.SocketType = zmq.ROUTER, **kwargs) -> None:
        """
        Create a socket with certain specifications. When successful, a logger is also created. Supported ZeroMQ protocols
        are TCP, IPC & INPROC. For IPC sockets, a file is created under TEMP_DIR of global configuration.

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
        **kwargs: dict
            socket_address: str
                applicable only for TCP socket to find the correct socket to connect. 

        Returns
        -------
        None 

        Raises
        ------
        NotImplementedError
            if protocol other than TCP, IPC or INPROC is used
        RuntimeError
            if protocol is TCP, a connection from client side is desired but a socket address is not supplied
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
            # re-compute for IPC because it looks for a file in a directory
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
            elif kwargs.get('socket_address', None):
                self.socket.connect(kwargs["socket_address"])
            else:
                raise RuntimeError(f"Socket must be either bound or connected. No operation is being carried out for this socket {identity}")
        elif protocol == ZMQ_PROTOCOLS.INPROC or protocol == "INPROC":
            # inproc_instance_name = instance_name.replace('/', '_').replace('-', '_')
            socket_address = f'inproc://{instance_name}'
            if bind:
                self.socket.bind(socket_address)
            else:
                self.socket.connect(socket_address)
        else:
            raise NotImplementedError("protocols other than IPC, TCP & INPROC are not implemented now for {}".format(self.__class__))
        self.logger = self.get_logger(self.identity, socket_type.name, protocol.name if isinstance(protocol, Enum) else protocol) 
        self.logger.info("created socket with address {} and {}".format(socket_address, "bound" if bind else "connected"))

    @classmethod
    def get_logger(cls, identity : str, socket_type : str, protocol : str, level = logging.DEBUG) -> logging.Logger:
        """
        creates a logger with name {class name} | {socket type} | {protocol} | {identity},
        default logging level is ``logging.INFO`` 
        """
        return create_default_logger('{}|{}|{}|{}'.format(cls.__name__, socket_type, protocol, identity) , level)
    
    def __del__(self) -> None:
        self.exit()


class BaseAsyncZMQ(BaseZMQ):
    """
    Base class for all async ZMQ servers and clients.
    """

    def create_socket(self, instance_name : str, context : typing.Union[zmq.asyncio.Context, None], *, identity : str, 
            bind : bool = False, protocol : str = "IPC", socket_type : zmq.SocketType = zmq.ROUTER, **kwargs) -> None:
        """
        Overloads ``create_socket()`` to create, bind/connect an async socket. A async context is created if none is supplied. 
        """
        if context and not isinstance(context, zmq.asyncio.Context):
            raise TypeError("async ZMQ message broker accepts only async ZMQ context. supplied type {}".format(type(context)))
        context = context or zmq.asyncio.Context()
        super().create_socket(context, instance_name, identity, bind, protocol, socket_type, **kwargs)
        

class BaseSyncZMQ(BaseZMQ):
    """
    Base class for all sync ZMQ servers and clients.
    """

    def create_socket(self, instance_name : str, context : typing.Union[zmq.Context, None], *, identity : str, 
            bind : bool = False, protocol : str = "IPC", socket_type : zmq.SocketType = zmq.ROUTER, **kwargs) -> None:
        """
        Overloads ``create_socket()`` to create, bind/connect a synchronous socket. A (synchronous) context is created 
        if none is supplied. 
        """
        if context and not isinstance(context, zmq.Context):
            raise TypeError("sync ZMQ message broker accepts only sync ZMQ context. supplied type {}".format(type(context)))
        context = context or zmq.Context()
        super().create_socket(context, instance_name, identity, bind, protocol, socket_type, **kwargs)


class BaseZMQServer(BaseZMQ):
    """
    Implements serializer instantiation and message parsing for ZMQ servers and can be subclassed by all 
    server instances irrespective of sync or async. For HTTP clients, json_serializer is necessary and for RPC clients, 
    any of the allowed serializer is possible. As suggested by ZMQ, a messaging contract is defined which is defined 
    as follows: 
    
    client's message to server: 
    ::
        [address, bytes(), client type, message type, messsage id, 
        [   0   ,   1    ,     2      ,      3      ,      4     , 
        
        timeout, instruction, arguments, execution context] 
          5    ,      6     ,     7    ,       8          ]
        
    server's message to client: 
    ::
        [address, bytes(), server_type, message_type, message id, data]
        [   0   ,   1    ,    2       ,      3      ,      4    ,  5  ]

    The messaging contract does not depend on sync or async implementation.  

    Parameters
    ----------
    server_type: Enum
        metadata about the nature of the server - currently not important.
    json_serializer: hololinked.server.serializers.JSONSerializer
        serializer used to send message to HTTP Server
    rpc_serializer: any of hololinked.server.serializers.serializer, default serpent
        serializer used to send message to RPC clients
    """
    def __init__(self, server_type : Enum, json_serializer : typing.Union[None, JSONSerializer] = None, 
                rpc_serializer : typing.Union[str, BaseSerializer, None] = None) -> None:
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
        self.server_type = server_type # type: bytes
        super().__init__()


    def parse_client_message(self, message : typing.List[bytes]) -> typing.List[typing.Union[bytes, typing.Any]]:
        """
        deserializes important parts of the client's message, namely instruction, arguments, execution context 
        based on the client type. For handshake messages, automatically handles handshake. In case of exceptions while 
        deserializing, automatically sends an invalid message to client informing the nature of exception with the 
        exception metadata. 
        
        client's message to server:
        ::
            [address, bytes(), client type, message type, messsage id, 
            [   0   ,   1    ,     2      ,      3      ,      4     , 
            
            timeout, instruction, arguments, execution context] 
               5   ,      6     ,     7    ,       8          ]

        Execution Context Definitions (typing.Dict[str, typing.Any] or JSON):
            - "plain_reply" - does not return state 
            - "fetch_execution_logs" - fetches logs that were accumulated while execution

        Parameters
        ----------
        message: List[bytes]
            message received from client
      
        Returns
        -------
        message: List[bytes | Any]
            message with instruction, arguments and execution context deserialized

        """
        try:
            message_type = message[CM_INDEX_MESSAGE_TYPE]
            if message_type == INSTRUCTION:
                client_type = message[CM_INDEX_CLIENT_TYPE]
                if client_type == PROXY:
                    message[CM_INDEX_INSTRUCTION] = self.rpc_serializer.loads(message[CM_INDEX_INSTRUCTION]) # type: ignore
                    message[CM_INDEX_ARGUMENTS] = self.rpc_serializer.loads(message[CM_INDEX_ARGUMENTS]) # type: ignore
                    message[CM_INDEX_EXECUTION_CONTEXT] = self.rpc_serializer.loads(message[CM_INDEX_EXECUTION_CONTEXT]) # type: ignore
                elif client_type == HTTP_SERVER:
                    message[CM_INDEX_INSTRUCTION] = self.json_serializer.loads(message[CM_INDEX_INSTRUCTION]) # type: ignore
                    message[CM_INDEX_ARGUMENTS] = self.json_serializer.loads(message[CM_INDEX_ARGUMENTS]) # type: ignore
                    message[CM_INDEX_EXECUTION_CONTEXT] = self.json_serializer.loads(message[CM_INDEX_EXECUTION_CONTEXT]) # type: ignore
                return message 
            elif message_type == HANDSHAKE:
                self.handshake(message)
        except Exception as ex:
            self.handle_invalid_message(message, ex)


    def craft_reply_from_arguments(self, address : bytes, client_type: bytes, message_type : bytes, 
                            message_id : bytes = b'', data : typing.Any = None) -> typing.List[bytes]:
        """
        call this method to craft an arbitrary reply or message to the client using the method arguments. 

        server's message to client:
        ::
            [address, bytes(), server_type, message_type, message id, data]
            [   0   ,   1    ,    2       ,      3      ,  4        ,  5  ]

        Parameters
        ----------
        address: bytes 
            the ROUTER address of the client
        message_type: bytes 
            type of the message, possible values are b'REPLY', b'HANDSHAKE' and b'TIMEOUT' 
        message_id: bytes
            message id of the original client message for which the reply is being crafted
        data: Any
            serializable data
        
        Returns
        -------
        message: List[bytes]
            the crafted reply with information in the correct positions within the list
        """
        if client_type == HTTP_SERVER:
            data = self.json_serializer.dumps(data)
        elif client_type == PROXY:
            data = self.rpc_serializer.dumps(data)

        return [
            address,
            EMPTY_BYTE,
            self.server_type,
            message_type,
            message_id,
            data
        ] 
           

    def craft_reply_from_client_message(self, original_client_message : typing.List[bytes], 
                                                            data : typing.Any = None) -> typing.List[bytes]:
        """
        craft a reply with certain data automatically from an originating client message. The client's address, type required
        for serialization requirements, message id etc. are automatically created from the original message.         

        server's message to client:
        ::
            [address, bytes(), server_type, message_type, message id, data]
            [   0   ,   1    ,    2       ,      3      ,      4    ,  5  ]

        Parameters
        ----------
        original_client_message: List[bytes]
            The message originated by the clieht for which the reply is being crafted
        data: Any
            serializable data 

        Returns
        -------
        message: List[bytes]
            the crafted reply with information in the correct positions within the list
        """
        client_type = original_client_message[CM_INDEX_CLIENT_TYPE]
        if client_type == HTTP_SERVER:
            data = self.json_serializer.dumps(data)
        elif client_type == PROXY:
            data = self.rpc_serializer.dumps(data)
        else:
            raise ValueError("invalid client type given '{}' for preparing message to send from '{}' of type {}".format(
                                                                        client_type, self.identity, self.__class__))
        return [
            original_client_message[CM_INDEX_ADDRESS],
            EMPTY_BYTE,
            self.server_type,
            REPLY,
            original_client_message[CM_INDEX_MESSAGE_ID],
            data
        ]
    

    def handshake(self, original_client_message : typing.List[bytes]) -> None:
        """
        pass a handshake message to client. Absolutely mandatory to ensure initial messages do not get lost 
        because of ZMQ's very tiny but significant initial delay after creating socket.

        Parameters
        ----------
        address: bytes
            the address of the client to send the handshake

        Returns
        -------
        None 
        """
        run_method_somehow(self._handshake(original_client_message))

    def _handshake(self, original_client_message : typing.List[bytes]) -> None:
        raise NotImplementedError(
            wrap_text("handshake cannot be handled - implement _handshake in {} to handshake.".format(
                self.__class__)))


    def handle_invalid_message(self, original_client_message : typing.List[bytes], exception : Exception) -> None:
        """
        pass an invalid message to the client when an exception occurred while parsing the message from the client 
        (``parse_client_message()``)

        Parameters
        ----------
        original_client_message: List[bytes]
            the client message parsing which the exception occurred
        exception: Exception
            exception object raised

        Returns
        -------
        None
        """
        run_method_somehow(self._handle_invalid_message(original_client_message, exception))

    def _handle_invalid_message(self, message : typing.List[bytes], exception : Exception) -> None:
        raise NotImplementedError(
            wrap_text("invalid message cannot be handled - implement _handle_invalid_message in {} to handle invalid messages.".format(
                self.__class__)))
            

    def handle_timeout(self, original_client_message : typing.List[bytes]) -> None:
        """
        pass timeout message to the client when the instruction could not be executed within specified timeout

        Parameters
        ----------
        original_client_message: List[bytes]
            the client message which could not executed within the specified timeout. timeout value is 
            generally specified within the execution context values.
        
        Returns
        -------
        None
        """
        run_method_somehow(self._handle_timeout(original_client_message))

    def _handle_timeout(self, original_client_message : typing.List[bytes]) -> None:
        raise NotImplementedError(
            wrap_text("timeouts cannot be handled - implement _handle_timeout in {} to handle timeout.".format(
                self.__class__)))



class BaseAsyncZMQServer(BaseZMQServer):
    """
    Common to all async ZMQ servers
    """
    
    async def _handshake(self, original_client_message : typing.List[bytes]) -> None:
        """
        Inner method that handles handshake. scheduled by ``handshake()`` method, signature same as ``handshake()``.
        """
        await self.socket.send_multipart(self.craft_reply_from_arguments(original_client_message[CM_INDEX_ADDRESS], 
                original_client_message[CM_INDEX_CLIENT_TYPE], HANDSHAKE, original_client_message[CM_INDEX_MESSAGE_ID],
                EMPTY_BYTE))
        self.logger.info("sent handshake to client '{}'".format(original_client_message[CM_INDEX_ADDRESS]))


    async def _handle_timeout(self, original_client_message : typing.List[bytes]) -> None:
        """
        Inner method that handles timeout. scheduled by ``handle_timeout()``, signature same as ``handle_timeout``.
        """
        await self.socket.send_multipart(self.craft_reply_from_arguments(original_client_message[CM_INDEX_ADDRESS], 
                original_client_message[CM_INDEX_CLIENT_TYPE], TIMEOUT, original_client_message[CM_INDEX_MESSAGE_ID]))

    
    async def _handle_invalid_message(self, original_client_message : typing.List[bytes], exception : Exception) -> None:
        """
        Inner method that handles invalid messages. scheduled by ``handle_invalid_message()``, 
        signature same as ``handle_invalid_message()``.
        """
        await self.socket.send_multipart(self.craft_reply_from_arguments(original_client_message[CM_INDEX_ADDRESS], 
                                            original_client_message[CM_INDEX_CLIENT_TYPE], INVALID_MESSAGE, 
                                            original_client_message[CM_INDEX_MESSAGE_ID]), exception)         
        self.logger.info("sent exception message to client '{}' : '{}'".format(original_client_message[CM_INDEX_ADDRESS], 
                                                                               str(exception))) 	


       
class AsyncZMQServer(BaseAsyncZMQServer, BaseAsyncZMQ):
    """
    Implements blocking (non-polled) async receive instructions and send replies.  
    """

    def __init__(self, instance_name : str, server_type : Enum, context : typing.Union[zmq.asyncio.Context, None] = None, 
                protocol : ZMQ_PROTOCOLS = ZMQ_PROTOCOLS.IPC, socket_type : zmq.SocketType = zmq.ROUTER, **kwargs) -> None:
        BaseAsyncZMQServer.__init__(self, server_type, json_serializer=kwargs.get('json_serializer', None), 
                               rpc_serializer=kwargs.get('rpc_serializer', None))
        BaseAsyncZMQ.__init__(self)
        self.instance_name = instance_name
        self.create_socket(instance_name, context, identity=instance_name, bind=True, protocol=protocol, 
                        socket_type=socket_type, socket_address=kwargs.get("socket_address", None)) 
        self._terminate_context = context == None # terminate if it was created by instance


    async def async_recv_instruction(self) -> typing.Any:
        """
        Receive one instruction in a blocking form. Async for multi-server paradigm, each server should schedule
        this method in the event loop explicitly. This is taken care by the ``Eventloop`` & ``RPCServer``.   

        Returns
        -------
        instruction: List[bytes | Any]
            received instruction with important content (instruction, arguments, execution context) deserialized. 
        """
        while True:
            instruction = self.parse_client_message(await self.socket.recv_multipart())
            if instruction:
                self.logger.debug("received instruction from client '{}' with msg-ID '{}'".format(
                                        instruction[CM_INDEX_ADDRESS], instruction[CM_INDEX_MESSAGE_ID]))
                return instruction
        

    async def async_recv_instructions(self) -> typing.List[typing.Any]:
        """
        Receive all currently available instructions in blocking form. Async for multi-server paradigm, each server should schedule
        this method in the event loop explicitly. This is taken care by the ``Eventloop`` & ``RPCServer``. 

        Returns
        -------
        instructions: List[List[bytes | Any]]
            list of received instructions with important content (instruction, arguments, execution context) deserialized.
        """
        instructions = [await self.async_recv_instruction()]
        while True:
            try:
                instruction = self.parse_client_message(await self.socket.recv_multipart(zmq.NOBLOCK))
                if instruction:
                    self.logger.debug("received instruction from client '{}' with msg-ID '{}'".format(
                                            instruction[CM_INDEX_ADDRESS], instruction[CM_INDEX_MESSAGE_ID]))
                    instructions.append(instruction)
            except zmq.Again: 
                break 
        return instructions
    

    async def async_send_reply(self, original_client_message : typing.List[bytes], data : typing.Any) -> None:
        """
        Send reply for an instruction. 

        Parameters
        ----------
        original_client_message: List[bytes]
            original message so that the reply can be properly crafted and routed
        data: Any
            serializable data to be sent as reply

        Returns
        -------
        None
        """
        await self.socket.send_multipart(self.craft_reply_from_client_message(original_client_message, data))
        self.logger.debug("sent reply to client '{}' with msg-ID '{}'".format(original_client_message[CM_INDEX_ADDRESS], 
                                                                    original_client_message[CM_INDEX_MESSAGE_ID]))


    def exit(self) -> None:
        """
        closes socket and context, warns if any error occurs. 
        """
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
    Identical to AsyncZMQServer, except that instructions are received in non-blocking/polling form. 
    This server can be stopped from server side by calling ``stop_polling()`` unlike ``AsyncZMQServer`` which 
    cannot be stopped manually unless an instruction arrives.

    Parameters
    ----------
    instance_name: str
        ``instance_name`` of the RemoteObject which the server serves
    server_type: str
        server type metadata - currently not useful/important
    context: Optional, zmq.asyncio.Context
        ZeroMQ Context object to use. All sockets share this context. Automatically created when None is supplied.
    socket_type : zmq.SocketType, default zmq.ROUTER
        socket type of ZMQ socket, default is ROUTER (enables address based routing of messages)
    protocol: Enum, default ZMQ_PROTOCOLS.IPC
        Use TCP for network access, IPC for multi-process applications, and INPROC for multi-threaded applications.  
    poll_timeout: int, default 25
        time in milliseconds to poll the sockets specified under ``procotols``. Useful for calling ``stop_polling()``
        where the max delay to stop polling will be ``poll_timeout``
  
    **kwargs:
        json_serializer: hololinked.server.serializers.JSONSerializer
            serializer used to send message to HTTP Server
        rpc_serializer: any of hololinked.server.serializers.serializer, default serpent
            serializer used to send message to RPC clients
    """

    def __init__(self, instance_name : str, *, server_type : Enum, context : typing.Union[zmq.asyncio.Context, None] = None, 
                socket_type : zmq.SocketType = zmq.ROUTER, protocol : ZMQ_PROTOCOLS = ZMQ_PROTOCOLS.IPC, 
                poll_timeout = 25, **kwargs) -> None:
        super().__init__(instance_name=instance_name, server_type=server_type, context=context, protocol=protocol,
                        socket_type=socket_type, **kwargs)
      
        self.poller = zmq.asyncio.Poller()
        self.poller.register(self.socket, zmq.POLLIN)
        self.poll_timeout = poll_timeout

    @property
    def poll_timeout(self) -> int:
        """
        socket polling timeout in milliseconds greater than 0. 
        """
        return self._poll_timeout

    @poll_timeout.setter
    def poll_timeout(self, value) -> None:
        if not isinstance(value, int) or value < 0:
            raise ValueError("polling period must be an integer greater than 0, not {}. Value is considered in milliseconds.".format(value))
        self._poll_timeout = value 

    async def poll_instructions(self) -> typing.List[typing.List[bytes]]:
        """
        poll for instructions with specified timeout (``poll_timeout``) and return if any instructions are available.
        This method blocks, so make sure other methods are scheduled which can stop polling. 

        Returns
        -------
        instructions: List[List[bytes]]
            list of received instructions with important content (instruction, arguments, execution context) deserialized.
        """
        self.stop_poll = False
        instructions = []
        while not self.stop_poll:
            sockets = await self.poller.poll(self._poll_timeout) # type hints dont work in this line
            for socket, _ in sockets:
                while True:
                    try:
                        instruction = self.parse_client_message(await socket.recv_multipart(zmq.NOBLOCK), socket)
                    except zmq.Again:
                        break
                    else:
                        if instruction:
                            self.logger.debug("received instruction from client '{}' with msg-ID '{}'".format(instruction[0], 
                                                                                                                instruction[4]))
                            instructions.append(instruction)
            if len(instructions) > 0:
                break
        return instructions

    def stop_polling(self) -> None:
        """
        stop polling and unblock ``poll_instructions()`` method
        """
        self.stop_poll = True 

    def exit(self) -> None:
        """
        unregister socket from poller and terminate socket and context.
        """
        try:
            self.poller.unregister(self.socket)
        except Exception as ex:
            self.logger.warn(f"suppressing exception while closing socket {self.identity} - {str(ex)}")
        return super().exit()
        


class ZMQServerPool(BaseZMQServer):
    """
    Implements pool of async ZMQ servers (& their sockets)
    """

    def __init__(self, instance_names : typing.Union[typing.List[str], None] = None, **kwargs) -> None:
        self.context = zmq.asyncio.Context()
        self.pool = dict() # type: typing.Dict[str, typing.Union[AsyncZMQServer, AsyncPollingZMQServer]]
        self.poller = zmq.asyncio.Poller()
        if instance_names:
            for instance_name in instance_names:
                self.pool[instance_name] = AsyncZMQServer(instance_name, ServerTypes.UNKNOWN_TYPE.value, self.context, 
                                                        **kwargs)
            for server in self.pool.values():
                self.poller.register(server.socket, zmq.POLLIN)
        super().__init__(server_type = ServerTypes.POOL.value, json_serializer = kwargs.get('json_serializer'), 
                    rpc_serializer = kwargs.get('rpc_serializer', None))

    def register_server(self, server : typing.Union[AsyncZMQServer, AsyncPollingZMQServer]) -> None:
        self.pool[server.instance_name] = server 
        self.poller.register(server.socket, zmq.POLLIN)

    def deregister_server(self, server : typing.Union[AsyncZMQServer, AsyncPollingZMQServer]) -> None:
        self.poller.unregister(server.socket)
        self.pool.pop(server.instance_name)

    @property
    def poll_timeout(self) -> int:
        """
        socket polling timeout in milliseconds greater than 0. 
        """
        return self._poll_timeout

    @poll_timeout.setter
    def poll_timeout(self, value) -> None:
        if not isinstance(value, int) or value < 0:
            raise ValueError("polling period must be an integer greater than 0, not {}. Value is considered in milliseconds.".format(value))
        self._poll_timeout = value 

    async def async_recv_instruction(self, instance_name : str) -> typing.List:
        """
        receive instruction for instance name

        Parameters
        ----------
        instance_name : str
            instance name of the ``RemoteObject`` or in this case, the ZMQ server. 
        """
        return await self.pool[instance_name].async_recv_instruction()
     
    async def async_recv_instructions(self, instance_name : str) -> typing.List[typing.List]:
        """
        receive all available instructions for instance name

        Parameters
        ----------
        instance_name : str
            instance name of the ``RemoteObject`` or in this case, the ZMQ server. 
        """
        return await self.pool[instance_name].async_recv_instructions()
   
    async def async_send_reply(self, instance_name : str, original_client_message : typing.List[bytes],  
                               data : typing.Any) -> None:
        """
        send reply for instance name

        Parameters
        ----------
        instance_name : str
            instance name of the ``RemoteObject`` or in this case, the ZMQ server. 
        original_client_message: List[bytes]
            instruction for which reply is being given
        data: Any
            data to be given as reply
        """
        await self.pool[instance_name].async_send_reply(original_client_message, data)
    
    async def poll(self) -> typing.List[typing.List[typing.Any]]:
        """
        Pool for instruction in the entire server pool. Map the instruction to the correct instance 
        using the 0th index of the instruction.  
        """
        self.stop_poll = False
        instructions = []
        while not self.stop_poll:
            sockets = await self.poller.poll(self._poll_timeout) 
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
        """
        stop polling method ``poll()``
        """
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

    def __getitem__(self, key) -> typing.Union[AsyncZMQServer, AsyncPollingZMQServer]:
        return self.pool[key]
    
    def __iter__(self) -> typing.Iterator[str]:
        return self.pool.__iter__()
    
    def __contains__(self, name : str) -> bool:
        return name in self.pool.keys()
    


class RPCServer(BaseZMQServer):
    """
    Top level ZMQ RPC server used by ``RemoteObject`` and ``Eventloop``. 

    Parameters
    ----------
    instance_name: str
        ``instance_name`` of the RemoteObject which the server serves
    server_type: str
        server type metadata - currently not useful/important
    context: Optional, zmq.asyncio.Context
        ZeroMQ Context object to use. All sockets share this context. Automatically created when None is supplied.
    protocols: List[str, Enum], default [ZMQ_PROTOCOLS.TCP, ZMQ_PROTOCOLS.IPC, ZMQ_PROTOCOLS.INPROC]
        all ZeroMQ sockets where instructions can be passed to the RPC server. Use TCP for network access,
        IPC for multi-process applications, and INPROC for multi-threaded applications. Use all for complete access. 
    poll_timeout: int, default 25
        time in milliseconds to poll the sockets specified under ``procotols``. Useful for calling ``stop_polling()``
        where the max delay to stop polling will be ``poll_timeout``
    """

    def __init__(self, instance_name : str, *, server_type : Enum, context : typing.Union[zmq.asyncio.Context, None] = None, 
                protocols : typing.List[ZMQ_PROTOCOLS] = [ZMQ_PROTOCOLS.TCP, ZMQ_PROTOCOLS.IPC, ZMQ_PROTOCOLS.INPROC], 
                poll_timeout = 25, **kwargs) -> None:
        super().__init__(server_type, kwargs.get('json_serializer', None), kwargs.get('rpc_serializer', None))
        kwargs["json_serializer"] = self.json_serializer
        kwargs["rpc_serializer"] = self.rpc_serializer
        self.context = context or zmq.asyncio.Context()
        self.poller = zmq.asyncio.Poller()
        if ZMQ_PROTOCOLS.TCP in protocols or "TCP" in protocols:
            self.tcp_server = AsyncPollingZMQServer(instance_name=instance_name, server_type=server_type, 
                                    context=self.context, protocol=ZMQ_PROTOCOLS.TCP, poll_timeout=poll_timeout, **kwargs)
            self.poller.register(self.tcp_server.socket)
        if ZMQ_PROTOCOLS.IPC in protocols or "IPC" in protocols: 
            self.ipc_server = AsyncPollingZMQServer(instance_name=instance_name, server_type=server_type, 
                                    context=self.context, protocol=ZMQ_PROTOCOLS.IPC, poll_timeout=poll_timeout, **kwargs)
            self.poller.register(self.ipc_server.socket)
        if ZMQ_PROTOCOLS.INPROC in protocols or "INPROC" in protocols: 
            self.inproc_server = AsyncPollingZMQServer(instance_name=instance_name, server_type=server_type, 
                                    context=self.context, protocol=ZMQ_PROTOCOLS.INPROC, poll_timeout=poll_timeout, **kwargs)
            self.poller.register(self.inproc_server.socket)
        self.poll_timeout = poll_timeout
        self.inproc_client = AsyncZMQClient(server_instance_name=f'{instance_name}/inner', identity=f'{instance_name}/tunneler',
                                client_type=TUNNELER, context=self.context, protocol=ZMQ_PROTOCOLS.INPROC, handshake=False)
        self._instructions = deque() # type: typing.Iterable[typing.Tuple[typing.List[bytes], asyncio.Event, asyncio.Future, zmq.Socket]]
        self._instructions_event = asyncio.Event()
        self.identity = f"{instance_name}/rpc-server"
        self.logger = self.get_logger(instance_name, 'RPC', 'MIXED')


    async def handshake_complete(self):
        """
        handles inproc client's handshake with ``RemoteObject``'s inproc server
        """
        await self.inproc_client.handshake_complete()


    def prepare(self):
        """
        registers socket polling method and message tunnelling methods to the running 
        asyncio event loop
        """
        eventloop = asyncio.get_event_loop()
        eventloop.call_soon(lambda : asyncio.create_task(self.poll()))
        eventloop.call_soon(lambda : asyncio.create_task(self.tunnel_message_to_remote_objects()))


    @property
    def poll_timeout(self) -> int:
        """
        socket polling timeout in milliseconds greater than 0. 
        """
        return self._poll_timeout

    @poll_timeout.setter
    def poll_timeout(self, value) -> None:
        if not isinstance(value, int) or value < 0:
            raise ValueError(("polling period must be an integer greater than 0, not {}.",
                              "Value is considered in milliseconds.".format(value)))
        self._poll_timeout = value 

    
    def _get_timeout_from_instruction(self, message : typing.Tuple[bytes]) -> float:
        """
        Unlike ``parse_client_message()``, this method only retrieves the timeout parameter
        """
        client_type = message[CM_INDEX_CLIENT_TYPE]
        if client_type == PROXY:
            return self.rpc_serializer.loads(message[CM_INDEX_TIMEOUT]) 
        elif client_type == HTTP_SERVER:
            return self.json_serializer.loads(message[CM_INDEX_TIMEOUT])
       

    async def poll(self):
        """
        poll for instructions and append them to instructions list to pass them to ``Eventloop``/``RemoteObject``'s inproc 
        server using an inner inproc client. Registers the messages for timeout calculation.
        """
        self.stop_poll = False
        eventloop = asyncio.get_event_loop()
        self.inproc_client.handshake()
        await self.inproc_client.handshake_complete()
        while not self.stop_poll:
            sockets : typing.Tuple[zmq.Socket, int] = await self.poller.poll(self._poll_timeout) # type
            for socket, _ in sockets:
                while True:
                    try:
                        original_instruction = await socket.recv_multipart(zmq.NOBLOCK)
                        if original_instruction[CM_INDEX_MESSAGE_TYPE] == HANDSHAKE:
                            handshake_task = asyncio.create_task(self._handshake(original_instruction, socket))
                            eventloop.call_soon(lambda : handshake_task)
                        timeout = self._get_timeout_from_instruction(original_instruction)
                        ready_to_process_event = None
                        timeout_task = None
                        if timeout is not None:
                            ready_to_process_event = asyncio.Event()
                            timeout_task = asyncio.create_task(self.process_timeouts(original_instruction, 
                                                        ready_to_process_event, timeout, socket))
                            eventloop.call_soon(lambda : timeout_task)
                    except zmq.Again:
                        break
                    except Exception as ex:
                        # handle invalid message
                        self.logger.error(f"exception occurred for message id {original_instruction[CM_INDEX_MESSAGE_ID]} - {str(ex)}")
                        invalid_message_task = asyncio.create_task(self._handle_invalid_message(original_instruction,
                                                                                        ex, socket))
                        eventloop.call_soon(lambda: invalid_message_task)
                    else:
                        self._instructions.append((original_instruction, ready_to_process_event, 
                                                                    timeout_task, socket))
                    
                        # print("instruction in RPC", original_instruction)
            self._instructions_event.set()
           

    async def tunnel_message_to_remote_objects(self):
        """
        message tunneler between external sockets and interal inproc client
        """
        while not self.stop_poll:
            if len(self._instructions) > 0:
                message, ready_to_process_event, timeout_task, origin_socket = self._instructions.popleft()
                timeout = True 
                if ready_to_process_event is not None: 
                    ready_to_process_event.set()
                    timeout = await timeout_task
                    # print("timeout result - ", timeout)
                if ready_to_process_event is None or not timeout:
                    original_address = message[CM_INDEX_ADDRESS]
                    message[CM_INDEX_ADDRESS] = self.inproc_client.server_address # replace address
                    # print("original address", original_address, "inproc address", message[0])
                    await self.inproc_client.socket.send_multipart(message)
                    # print("*********sent message to inproc")
                    reply = await self.inproc_client.socket.recv_multipart()
                    # print("--------received message from inproc")
                    reply[SM_INDEX_ADDRESS] = original_address
                    await origin_socket.send_multipart(reply)
                    # print("###### sent message to client")
            else:
                await self._instructions_event.wait()
                self._instructions_event.clear()
        

    async def process_timeouts(self, original_client_message : typing.List, ready_to_process_event : asyncio.Event,
                               timeout : typing.Optional[float], origin_socket : zmq.Socket) -> bool:
        """
        replies timeout to client if timeout occured and prevents the instruction from being executed. 
        """
        try:
            await asyncio.wait_for(ready_to_process_event.wait(), timeout)
            return False 
        except TimeoutError:    
            await origin_socket.send_multipart(self.craft_reply_from_arguments(original_client_message[CM_INDEX_ADDRESS], 
                original_client_message[CM_INDEX_CLIENT_TYPE], TIMEOUT, original_client_message[CM_INDEX_MESSAGE_ID]))
            return True

    async def _handle_invalid_message(self, original_client_message: builtins.list[builtins.bytes], exception: builtins.Exception,
                                    originating_socket : zmq.Socket) -> None:
        await originating_socket.send_multipart(self.craft_reply_from_arguments(
                            original_client_message[CM_INDEX_ADDRESS], original_client_message[CM_INDEX_CLIENT_TYPE], 
                            INVALID_MESSAGE, original_client_message[CM_INDEX_MESSAGE_ID], exception))
    
    async def _handshake(self, original_client_message: builtins.list[builtins.bytes],
                                    originating_socket : zmq.Socket) -> None:
        await originating_socket.send_multipart(self.craft_reply_from_arguments(
                original_client_message[CM_INDEX_ADDRESS], 
                original_client_message[CM_INDEX_CLIENT_TYPE], HANDSHAKE, original_client_message[CM_INDEX_MESSAGE_ID],
                EMPTY_BYTE))

    def exit(self):
        self.stop_poll = True
        sockets = list(self.poller._map.keys())
        for i in range(len(sockets)): # iterating over keys will cause dictionary size change during iteration
            self.poller.unregister(sockets[i])
        try:
            self.inproc_server.exit()
            self.ipc_server.exit()
            self.tcp_server.exit()
            self.inproc_client.exit()
        except:
            pass 
        self.context.term()
        self.logger.info("terminated context of socket '{}' of type '{}'".format(self.identity, self.__class__))

    
       
class BaseZMQClient(BaseZMQ):
    """    
    Base class for all ZMQ clients irrespective of sync and async.

    server's reply to client
    ::
        [address, bytes(), server type , message_type, message id, content or response or reply]
        [   0   ,   1    ,    2        ,     3       ,     4     ,            5                ]

    Parameters
    ----------
    server_instance_name: str
        The instance name of the server (or ``RemoteObject``)
   client_type: str
        RPC or HTTP Server
    **kwargs:
        rpc_serializer: 
            custom implementation of RPC serializer if necessary
        json_serializer:
            custom implementation of JSON serializer if necessary

    """

    def __init__(self, server_instance_name : str, client_type : bytes, **kwargs) -> None:
        if client_type in [PROXY, HTTP_SERVER, TUNNELER]: 
            self.client_type = client_type
        else:
            raise ValueError("Invalid client type for {}. Given option {}.".format(self.__class__, client_type)) 
        self.rpc_serializer = None
        self.json_serializer = None
        if client_type == HTTP_SERVER:
            json_serializer = kwargs.get("json_serializer", None)
            if json_serializer is None or isinstance(json_serializer, JSONSerializer):
                self.json_serializer = json_serializer or JSONSerializer()
            else:
                raise ValueError("Invalid JSON serializer option for {}. Given option {}.".format(self.__class__, 
                                                                                            json_serializer))
        elif client_type == PROXY: 
            rpc_serializer = kwargs.get("rpc_serializer", None)
            if rpc_serializer is None or isinstance(rpc_serializer, (PickleSerializer, SerpentSerializer, 
                                                                            JSONSerializer)): #, DillSerializer)): 
                self.rpc_serializer = rpc_serializer or SerpentSerializer()
            elif isinstance(rpc_serializer, str) and rpc_serializer in serializers.keys():
                self.rpc_serializer = serializers[rpc_serializer]()
            else:
                raise ValueError("invalid proxy serializer option for {}. Given option {}.".format(self.__class__, 
                                                                                            rpc_serializer))
        if server_instance_name:
            self.server_address = bytes(server_instance_name, encoding='utf-8')
        self.server_instance_name = server_instance_name
        self.server_type = ServerTypes.UNKNOWN_TYPE.value
        super().__init__()


    def raise_local_exception(exception : typing.Dict[str, typing.Any]) -> None:
        """
        raises an exception on client side using an exception from server by mapping it to the correct one based on type.

        Parameters
        ----------
        exception: Dict[str, Any]
            exception dictionary made by server with following keys - type, message, traceback, notes

        Raises
        ------
        python exception based on type. If not found in builtins 
        """
        exc = getattr(builtins, exception["type"], None)
        message = f"server raised exception, check following for server side traceback & above for client side traceback : "
        if exc is None:
            ex = Exception(message)
        else: 
            ex = exc(message)
        ex.__notes__ = exception["traceback"]
        raise ex from None 


    def parse_server_message(self, message : typing.List[bytes], raise_client_side_exception : bool = False) -> typing.Any:
        """
        server's message to client: 

        ::
            [address, bytes(), server type , message_type, message id, content or response or reply]
            [   0   ,   1    ,    2        ,     3     ,       4     ,            5                ]

        Parameters
        ----------
        message: List[bytes]
            message sent be server
        raise_client_side_exception: bool
            raises exception from server on client
        
        Raises
        ------
        """
       
        message_type = message[SM_INDEX_MESSAGE_TYPE]
        if message_type == REPLY:
            if self.client_type == HTTP_SERVER:
                message[SM_INDEX_DATA] = self.json_serializer.loads(message[SM_INDEX_DATA]) # type: ignore
            elif self.client_type == PROXY:
                message[SM_INDEX_DATA] = self.rpc_serializer.loads(message[SM_INDEX_DATA]) # type: ignore
            return message 
        elif message_type == HANDSHAKE:
            self.logger.debug("""handshake messages arriving out of order are silently dropped as receiving this message 
                means handshake was successful before. Received hanshake from {}""".format(message[0]))
        elif message_type == INVALID_MESSAGE:
            if self.client_type == HTTP_SERVER:
                message[SM_INDEX_DATA] = self.json_serializer.loads(message[SM_INDEX_DATA]) # type: ignore
            elif self.client_type == PROXY:
                message[SM_INDEX_DATA] = self.rpc_serializer.loads(message[SM_INDEX_DATA]) # type: ignore
            self.raise_local_exception(message)
            # if message[SM_INDEX_DATA].get('exception', None) is not None and raise_client_side_exception:
            #      self.raise_local_exception(message[SM_INDEX_DATA]['exception'])
        else:
            raise NotImplementedError("Unknown message type {} received. This message cannot be dealt.".format(message_type))


    def craft_instruction_from_arguments(self, instruction : str, arguments : typing.Dict[str, typing.Any] = EMPTY_DICT, 
                timeout : typing.Optional[float] = None, context : typing.Dict[str, typing.Any] = EMPTY_DICT) -> typing.List[bytes]: 
        """
        message from client to server:

        ::
            [address, bytes(), client type, message type, message id, instruction, arguments]
            [ 0     ,   1    ,     2      ,      3      ,       4   ,    5       ,     6    ]

        """
        message_id = bytes(str(uuid4()), encoding='utf-8')
        if self.client_type == HTTP_SERVER:
            timeout : bytes = self.json_serializer.dumps(timeout)
            instruction : bytes = self.json_serializer.dumps(instruction)
            # if arguments == b'':
            #     arguments : bytes = self.json_serializer.dumps({}) 
            # elif not isinstance(arguments, bytes):
            arguments : bytes = self.json_serializer.dumps(arguments) 
            context : bytes = self.json_serializer.dumps(context)
        elif self.client_type == PROXY:
            timeout : bytes = self.rpc_serializer.dumps(timeout)
            instruction : bytes = self.rpc_serializer.dumps(instruction)
            arguments : bytes = self.rpc_serializer.dumps(arguments) 
            context : bytes = self.rpc_serializer.dumps(context)
              
        return [
            self.server_address, 
            EMPTY_BYTE,
            self.client_type,
            INSTRUCTION,
            message_id,
            timeout, 
            instruction,
            arguments,
            context
        ]


    def craft_empty_message_with_type(self, message_type : bytes = HANDSHAKE):
        """
        create handshake message, ignores 
        """
        return [
            self.server_address,
            EMPTY_BYTE,
            self.client_type,
            message_type,
            EMPTY_BYTE,
            EMPTY_BYTE,
            EMPTY_BYTE,
            EMPTY_BYTE,
            EMPTY_BYTE
        ]


class SyncZMQClient(BaseZMQClient, BaseSyncZMQ):
    """
    Synchronous ZMQ client that connect with sync or async server based on ZMQ protocol. Works like REQ-REP socket. 
    Each request is blocking until response is received. Suitable for most purposes. 

    Parameters
    ----------
    server_instance_name: str
        The instance name of the server (or ``RemoteObject``)
    identity: str 
        Unique identity of the client to receive messages from the server. Each client connecting to same server must 
        still have unique ID. 
    client_type: str
        RPC or HTTP Server
    handshake: bool
        when true, handshake with the server first before allowing first message and block until that handshake was
        accomplished.
    protocol: str | Enum, TCP, IPC or INPROC, default IPC 
        protocol implemented by the server 
    **serializer:
        rpc_serializer: 
            custom implementation of RPC serializer if necessary
        json_serializer:
            custom implementation of JSON serializer if necessary
    """

    def __init__(self, server_instance_name : str, identity : str, client_type = HTTP_SERVER, 
                handshake : bool = True, protocol : str = "IPC", context : typing.Union[zmq.asyncio.Context, None] = None, 
                **serializer) -> None:
        BaseZMQClient.__init__(self, server_instance_name=server_instance_name, 
                            client_type=client_type, **serializer)
        BaseSyncZMQ.__init__(self)
        self.create_socket(server_instance_name, context, identity=identity, protocol=protocol)
        self._terminate_context = context == None
        if handshake:
            self.handshake()
    
    def send_instruction(self, instruction : str, arguments : typing.Dict[str, typing.Any] = EMPTY_DICT, 
                        timeout : typing.Optional[float] = None, context : typing.Dict[str, typing.Any] = EMPTY_DICT) -> bytes:
        """
        send message to server. 

        client's message to server:
        ::
            [address, bytes(), client type, message type, messsage id, 
            [   0   ,   1    ,     2      ,      3      ,      4     , 
            
            timeout, instruction, arguments, execution context] 
               5   ,      6     ,     7    ,       8          ]

        Execution Context Definitions (typing.Dict[str, typing.Any] or JSON):
            - "plain_reply" - does not return state 
            - "fetch_execution_logs" - fetches logs that were accumulated while execution

        Parameters
        ----------
        instruction: str
            unique str identifying a server side or ``RemoteObject`` resource. These values corresponding 
            to automatically extracted name from the object name or the URL_path prepended with the instance name. 
        arguments: Dict[str, Any]
            if the instruction invokes a method, arguments of that method. 
        context: Dict[str, Any]
            see execution context definitions

        Returns
        -------
        message id : bytes
            a byte representation of message id
        """
        message = self.craft_instruction_from_arguments(instruction, arguments, timeout, context)
        self.socket.send_multipart(message)
        self.logger.debug("sent instruction '{}' to server '{}' with msg-id {}".format(instruction, 
                                                    self.server_instance_name, message[SM_INDEX_MESSAGE_ID]))
        return message[SM_INDEX_MESSAGE_ID]
    
    def recv_reply(self, raise_client_side_exception : bool = False) -> typing.List[typing.Union[
                                                                            bytes, typing.Dict[str, typing.Any]]]:
        """
        Receives reply from server. Messages are identified by message id, so call this method immediately after 
        calling ``send_instruction()`` to avoid receiving messages out of order. Or, use other methods like
        ``execute()``, ``read_attribute()`` or ``write_attribute()``.

        Parameters
        ----------
        raise_client_side_exception: bool, default False
            if True, any exceptions raised during execution inside ``RemoteObject`` instance will be raised on the client.
            See docs of ``raise_local_exception()`` for info on exception 
        """
        while True:
            reply = self.parse_server_message(self.socket.recv_multipart(), raise_client_side_exception) # type: ignore
            if reply:
                self.logger.debug("received reply with msg-id {}".format(reply[SM_INDEX_MESSAGE_ID]))
                return reply
                
    def execute(self, instruction : str, arguments : typing.Dict[str, typing.Any] = EMPTY_DICT, 
                    context : typing.Dict[str, typing.Any] = EMPTY_DICT, raise_client_side_exception : bool = False
                ) -> typing.List[typing.Union[bytes, typing.Dict[str, typing.Any]]]:
        """
        send an instruction and receive the reply for it. 

        Parameters
        ----------
        instruction: str
            unique str identifying a server side or ``RemoteObject`` resource. These values corresponding 
            to automatically extracted name from the object name or the URL_path prepended with the instance name. 
        arguments: Dict[str, Any]
            if the instruction invokes a method, arguments of that method. 
        context: Dict[str, Any]
            see execution context definitions

        Returns
        -------
        message id : bytes
            a byte representation of message id
        """
        self.send_instruction(instruction, arguments, context)
        return self.recv_reply(raise_client_side_exception)
    

    def handshake(self) -> None: 
        """
        hanshake with server
        """
        poller = zmq.Poller()
        poller.register(self.socket, zmq.POLLIN)
        while True:
            self.socket.send_multipart(self.create_empty_message_with_type(HANDSHAKE))
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
                        self.server_type = message[SM_INDEX_SERVER_TYPE]
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
                handshake : bool = True, protocol : str = "IPC", context : typing.Union[zmq.asyncio.Context, None] = None, 
                **serializer) -> None:
        BaseZMQClient.__init__(self, server_instance_name=server_instance_name, client_type=client_type, **serializer)
        BaseAsyncZMQ.__init__(self)
        self.create_socket(instance_name=server_instance_name, context=context, identity=identity, protocol=protocol)
        self._terminate_context = context == None
        self._handshake_event = asyncio.Event()
        if handshake:
            self.handshake()
    
    def handshake(self) -> None:
        """
        automatically called when handshake argument at init is True. When not automatically called, it is necessary
        to call this method before awaiting ``handshake_complete()``.
        """
        run_method_somehow(self._handshake())

    async def _handshake(self) -> None:
        """
        inner method that performs handshake with server
        """
        self._handshake_event.clear()
        poller = zmq.asyncio.Poller()
        poller.register(self.socket, zmq.POLLIN)
        while True:
            await self.socket.send_multipart(self.craft_empty_message_with_type(HANDSHAKE))
            self.logger.debug("sent handshake to server - '{}'".format(self.server_instance_name))
            if await poller.poll(500):
                try:
                    msg = await self.socket.recv_multipart(zmq.NOBLOCK)
                except zmq.Again:
                    pass 
                else:
                    if msg[SM_INDEX_MESSAGE_TYPE] == HANDSHAKE: 
                        self.logger.info("client '{}' handshook with server '{}'".format(self.identity, self.server_instance_name))
                        self.server_type = msg[SM_INDEX_SERVER_TYPE]
                        break
                    else:
                        self.logger.info("handshake cannot be done with server '{}'. another message arrived before handshake complete.".format(
                            self.server_instance_name))
        poller.unregister(self.socket)
        self._handshake_event.set()
        del poller
    
    async def handshake_complete(self):
        """
        wait for handshake to complete
        """
        await self._handshake_event.wait()
       
    async def async_send_instruction(self, instruction : str, arguments : typing.Dict[str, typing.Any] = EMPTY_DICT, 
                    timeout : typing.Optional[float] = None, context : typing.Dict[str, typing.Any] = EMPTY_DICT) -> bytes:
        """
        send message to server. 

        client's message to server:
        ::
            [address, bytes(), client type, message type, messsage id, 
            [   0   ,   1    ,     2      ,      3      ,      4     , 
            
            timeout, instruction, arguments, execution context] 
               5   ,      6     ,     7    ,       8          ]

        Execution Context Definitions (typing.Dict[str, typing.Any] or JSON):
            - "plain_reply" - does not return state 
            - "fetch_execution_logs" - fetches logs that were accumulated while execution

        Parameters
        ----------
        instruction: str
            unique str identifying a server side or ``RemoteObject`` resource. These values corresponding 
            to automatically extracted name from the object name or the URL_path prepended with the instance name. 
        arguments: Dict[str, Any]
            if the instruction invokes a method, arguments of that method. 
        context: Dict[str, Any]
            see execution context definitions

        Returns
        -------
        message id : bytes
            a byte representation of message id
        """
        message = self.craft_instruction_from_arguments(instruction, arguments, timeout, context) 
        await self.socket.send_multipart(message)
        self.logger.debug("sent instruction '{}' to server '{}' with msg-id {}".format(instruction, 
                                                            self.server_instance_name, message[SM_INDEX_MESSAGE_ID]))
        return message[SM_INDEX_MESSAGE_ID]
    
    async def async_recv_reply(self, raise_client_side_exception : bool) -> typing.List[typing.Union[bytes, 
                                                                                    typing.Dict[str, typing.Any]]]:
        """
        Receives reply from server. Messages are identified by message id, so call this method immediately after 
        calling ``send_instruction()`` to avoid receiving messages out of order. Or, use other methods like
        ``execute()``, ``read_attribute()`` or ``write_attribute()``.

        Parameters
        ----------
        raise_client_side_exception: bool, default False
            if True, any exceptions raised during execution inside ``RemoteObject`` instance will be raised on the client.
            See docs of ``raise_local_exception()`` for info on exception 
        """
        while True:
            reply = self.parse_server_message(await self.socket.recv_multipart(), raise_client_side_exception)# [2] # type: ignore
            if reply:
                self.logger.debug("received reply with message-id {}".format(reply[SM_INDEX_MESSAGE_ID]))
                return reply
            
    async def async_execute(self, instruction : str, arguments : typing.Dict[str, typing.Any] = EMPTY_DICT, 
                        context : typing.Dict[str, typing.Any] = EMPTY_DICT, raise_client_side_exception = False): 
        """
        send an instruction and receive the reply for it. 

        Parameters
        ----------
        instruction: str
            unique str identifying a server side or ``RemoteObject`` resource. These values corresponding 
            to automatically extracted name from the object name or the URL_path prepended with the instance name. 
        arguments: Dict[str, Any]
            if the instruction invokes a method, arguments of that method. 
        context: Dict[str, Any]
            see execution context definitions

        Returns
        -------
        message id : bytes
            a byte representation of message id
        """
        await self.async_send_instruction(instruction, arguments, context)
        return await self.async_recv_reply(raise_client_side_exception)
    
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

    

class MessageMappedZMQClientPool(BaseZMQClient):
    """
    Pool of clients where message ID can track the replies irrespective of order of arrival. 
    """

    def __init__(self, server_instance_names: typing.List[str], identity: str, poll_timeout = 25, 
                protocol : str = 'IPC', client_type = HTTP_SERVER, **serializer) -> None:
        self.identity = identity 
        self.logger = self.get_logger(identity, 'pooled', logging.DEBUG)
        # this class does not call create_socket method
        super().__init__(server_instance_name=None, client_type=client_type, **serializer)
        self.context = zmq.asyncio.Context()
        self.pool = dict() # type: typing.Dict[str, AsyncZMQClient]
        for instance_name in server_instance_names:
            self.pool[instance_name] = AsyncZMQClient(server_instance_name=instance_name,
                identity=identity, client_type=client_type, handshake=True, protocol=protocol, 
                context=self.context, rpc_serializer=self.rpc_serializer, json_serializer=self.json_serializer)
        self.poller = zmq.asyncio.Poller()
        for client in self.pool.values():
            self.poller.register(client.socket, zmq.POLLIN)
        # Both the client pool as well as the individual client get their serializers and client_types
        # This is required to implement pool level sending and receiving messages like polling of pool of sockets
        self.event_pool = AsyncioEventPool(len(server_instance_names))
        self.events_map = dict() # type: typing.Dict[bytes, asyncio.Event]
        self.message_map = dict()
        self.cancelled_messages = []
        self.poll_timeout = poll_timeout
        self.stop_poll = False 


    def create_new(self, server_instance_name : str, protocol : str = 'IPC') -> None:
        """
        Create new server with specified protocol. other arguments are taken from pool specifications. 
        
        Parameters
        ----------
        instance_name: str
            instance name of server 
        protocol: str
            protocol implemented by ZMQ server
        """
        if server_instance_name not in self.pool.keys():
            self.pool[server_instance_name] = AsyncZMQClient(server_instance_name=server_instance_name,
                identity = self.identity, client_type = self.client_type, handshake = True, protocol = protocol, 
                context = self.context, rpc_serializer = self.rpc_serializer, json_serializer = self.json_serializer)
        else: 
            raise ValueError(f"client for instance name {server_instance_name} already present in pool")


    @property
    def poll_timeout(self) -> int:
        """
        socket polling timeout in milliseconds greater than 0. 
        """
        return self._poll_timeout

    @poll_timeout.setter
    def poll_timeout(self, value) -> None:
        if not isinstance(value, int) or value < 0:
            raise ValueError("polling period must be an integer greater than 0, not {}. Value is considered in milliseconds".format(value))
        self._poll_timeout = value 


    async def poll(self) -> None:
        """
        Poll for replies from server. Since the client is message mapped, this method should be independently started
        in the event loop. Sending message and retrieving a message mapped is still carried out by other methods.
        """
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
                        # errors in handle_message should reach the client. 
                        break
                    else:
                        if reply:
                            address, _, server_type, message_type, message_id, data = reply
                            self.logger.debug("received reply from server '{}' with message ID {}".format(address, message_id))
                            if message_id in self.cancelled_messages:
                                self.cancelled_messages.remove(message_id)
                                self.logger.debug(f'message_id {message_id} cancelled')
                                continue
                            try:
                                event = self.events_map[message_id] 
                            except KeyError:
                                invalid_event_task = asyncio.create_task(self._resolve_reply(message_id, data))
                                event_loop.call_soon(lambda: invalid_event_task)
                            else:    
                                self.message_map[message_id] = data
                                event.set()


    async def _resolve_reply(self, message_id : bytes, data : typing.Any) -> None:
        """
        This method is called when there is an asyncio Event not available for a message ID. This can happen only 
        when the server replied before the client created a asyncio.Event object. check ``async_execute()`` for details.

        Parameters
        ----------
        message_id: bytes 
            the message for which the event was not created
        data: bytes
            the data given by the server which needs to mapped to the message
        """
        max_number_of_retries = 100
        for i in range(max_number_of_retries):
            await asyncio.sleep(0.025)
            try:
                event = self.events_map[message_id]
            except KeyError:
                if message_id in self.cancelled_messages:
                    # Only for safety, likely should never reach here
                    self.cancelled_messages.remove(message_id)
                    self.logger.debug(f'message_id {message_id} cancelled')
                    return 
                if i >= max_number_of_retries - 1:
                    self.logger.error("unknown message id {} without corresponding event object".format(message_id)) 
                    # print(return_value)
                    return
            else:    
                self.message_map[message_id] = data
                event.set()
                break


    async def async_send_instruction(self, instance_name : str, instruction : str, 
                arguments : typing.Dict[str, typing.Any] = EMPTY_DICT, timeout : typing.Optional[float] = 3,
                context : typing.Dict[str, typing.Any] = EMPTY_DICT) -> bytes:
        """
        Send instruction to server with instance name. Replies are automatically polled & to be retrieved using 
        ``async_recv_reply()``

        Parameters
        ----------
        instance_name: str
            instance name of the server
        instruction: str
            unique str identifying a server side or ``RemoteObject`` resource. These values corresponding 
            to automatically extracted name from the object name or the URL_path prepended with the instance name. 
        arguments: Dict[str, Any]
            if the instruction invokes a method, arguments of that method. 
        context: Dict[str, Any]
            see execution context definitions

        Returns
        -------
        message_id: bytes
            created message ID
        """
        message_id = await self.pool[instance_name].async_send_instruction(instruction, arguments, timeout, context)
        event = self.event_pool.pop()
        self.events_map[message_id] = event 
        return message_id

    async def async_recv_reply(self, message_id : bytes, plain_reply : bool = False, raise_client_side_exception = False,
                        timeout : typing.Optional[float] = None) -> typing.Dict[str, typing.Any]:
        """
        Receive reply for specified message ID. 

        Parameters
        ----------
        message_id: bytes
            the message id for which reply needs to eb fetched
        plain_reply: bool, default False
            strip reply of any other contents like state machine state
        raise_client_side_exceptions: bool, default False
            raise exceptions from server on client side
        timeout: float, 
            client side timeout, not the same as timeout passed to server, recommended to be None in general cases. 
            Server side timeouts ensure start of execution of instructions within specified timeouts and 
            drops execution altogether if timeout occured. Client side timeouts only wait for message to come within 
            the timeout, but do not gaurantee non-execution.  

        Returns
        -------
        reply: dict, Any
            dictionary when plain reply is False, any value returned from execution on the server side if plain reply is
            True.

        Raises
        ------
        ValueError: 
            if supplied message id is not valid
        TimeoutError:
            if timeout is not None and reply did not arrive
        """
        try:
            event = self.events_map[message_id]
        except KeyError:
            raise ValueError(f"message id {message_id} unknown.") from None
        try:
            await asyncio.wait_for(event.wait(), timeout if (timeout and timeout > 0) else None)
        except TimeoutError:
            self.cancelled_messages.append(message_id)
            self.logger.debug(f'message_id {message_id} added to list of cancelled messages')
            raise TimeoutError(f"Execution not completed within {timeout} seconds") from None
        else:
            self.events_map.pop(message_id)
            reply = self.message_map.pop(message_id)
            self.event_pool.completed(event)
            if not plain_reply and reply.get('exception', None) is not None and raise_client_side_exception:
                exc_info = reply['exception']
                raise Exception("traceback : {},\nmessage : {},\ntype : {}".format (
                                '\n'.join(exc_info["traceback"]), exc_info['message'], exc_info["type"]))
            return reply

    async def async_execute(self, instance_name : str, instruction : str, arguments : typing.Dict[str, typing.Any] = EMPTY_DICT, 
                    context : typing.Dict[str, typing.Any] = EMPTY_DICT, raise_client_side_exception = False, 
                    server_timeout : typing.Optional[float] = 3, client_timeout : typing.Optional[float] = None) -> typing.Dict[str, typing.Any]:
        """
        sends message and receives reply.

        Parameters
        ----------
        instance_name: str
            instance name of the server
        instruction: str
            unique str identifying a server side or ``RemoteObject`` resource. These values corresponding 
            to automatically extracted name from the object name or the URL_path prepended with the instance name. 
        arguments: Dict[str, Any]
            if the instruction invokes a method, arguments of that method. 
        context: Dict[str, Any]
            see execution context definitions
        raise_client_side_exceptions: bool, default False
            raise exceptions from server on client side
        server_timeout: float, default 3 
            server side timeout
        client_timeout: float, default None
            client side timeout, not the same as timeout passed to server, recommended to be None in general cases. 
            Server side timeouts ensure start of execution of instructions within specified timeouts and 
            drops execution altogether if timeout occured. Client side timeouts only wait for message to come within 
            the timeout, but do not gaurantee non-execution.  

        """
        message_id = await self.async_send_instruction(instance_name, instruction, arguments, server_timeout, context)
        return await self.async_recv_reply(message_id, False, raise_client_side_exception, client_timeout)

    def start_polling(self) -> None:
        """
        register the server message polling loop in the asyncio event loop. 
        """
        event_loop = asyncio.get_event_loop()
        event_loop.call_soon(lambda: asyncio.create_task(self.poll()))

    async def stop_polling(self):
        """
        stop polling for replies from server
        """
        self.stop_poll = True

    # async def ping_all_servers(self):
    #     """
    #     ping all servers connected to the client pool
    #     """
    #     replies = await asyncio.gather(*[self.async_execute(
    #         instance_name, '/ping') for instance_name in self.pool.keys()]) # type: typing.List[typing.Dict[str, typing.Any]]
    #     sorted_reply = dict() 
    #     for reply, instance_name in zip(replies, self.pool.keys()):
    #         sorted_reply[instance_name] = reply.get("returnValue", False if reply.get("exception", None) is None else True)  # type: ignore
    #     return sorted_reply

    # def organised_gathered_replies(self, instance_names : List[str], gathered_replies : List[Any], context : Dict[str, Any] = EMPTY_DICT):
    #     """
    #     First thing tomorrow
    #     """
    #     plain_reply = context.pop('plain_reply', False)
    #     if not plain_reply:
    #         replies = dict(
    #             returnValue = dict(),
    #             state = dict()
    #         )
    #         for  instance_name, reply in zip(instance_names, gathered_replies):
    #             replies["state"].update(reply["state"])
    #             replies["returnValue"][instance_name] = reply.get("returnValue", reply.get("exception", None))
    #     else: 
    #         replies = {}
    #         for instance_name, reply in zip(instance_names, gathered_replies):
    #             replies[instance_name] = reply
    #     return replies  

    # async def async_execute_in_all(self, instruction : str, arguments : Dict[str, Any] = EMPTY_DICT, 
    #                     context : Dict[str, Any] = EMPTY_DICT, raise_client_side_exception = False) -> Dict[str, Any]:
    #     instance_names = self.pool.keys()
    #     gathered_replies = await asyncio.gather(*[
    #         self.async_execute(instance_name, instruction, arguments, context, raise_client_side_exception) for instance_name in instance_names])
    #     return self.organised_gathered_replies(instance_names, gathered_replies, context)
    
    # async def async_execute_in_all_remote_objects(self, instruction : str, arguments : Dict[str, Any] = EMPTY_DICT,
    #                             context : Dict[str, Any] = EMPTY_DICT, raise_client_side_exception = False) -> Dict[str, Any]:
    #     instance_names = [instance_name for instance_name, client in self.pool.items() if client.server_type == ServerTypes.USER_REMOTE_OBJECT]
    #     gathered_replies = await asyncio.gather(*[
    #         self.async_execute(instance_name, instruction, arguments, context, raise_client_side_exception) for instance_name in instance_names])
    #     return self.organised_gathered_replies(instance_names, gathered_replies, context)
    
    # async def async_execute_in_all_eventloops(self, instruction : str, arguments : Dict[str, Any] = EMPTY_DICT, 
    #                     context : Dict[str, Any] = EMPTY_DICT, raise_client_side_exception = False) -> Dict[str, Any]:
    #     instance_names = [instance_name for instance_name, client in self.pool.items() if client.server_type == ServerTypes.EVENTLOOP]
    #     gathered_replies = await asyncio.gather(*[
    #         self.async_execute(instance_name, instruction, arguments, context, raise_client_side_exception) for instance_name in instance_names])
    #     return self.organised_gathered_replies(instance_names, gathered_replies, context)
    
    def __contains__(self, name : str) -> bool:
        return name in self.pool

    def __getitem__(self, key) ->AsyncZMQClient:
        return self.pool[key]
    
    def __iter__(self) -> typing.Iterator[AsyncZMQClient]:
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


class AsyncioEventPool:
    """
    creates a pool of asyncio Events to be used as a synchronisation object for MessageMappedClientPool

    Parameters
    ----------
    initial_number_of_events: int
        initial pool size of events
    """

    def __init__(self, initial_number_of_events : int) -> None:
        self.pool = [asyncio.Event() for i in range(initial_number_of_events)] 
        self.size = initial_number_of_events

    def pop(self) -> asyncio.Event:
        """
        pop an event, new one is created if nothing left in pool
        """
        try:
            event = self.pool.pop(0)
        except IndexError:
            self.size += 1
            event = asyncio.Event()
        event.clear()
        return event

    def completed(self, event : asyncio.Event) -> None:
        """
        put an event back into the pool
        """
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

    def __init__(self,  identity : str, context : typing.Union[zmq.Context, None] = None, **serializer) -> None:
        super().__init__(server_type=ServerTypes.UNKNOWN_TYPE.value, **serializer)
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
                self.logger = self.get_logger(identity, "PUB", "TCP", logging.DEBUG)
                self.logger.info("created event publishing socket at {}".format(self.socket_address))
                break
        self.events = set() # type: typing.Set[Event] 
        self.event_ids = set() # type: typing.Set[bytes]

    def register_event(self, event : Event) -> None:
        # unique_str_bytes = bytes(unique_str, encoding = 'utf-8') 
        if event._unique_event_name in self.events:
            raise AttributeError(wrap_text(
                """event {} already found in list of events, please use another name. 
                Also, Remotesubobject and RemoteObject cannot share event names.""".format(event.name))
            )
        self.event_ids.add(event._unique_event_name)
        self.events.add(event) 
        self.logger.info("registered event '{}' serving at PUB socket with address : {}".format(event.name, self.socket_address))
               
    def publish_event(self, unique_str : bytes, data : typing.Any, serialize : bool = True) -> None: 
        if unique_str in self.event_ids:
            self.socket.send_multipart([unique_str, self.json_serializer.dumps(data) if serialize else data])
        else:
            raise AttributeError("event name {} not yet registered with socket {}".format(unique_str, self.socket_address))
        
    def exit(self):
        try:
            self.socket.close(0)
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
            self.socket.close(0)
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
            


__all__ = ['ServerTypes', 'AsyncZMQServer', 'AsyncPollingZMQServer', 'ZMQServerPool', 'RPCServer',
           'SyncZMQClient', 'AsyncZMQClient', 'MessageMappedZMQClientPool', 'Event', 'CriticalEvent']