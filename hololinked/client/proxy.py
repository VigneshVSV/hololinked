import threading 
import warnings
import typing 
import logging
import uuid

from ..server.data_classes import RPCResource, ServerSentEvent
from ..server.zmq_message_brokers import AsyncZMQClient, SyncZMQClient, PROXY
from ..server.events import EventConsumer
from ..server.utils import current_datetime_ms_str
from ..server.constants import (JSON, CommonInstructions, 
                            ServerMessage, ServerMessageData, ResourceTypes)


__WRAPPER_ASSIGNMENTS__ =  ('__name__', '__qualname__', '__doc__')


class ObjectProxy:
    """
    Procedural client for ``RemoteObject``. Once connected to a server, parameters, methods and events are 
    dynamically populated. Any of the ZMQ protocols of the server is supported. 

    Parameters
    ----------
    instance_name: str
        instance name of the server
    invokation_timeout: float, int
        timeout to schedule a method call or parameter read/write in server. execution time wait is controlled by 
        ``execution_timeout``
    execution_timeout: float, int
        timeout to return without a reply after scheduling a method call or parameter read/write. 
    load_remote_object: bool, default True
        when True, remote object is located and its resources are loaded. 
    protocol: str
        ZMQ protocol used to connect to server. Unlike the server, only one can be specified.  
    **kwargs:
        asynch_mixin: bool, default False
            whether to use both synchronous and asynchronous clients. 
        serializer: BaseSerializer
            use a custom serializer, must be same as the serializer supplied to the server. 
        allow_foreign_attributes: bool, default False
            allows local attributes for proxy apart from parameters fetched from the server.
    """

    _own_attrs = frozenset([
        '_zmq_client', '_async_zmq_client', 'identity', '__annotations__', '_allow_foreign_attributes',
        'instance_name', 'logger', 'execution_timeout', 'invokation_timeout', '_execution_timeout', '_invokation_timeout', 
        '_events'
    ])

    def __init__(self, instance_name : str, protocol : str, invokation_timeout : float = 5, load_remote_object = True, 
                    **kwargs) -> None:
        self._allow_foreign_attributes = kwargs.get('allow_foreign_attributes', False)
        self.instance_name = instance_name
        self.invokation_timeout = invokation_timeout
        self.execution_timeout = kwargs.get("execution_timeout", None)
        self.identity = f"{instance_name}|{uuid.uuid4()}"
        self.logger = logging.Logger(self.identity)
        # compose ZMQ client in Proxy client so that all sending and receiving is
        # done by the ZMQ client and not by the Proxy client directly. Proxy client only 
        # bothers mainly about __setattr__ and _getattr__
        self._async_zmq_client = None    
        self._zmq_client = SyncZMQClient(instance_name, self.identity, client_type=PROXY, protocol=protocol, 
                                            rpc_serializer=kwargs.get('serializer', None), **kwargs)
        if kwargs.get("asynch_mixin", False):
            self._async_zmq_client = AsyncZMQClient(instance_name, self.identity, client_type=PROXY, protocol=protocol, 
                                            rpc_serializer=kwargs.get('serializer', None), **kwargs)
        if load_remote_object:
            self.load_remote_object()

    def __del__(self) -> None:
        if hasattr(self, '_zmq_client') and self._zmq_client:
            self._zmq_client.exit()
        if hasattr(self, '_async_zmq_client') and self._async_zmq_client:
            self._async_zmq_client.exit()

    def __getattribute__(self, __name: str) -> typing.Any:
        obj = super().__getattribute__(__name)
        if isinstance(obj, _RemoteParameter):
            return obj.get()
        return obj

    def __setattr__(self, __name : str, __value : typing.Any) -> None:
        if __name in ObjectProxy._own_attrs or (__name not in self.__dict__ and isinstance(__value, __allowed_attribute_types__)) or self._allow_foreign_attributes:
            # allowed attribute types are _RemoteParameter and _RemoteMethod defined after this class
            return super(ObjectProxy, self).__setattr__(__name, __value)
        elif __name in self.__dict__:
            obj = self.__dict__[__name]
            if isinstance(obj, _RemoteParameter):
                obj.set(value=__value)
                return
            raise AttributeError(f"Cannot set attribute {__name} again to ObjectProxy for {self.instance_name}.")
        raise AttributeError(f"Cannot set foreign attribute {__name} to ObjectProxy for {self.instance_name}. Given attribute not found in server object.")

    def __repr__(self) -> str:
        return f'ObjectProxy {self.instance_name}'

    def __enter__(self):
        raise NotImplementedError("with statement is not completely implemented yet. Avoid.")

    def __exit__(self, exc_type, exc_value, traceback):
        raise NotImplementedError("with statement is not completely implemented yet. Avoid.")
    
    def __bool__(self) -> bool: 
        try: 
            self._zmq_client.handshake(num_of_tries=10)
            return True
        except RuntimeError:
            return False

    def __eq__(self, other) -> bool:
        if other is self:
            return True
        return (isinstance(other, ObjectProxy) and other.instance_name == self.instance_name and 
                other._zmq_client.protocol == self._zmq_client.protocol)

    def __ne__(self, other) -> bool:
        if other and isinstance(other, ObjectProxy):
            return (other.instance_name != self.instance_name or 
                    other._zmq_client.protocol != self._zmq_client.protocol)
        return True

    def __hash__(self) -> int:
        return hash(self.identity)
    
    def get_invokation_timeout(self) -> typing.Union[float, int]:
        return self._invokation_timeout 
    
    def set_invokation_timeout(self, value : typing.Union[float, int]) -> None:
        if not isinstance(value, (float, int, type(None))):
            raise TypeError(f"Timeout can only be float or int greater than 0, or None. Given type {type(value)}.")
        elif value is not None and value < 0:
            raise ValueError("Timeout must be at least 0 or None, not negative.")
        self._invokation_timeout = value
    
    invokation_timeout = property(fget=get_invokation_timeout, fset=set_invokation_timeout,
                        doc="Timeout in seconds on server side for invoking a method or read/write parameter. \
                                Defaults to 5 seconds and network times not considered."
    )

    def get_execution_timeout(self) -> typing.Union[float, int]:
        return self._execution_timeout 
    
    def set_execution_timeout(self, value : typing.Union[float, int]) -> None:
        if not isinstance(value, (float, int, type(None))):
            raise TypeError(f"Timeout can only be float or int greater than 0, or None. Given type {type(value)}.")
        elif value is not None and value < 0:
            raise ValueError("Timeout must be at least 0 or None, not negative.")
        self._execution_timeout = value
    
    execution_timeout = property(fget=get_execution_timeout, fset=set_execution_timeout,
                        doc="Timeout in seconds on server side for execution of method or read/write parameter. \
                                Defaults to None (i.e. waits indefinitely until return) and network times not considered."
    )


    def invoke(self, method : str, oneway : bool = False, noblock : bool = False, 
                                *args, **kwargs) -> typing.Any:
        """
        call a method on the server by name string with positional and keyword 
        arguments.

        Parameters
        ----------
        method: str 
            name of the method
        oneway: bool, default False 
            only send an instruction to invoke the method but do not fetch the reply.
        noblock: bool, default False 
            request a method call but collect the reply later using a reply id

        Returns
        -------
        return value: Any 
            return value of the method call

        Raises
        ------
        AttributeError: 
            if no method with specified name found on the server
        """
        method = getattr(self, method, None) # type: _RemoteMethod 
        if not isinstance(method, _RemoteMethod):
            raise AttributeError(f"No remote method named {method}")
        if oneway:
            method.oneway(*args, **kwargs)
        elif noblock:
            return method.noblock(*args, **kwargs)
        else:
            return method(*args, **kwargs)


    async def async_invoke(self, method : str, *args, **kwargs) -> typing.Any:
        """
        async call a method on the server by name string with positional and keyword 
        arguments. noblock and oneway not supported for async calls. 

        Parameters
        ----------
        method: str 
            name of the method

        Returns
        -------
        return_value: Any 
            return value of the method call
        
        Raises
        ------
        AttributeError: 
            if no method with specified name found on the server
        RuntimeError:
            if asynch_mixin was False at ``__init__()`` - no asynchronous client was created
        """
        method = getattr(self, method, None) # type: _RemoteMethod 
        if not isinstance(method, _RemoteMethod):
            raise AttributeError(f"No remote method named {method}")
        return await method.async_call(*args, **kwargs)


    def set_parameter(self, name : str, value : typing.Any, oneway : bool = False, 
                        noblock : bool = False) -> None:
        """
        set parameter on server by name string with specified value. 

        Parameters
        ----------
        name: str
            name of the parameter
        value: Any 
            value of parameter to be set
        oneway: bool, default False 
            only send an instruction to set the parameter but do not fetch the reply.
            (whether set was successful or not)

        Raises
        ------
        AttributeError: 
            if no method with specified name found on the server
        """
        parameter = getattr(self, name, None) # type: _RemoteParameter
        if not isinstance(parameter, _RemoteParameter):
            raise AttributeError(f"No remote parameter named {parameter}")
        if oneway:
            parameter.oneway_set(value)
        elif noblock:
            return parameter.noblock_set(value)
        else:
            parameter.set(value)


    async def async_set_parameter(self, name : str, value : typing.Any) -> None:
        """
        async set parameter on server by name string with specified value. 

        Parameters
        ----------
        name: str 
            name of the parameter
        value: Any 
            value of parameter to be set
        
        Raises
        ------
        AttributeError: 
            if no method with specified name found on the server
        """
        parameter = getattr(self, name, None) # type: _RemoteParameter
        if not isinstance(parameter, _RemoteParameter):
            raise AttributeError(f"No remote parameter named {parameter}")
        await parameter.async_set(value)
    

    def get_parameter(self, name : str) -> None:
        """
        async get parameter on server by name string. 

        Parameters
        ----------
        name: str 
            name of the parameter

        Raises
        ------
        AttributeError: 
            if no method with specified name found on the server
        """
        parameter = getattr(self, name, None) # type: _RemoteParameter
        if not isinstance(parameter, _RemoteParameter):
            raise AttributeError(f"No remote parameter named {parameter}")
        return parameter.get()
    

    async def async_get_parameter(self, name : str) -> None:
        """
        async set parameter on server by name string with specified value. 

        Parameters
        ----------
        value: Any 
            value of parameter to be set
        
        Raises
        ------
        AttributeError: 
            if no method with specified name found on the server
        """
        parameter = getattr(self, parameter, None) # type: _RemoteParameter
        if not isinstance(parameter, _RemoteParameter):
            raise AttributeError(f"No remote parameter named {parameter}")
        return await parameter.async_get()


    def set_parameters(self, parameter : str, value : typing.Any, oneway : bool) -> None:
        parameter = getattr(self, parameter, None) # type: _RemoteParameter
        if not isinstance(parameter, _RemoteParameter):
            raise AttributeError(f"No remote parameter named {parameter}")
        if oneway:
            parameter.oneway_set(value)
        else:
            parameter.set(value)

    async def async_set_parameters(self, oneway : bool = False, noblock : bool = False, **parameters) -> None:
        parameter = getattr(self, parameter, None) # type: _RemoteParameter
        if not isinstance(parameter, _RemoteParameter):
            raise AttributeError(f"No remote parameter named {parameter}")
        if oneway:
            parameter.oneway(value)
        else:
            parameter.set(value)


    def subscribe_event(self, name : str, callbacks : typing.Union[typing.List[typing.Callable], typing.Callable],
                        thread_callbacks : bool = False) -> None:
        event = getattr(self, name, None) # type: _Event
        if not isinstance(event, _Event):
            raise AttributeError(f"No event named {name}")
        if event._subscribed:
            event.add_callbacks(callbacks)
        else: 
            event.subscribe(callbacks, thread_callbacks)
       
    def unsubscribe_event(self, name : str):
        event = getattr(self, name, None) # type: _Event
        if not isinstance(event, _Event):
            raise AttributeError(f"No event named {name}")
        event.unsubscribe()


    def load_remote_object(self):
        """
        Get exposed resources from server (methods, parameters, events) and remember them as attributes of the proxy.
        """
        fetch = _RemoteMethod(self._zmq_client, f'/{self.instance_name}{CommonInstructions.RPC_RESOURCES}', 
                                    self._invokation_timeout) # type: _RemoteMethod
        reply = fetch() # type: typing.Dict[str, typing.Dict[str, typing.Any]]

        allowed_events = []
        for name, data in reply.items():
            if isinstance(data, dict):
                try:
                    if data["what"] == ResourceTypes.EVENT:
                        data = ServerSentEvent(**data)
                    else:
                        data = RPCResource(**data)
                except Exception as ex:
                    ex.add_note("Did you correctly configure your serializer? " + 
                            "This part fails when serializer does not work with the instance_resources dictionary (especially recursive deserilization)."
                            + "The error message may not be related to serialization as well. Visit https://hololinked.readthedocs.io/en/latest/howto/index.html" ) 
                    raise ex from None
            elif not isinstance(data, (RPCResource, ServerSentEvent)):
                raise RuntimeError("Logic error - deserialized info about server not instance of hololinked.server.data_classes.RPCResource")
            if data.what == ResourceTypes.CALLABLE:
                _add_method(self, _RemoteMethod(self._zmq_client, data.instruction, self.invokation_timeout, 
                                                self.execution_timeout, data.argument_schema, self._async_zmq_client), data)
            elif data.what == ResourceTypes.PARAMETER:
                _add_parameter(self, _RemoteParameter(self._zmq_client, data.instruction, self.invokation_timeout,
                                                self.execution_timeout, self._async_zmq_client), data)
            elif data.what == ResourceTypes.EVENT:
                assert isinstance(data, ServerSentEvent)
                _add_event(self, _Event(self._zmq_client, data.name, data.unique_identifier, data.socket_address), data)
        self._events = {}



