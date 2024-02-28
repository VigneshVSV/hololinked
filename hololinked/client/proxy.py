import threading 
import asyncio
import typing 
import logging
import uuid
from typing import Any

from ..server.data_classes import RPCResource
from ..server.zmq_message_brokers import SyncZMQClient, EventConsumer, PROXY
from ..server.utils import current_datetime_ms_str
from ..server.constants import (SERIALIZABLE_WRAPPER_ASSIGNMENTS, Instructions, 
                            ServerMessage, ServerMessageData, ResourceType)

from ..server.zmq_message_brokers import (CM_INDEX_ADDRESS, CM_INDEX_ARGUMENTS, CM_INDEX_CLIENT_TYPE, CM_INDEX_EXECUTION_CONTEXT,
                        CM_INDEX_INSTRUCTION, CM_INDEX_MESSAGE_ID, CM_INDEX_MESSAGE_TYPE, CM_INDEX_TIMEOUT)
from ..server.zmq_message_brokers import (SM_INDEX_ADDRESS, SM_INDEX_DATA, SM_INDEX_MESSAGE_ID, SM_INDEX_MESSAGE_TYPE, 
                        SM_INDEX_SERVER_TYPE)

class ObjectProxy:

    _own_attrs = frozenset([
        '_zmq_client', 'identity', '__annotations__',
        'instance_name', 'logger', 'timeout', '_timeout', 
        '_events'
    ])

    def __init__(self, instance_name : str, timeout : float = 5, load_remote_object = True, protocol : str = 'TCP', **kwargs) -> None:
        self.instance_name = instance_name
        self.timeout = timeout
        self.identity = f"{instance_name}|{uuid.uuid4()}"
        self.logger = logging.Logger(self.identity)
        # compose ZMQ client in Proxy client so that all sending and receiving is
        # done by the ZMQ client and not by the Proxy client directly. Proxy client only 
        # bothers mainly about __setattr__ and _getattr__
        self._zmq_client = SyncZMQClient(instance_name, self.identity, client_type=PROXY, protocol=protocol, **kwargs)
        if load_remote_object:
            self.load_remote_object()

    def __del__(self):
        self._zmq_client.exit()

    def __getattribute__(self, __name: str) -> Any:
        obj = super().__getattribute__(__name)
        if isinstance(obj, _RemoteParameter):
            return obj.get()
        return obj

    def __setattr__(self, __name : str, __value : typing.Any):
        if __name in ObjectProxy._own_attrs or (__name not in self.__dict__ and isinstance(__value, __allowed_attribute_types__)):
            print(f"setting {__name}")
            return super(ObjectProxy, self).__setattr__(__name, __value)
        elif __name in self.__dict__:
            obj = self.__dict__[__name]
            if isinstance(obj, _RemoteParameter):
                obj.set(value=__value)
                return
            raise AttributeError(f"Cannot reset attribute {__name} again to ObjectProxy for {self.instance_name}.")
        raise AttributeError(f"Cannot set foreign attribute {__name} to ObjectProxy for {self.instance_name}. Given attribute not found in RemoteObject.")

    def __repr__(self):
        return f'ObjectProxy {self.instance_name}'

    def __enter__(self):
        raise NotImplementedError("with statement is not completely implemented yet. Avoid.")
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        raise NotImplementedError("with statement is not completely implemented yet. Avoid.")
    
    def __bool__(self): return True

    def __eq__(self, other):
        if other is self:
            return True
        return isinstance(other, ObjectProxy) and other.instance_name == self.instance_name

    def __ne__(self, other):
        if other and isinstance(other, ObjectProxy):
            return other.instance_name != self.instance_name
        return True

    def __hash__(self):
        return hash(self.identity)
    
    @property
    def timeout(self) -> typing.Union[float, int]:
        return self._timeout 
    
    @timeout.setter
    def timeout(self, value : typing.Union[float, int]):
        if not isinstance(value, (float, int, type(None))):
            raise TypeError(f"Timeout can only be float or int greater than 0, or None. Given type {type(value)}.")
        elif value is not None and value < 0:
            raise ValueError("Timeout must be at least 0 or None, not negative.")
        self._timeout = value
    
    timeout.__doc__ = """Timeout in seconds on server side for execution of method. Defaults to 5 seconds and 
            network times not considered."""

    def invoke(self, method : str, oneway : bool = False, **kwargs) -> typing.Any:
        method = getattr(self, method, None) # type: _RemoteMethod 
        if not isinstance(method, _RemoteMethod):
            raise AttributeError(f"No remote method named {method}")
        if oneway:
            method.oneway(**kwargs)
        else:
            return method(**kwargs)

    async def async_invoke(self, method : str, **kwargs):
        method = getattr(self, method, None) # type: _RemoteMethod 
        if not isinstance(method, _RemoteMethod):
            raise AttributeError(f"No remote method named {method}")
        return await method.async_call(**kwargs)

    def set_parameter(self, parameter : str, value : typing.Any, oneway : bool) -> None:
        parameter = getattr(self, parameter, None) # type: _RemoteParameter
        if not isinstance(parameter, _RemoteParameter):
            raise AttributeError(f"No remote parameter named {parameter}")
        if oneway:
            parameter.oneway(value)
        else:
            parameter.set(value)

    async def async_set_parameters(self, oneway : bool = False, noblock : bool = False, **parameters):
        pass 

    def subscribe_event(self, event_name : str, callback : typing.Callable):
        event = getattr(self, event_name, None) # type: _Event
        if not isinstance(event, _Event):
            raise AttributeError(f"No event named {event_name}")
        if event._subscribed:
            event._cbs.append(callback)
            return self._events.
        else: 
            event._subscribe([callback])
            self._events[uuid.uuid4()] = event

    def unsubscribe_event(self, event_name : str):
        event = getattr(self, event_name, None) # type: _Event
        if not isinstance(event, _Event):
            raise AttributeError(f"No event named {event_name}")
        event._unsubscribe()

    
    def load_remote_object(self):
        """
        Get metadata from server (methods, parameters...) and remember them in some attributes of the proxy.
        Usually this will already be known due to the default behavior of the connect handshake, where the
        connect response also includes the metadata.
        """
        fetch = _RemoteMethod(self._zmq_client, f'/{self.instance_name}{Instructions.RPC_RESOURCES}', 
                                    self._timeout) # type: _RemoteMethod
        reply = fetch()[ServerMessage.DATA][ServerMessageData.RETURN_VALUE] # type: typing.Dict[str, typing.Dict[str, typing.Any]]

        allowed_events = []
        for name, data in reply.items():
            if isinstance(data, dict):
                data = RPCResource(**data)
            elif not isinstance(data, RPCResource):
                raise RuntimeError("Logic error - desieralized info about server not instance of ProxyResourceData")
            if data.what == ResourceType.CALLABLE:
                _add_method(self, _RemoteMethod(self._zmq_client, data.instruction, self.timeout), data)
            elif data.what == ResourceType.PARAMETER:
                _add_parameter(self, _RemoteParameter(self._zmq_client, data.instruction, self.timeout), data)
            elif data.what == ResourceType.EVENT:
                _add_event(self, _Event(self._zmq_client, data.event_name, data.event_socket), data)
        self._events = {}

 