# SM = Server Message
SM_INDEX_ADDRESS = ServerMessage.ADDRESS.value
SM_INDEX_SERVER_TYPE = ServerMessage.SERVER_TYPE.value
SM_INDEX_MESSAGE_TYPE = ServerMessage.MESSAGE_TYPE.value
SM_INDEX_MESSAGE_ID = ServerMessage.MESSAGE_ID.value
SM_INDEX_DATA = ServerMessage.DATA.value
SM_DATA_RETURN_VALUE = ServerMessageData.RETURN_VALUE.value

class _RemoteMethod:
    """method call abstraction"""

    def __init__(self, sync_client : SyncZMQClient, instruction : str, invokation_timeout : typing.Optional[float] = 5, 
                    execution_timeout : typing.Optional[float] = None, argument_schema : typing.Optional[JSON] = None,
                    async_client : typing.Optional[AsyncZMQClient] = None) -> None:
        self._zmq_client = sync_client
        self._async_zmq_client = async_client
        self._instruction = instruction
        self._invokation_timeout = invokation_timeout
        self._execution_timeout = execution_timeout
        self._schema = argument_schema
        # self._loop = asyncio.get_event_loop()
    
    @property # i.e. cannot have setter
    def last_return_value(self):
        """
        cached return value of the last call to the method
        """
        return self._last_return_value[SM_INDEX_DATA][SM_DATA_RETURN_VALUE]
    
    def oneway(self, *args, **kwargs) -> None:
        """
        only issues the method call to the server and does not wait for reply,
        neither does the server reply to this call.  
        """
        if len(args) > 0: 
            kwargs["__args__"] = args
        self._zmq_client.send_instruction(self._instruction, kwargs, None, None, self._schema)

    def noblock(self, *args, **kwargs) -> None:
        pass 

    def __call__(self, *args, **kwargs) -> typing.Any:
        """
        execute method on server
        """
        if len(args) > 0: 
            kwargs["__args__"] = args
        self._last_return_value = self._zmq_client.execute(self._instruction, 
                                        kwargs, self._invokation_timeout, raise_client_side_exception=True,
                                        argument_schema=self._schema)
        return self._last_return_value[SM_INDEX_DATA][SM_DATA_RETURN_VALUE]
    
    async def async_call(self, *args, **kwargs):
        """
        async execute method on server
        """
        if not self._async_zmq_client:
            raise RuntimeError("async calls not possible as asynch_mixin was not set at __init__()")
        if len(args) > 0: 
            kwargs["__args__"] = args
        self._last_return_value = await self._async_zmq_client.async_execute(self._instruction, 
                                        kwargs, self._invokation_timeout, raise_client_side_exception=True,
                                        argument_schema=self._schema)
        return self._last_return_value[SM_INDEX_DATA][SM_DATA_RETURN_VALUE]

    
class _RemoteParameter:
    """parameter set & get abstraction"""

    def __init__(self, client : SyncZMQClient, instruction : str, invokation_timeout : typing.Optional[float] = 5, 
                    execution_timeout : typing.Optional[float] = None, async_client : typing.Optional[AsyncZMQClient] = None) -> None:
        self._zmq_client = client
        self._async_zmq_client = async_client
        self._invokation_timeout = invokation_timeout
        self._read_instruction = instruction + '/read'
        self._write_instruction = instruction + '/write'

    @property # i.e. cannot have setter
    def last_read_value(self) -> typing.Any:
        """
        cache of last read value
        """
        return self._last_value
    
    def set(self, value : typing.Any) -> None:
        self._last_value = self._zmq_client.execute(self._write_instruction, dict(value=value),
                                                        raise_client_side_exception=True)
     
    def get(self) -> typing.Any:
        self._last_value = self._zmq_client.execute(self._read_instruction, 
                                                timeout=self._invokation_timeout, 
                                                raise_client_side_exception=True)
        return self._last_value[SM_INDEX_DATA][SM_DATA_RETURN_VALUE]
    
    async def async_set(self, value : typing.Any) -> None:
        self._last_value = await self._async_zmq_client.async_execute(self._write_instruction, dict(value=value),
                                                        self._invokation_timeout, raise_client_side_exception=True)
    
    async def async_get(self) -> typing.Any:
        self._last_value = await self._async_zmq_client.async_execute(self._read_instruction,
                                                timeout=self._invokation_timeout, raise_client_side_exception=True)
        return self._last_value[SM_INDEX_DATA][SM_DATA_RETURN_VALUE]
    
    def oneway_set(self, value : typing.Any) -> None:
        self._zmq_client.send_instruction(self._instruction, dict(value=value))

    def noblock_set(self, value : typing.Any) -> None:
        pass 
  