class _RemoteMethod:
    """method call abstraction"""

    def __init__(self, client : SyncZMQClient, instruction : str, timeout : typing.Optional[float] = None) -> None:
        self._zmq_client = client
        self._instruction = instruction
        self._timeout = timeout
        self._loop = asyncio.get_event_loop()
    
    @property # i.e. cannot have setter
    def last_return_value(self):
        return self._last_return_value
    
    def oneway(self, *args, **kwargs) -> None:
        kwargs["__args__"] = args 
        self._zmq_client.send_instruction(self._instruction, kwargs, self._timeout)

    def __call__(self, *args, **kwargs) -> typing.Any:
        kwargs["__args__"] = args 
        self._last_return_value = self._zmq_client.execute(self._instruction, 
                                        kwargs, raise_client_side_exception=True)
        return self._last_return_value
    
    async def async_call(self, *args, **kwargs):
        pass       
    

    
class _RemoteParameter:
    """parameter set & get abstraction"""

    def __init__(self, client : SyncZMQClient, instruction : str, 
                                timeout : typing.Optional[float] = None) -> None:
        self._zmq_client = client
        self._timeout = timeout
        self._read_instruction = instruction + '/read'
        self._write_instruction = instruction + '/write'

    def __del__(self):
        self._zmq_client = None 

    @property # i.e. cannot have setter
    def last_value(self):
        return self._last_value
    
    def set(self, value : typing.Any) -> typing.Any:
        self._last_value : typing.Dict = self._zmq_client.execute(self._write_instruction, dict(value=value),
                                                        raise_client_side_exception=True)
     
    def get(self):
        self._last_value : typing.Dict = self._zmq_client.execute(self._read_instruction,
                                                raise_client_side_exception=True)
        return self._last_value[SM_INDEX_DATA]
    
    async def async_set(self, value : typing.Any) -> typing.Any:
        self._last_value : typing.Dict = await self._zmq_client.execute(self._write_instruction, dict(value=value),
                                                        raise_client_side_exception=True)
    
    async def async_get(self):
        self._last_value : typing.Dict = await self._zmq_client.execute(self._read_instruction,
                                                raise_client_side_exception=True)
        return self._last_value
    
    def oneway(self):
        pass
  