class _Event:
    """event streaming"""

    def __init__(self, client : SyncZMQClient, name : str, unique_identifier : str, socket : str) -> None:
        self._zmq_client = client 
        self._name = name
        self._unique_identifier = bytes(unique_identifier, encoding='utf-8')
        self._socket_address = socket
        self._callbacks = None 

    def add_callbacks(self, callbacks : typing.Union[typing.List[typing.Callable], typing.Callable]) -> None:
        if not self._callbacks:
            self._callbacks = [] 
        if isinstance(callbacks, list):
            self._callbacks.extend(callbacks)
        else:
            self._callbacks.append(callbacks)

    def subscribe(self, callbacks : typing.Union[typing.List[typing.Callable], typing.Callable], 
                    thread_callbacks : bool = False):
        self._event_consumer = EventConsumer(self._unique_identifier, self._socket_address, 
                                f"{self._name}_RPCEvent@"+current_datetime_ms_str())
        self.add_callbacks(callbacks) 
        self._subscribed = True
        self._thread_callbacks = thread_callbacks
        self._thread = threading.Thread(target=self.listen)
        self._thread.start()

    def listen(self):
        while self._subscribed:
            try:
                data = self._event_consumer.receive_event(deserialize=True)
                for cb in self._callbacks: 
                    cb(data)
            except Exception as ex:
                warnings.warn(f"Uncaught exception - {str(ex)}", 
                                category=RuntimeWarning)
        self._event_consumer.exit()

    def unsubscribe(self, join_thread : bool = False):
        self._subscribed = False
        if join_thread:
            self._thread.join()



class _StreamResultIterator(object):
    """
    Pyro returns this as a result of a remote call which returns an iterator or generator.
    It is a normal iterable and produces elements on demand from the remote iterator.
    You can simply use it in for loops, list comprehensions etc.
    """
    def __init__(self, streamId, proxy):
        self.streamId = streamId
        self.proxy = proxy
        self.pyroseq = proxy._pyroSeq

    def __iter__(self):
        return self

    def __next__(self):
        if self.proxy is None:
            raise StopIteration
        if self.proxy._pyroConnection is None:
            raise errors.ConnectionClosedError("the proxy for this stream result has been closed")
        self.pyroseq += 1
        try:
            return self.proxy._pyroInvoke("get_next_stream_item", [self.streamId], {}, objectId=core.DAEMON_NAME)
        except (StopIteration, GeneratorExit):
            # when the iterator is exhausted, the proxy is removed to avoid unneeded close_stream calls later
            # (the server has closed its part of the stream by itself already)
            self.proxy = None
            raise

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    def close(self):
        if self.proxy and self.proxy._pyroConnection is not None:
            if self.pyroseq == self.proxy._pyroSeq:
                # we're still in sync, it's okay to use the same proxy to close this stream
                self.proxy._pyroInvoke("close_stream", [self.streamId], {},
                                       flags=protocol.FLAGS_ONEWAY, objectId=core.DAEMON_NAME)
            else:
                # The proxy's sequence number has diverged.
                # One of the reasons this can happen is because this call is being done from python's GC where
                # it decides to gc old iterator objects *during a new call on the proxy*.
                # If we use the same proxy and do a call in between, the other call on the proxy will get an out of sync seq and crash!
                # We create a temporary second proxy to call close_stream on. This is inefficient, but avoids the problem.
                with contextlib.suppress(errors.CommunicationError):
                    with self.proxy.__copy__() as closingProxy:
                        closingProxy._pyroInvoke("close_stream", [self.streamId], {},
                                                 flags=protocol.FLAGS_ONEWAY, objectId=core.DAEMON_NAME)
        self.proxy = None



__allowed_attribute_types__ = (_RemoteParameter, _RemoteMethod, _Event)

def _add_method(client_obj : ObjectProxy, method : _RemoteMethod, func_info : RPCResource) -> None:
    if not func_info.top_owner:
        return 
        raise RuntimeError("logic error")
    for dunder in __WRAPPER_ASSIGNMENTS__:
        if dunder == '__qualname__':
            info = '{}.{}'.format(client_obj.__class__.__name__, func_info.get_dunder_attr(dunder).split('.')[1])
        else:
            info = func_info.get_dunder_attr(dunder)
        setattr(method, dunder, info)
    client_obj.__setattr__(func_info.name, method)

def _add_parameter(client_obj : ObjectProxy, parameter : _RemoteParameter, parameter_info : RPCResource) -> None:
    if not parameter_info.top_owner:
        return
        raise RuntimeError("logic error")
    for attr in ['doc', 'name']: 
        # just to imitate _add_method logic
        setattr(parameter, attr, getattr(parameter_info, attr))
    client_obj.__setattr__(parameter_info.name, parameter)

def _add_event(client_obj : ObjectProxy, event : _Event, event_info) -> None:
    client_obj.__setattr__(event.name)


__all__ = ['ObjectProxy']