class _Event:
    """event streaming"""

    def __init__(self, client : SyncZMQClient, event_name : str, event_socket : str) -> None:
        self._zmq_client = client 
        self._name = event_name
        self._URL = event_name
        self._socket_address = event_socket

    def _subscribe(self, callbacks : typing.List[typing.Callable]):
        self._event_consumer = EventConsumer(self._URL, self._socket_address, 
                                f"{self._socket_address}_HTTPEvent@"+current_datetime_ms_str())
        self._cbs = callbacks 
        self._subscribed = True
        self._thread = threading.Thread(target=self.listen)
        self._thread.start()

    def listen(self):
        while self._subscribed:
            try:
                data = self._event_consumer.receive_event(deserialize=True)
                for cb in self._cbs: 
                    cb(data)
            except Exception as E:
                print(E)
        self._event_consumer.exit()

    def _unsubscribe(self):
        self._subscribed = False



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



__allowed_attribute_types__ = (_RemoteParameter, _RemoteMethod)

def _add_method(client_obj : ObjectProxy, method : _RemoteMethod, func_info : RPCResource) -> None:
    if not func_info.top_owner:
        return
    for dunder in SERIALIZABLE_WRAPPER_ASSIGNMENTS:
        if dunder == '__qualname__':
            info = '{}.{}'.format(client_obj.__class__.__name__, func_info.get_dunder_attr(dunder).split('.')[1])
        else:
            info = func_info.get_dunder_attr(dunder)
        setattr(method, dunder, info)
    client_obj.__setattr__(func_info.name, method)

def _add_parameter(client_obj : ObjectProxy, parameter : _RemoteParameter, parameter_info : RPCResource) -> None:
    if not parameter_info.top_owner:
        return
    for attr in ['doc', 'name']: 
        # just to imitate _add_method logic
        setattr(parameter, attr, getattr(parameter_info, attr))
    client_obj.__setattr__(parameter_info.name, parameter)

def _add_event(client_obj : ObjectProxy, event : _Event, event_info) -> None:
    client_obj.__setattr__(event.name)


__all__ = ['ObjectProxy']

