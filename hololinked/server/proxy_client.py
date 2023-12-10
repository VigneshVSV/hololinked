import threading 
import asyncio
import typing 
import logging
from typing import Any

from .zmq_message_brokers import SyncZMQClient, EventConsumer, PROXY
from .utils import current_datetime_ms_str, raise_local_exception
from .constants import PARAMETER, SERIALIZABLE_WRAPPER_ASSIGNMENTS, FUNC, CALLABLE, ATTRIBUTE, EVENT
from .data_classes import ProxyResourceData



SingleLevelNestedJSON = typing.Dict[str, typing.Dict[str, typing.Any]]



class ObjectProxy:

    __own_attrs__ = frozenset([
        '_client', '_client_ID', '__annotations__',
        'instance_name', 'logger', 'timeout', '_timeout', 
    ])

    def __init__(self, instance_name : str, timeout : float = 5, load_remote_object = True, **kwargs) -> None:
        self.instance_name = instance_name
        self._client_ID = instance_name+current_datetime_ms_str()
        self.logger = logging.Logger(self._client_ID)
        self.timeout = timeout
        # compose ZMQ client in Proxy client so that all sending and receiving is
        # done by the ZMQ client and not by the Proxy client directly. Proxy client only 
        # bothers mainly about __setattr__ and _getattr__
        self._client = SyncZMQClient(instance_name, self._client_ID, client_type=PROXY, **kwargs)
        if load_remote_object:
            self.load_remote_object()

    def __del__(self):
        self._client.exit()

    def __getattribute__(self, __name: str) -> Any:
        obj = super().__getattribute__(__name)
        if isinstance(obj, _RemoteParameter):
            return obj.get()
        return obj

    def __setattr__(self, __name : str, __value : typing.Any):
        if __name in ObjectProxy.__own_attrs__ or (__name not in self.__dict__ and isinstance(__value, __allowed_attribute_types__)):
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
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        raise NotImplementedError("with statement exit is not yet implemented. Avoid.")
    
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
        return hash(self._client_ID)
    
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
        method : _RemoteMethod = getattr(self, method, None)
        if not method:
            raise AttributeError(f"No remote method named {method}")
        if oneway:
            method.oneway(**kwargs)
        else:
            return method(**kwargs)

    async def async_invoke(self, method : str, **kwargs):
        method : _RemoteMethod = getattr(self, method, None)
        if not method:
            raise AttributeError(f"No remote method named {method}")
        return await method.async_call(**kwargs)

    def set_parameter(self, parameter : str, value : typing.Any, oneway : bool) -> None:
        parameter : _RemoteParameter = getattr(self, parameter, None)
        if not parameter:
            raise AttributeError(f"No remote parameter named {parameter}")
        if oneway:
            parameter.oneway(value)
        else:
            parameter.set(value)

    async def async_set_parameters(self, oneway : bool = False, noblock : bool = False, **parameters):
        pass 

    def subscribe_event(self, event_name : str, callback : typing.Callable):
        pass

    def unsubscribe_event(self, event_name : str):
        pass

    # def __getstate__(self):
    #     # make sure a tuple of just primitive types are used to allow for proper serialization
    #     return str(self._pyroUri), tuple(self._pyroOneway), tuple(self._pyroMethods), \
    #            tuple(self._pyroAttrs), self._pyroHandshake, self._pyroSerializer

    # def __setstate__(self, state):
    #     self._pyroUri = core.URI(state[0])
    #     self._pyroOneway = set(state[1])
    #     self._pyroMethods = set(state[2])
    #     self._pyroAttrs = set(state[3])
    #     self._pyroHandshake = state[4]
    #     self._pyroSerializer = state[5]
    #     self.__pyroTimeout = config.COMMTIMEOUT
    #     self._pyroMaxRetries = config.MAX_RETRIES
    #     self._pyroConnection = None
    #     self._pyroLocalSocket = None
    #     self._pyroSeq = 0
    #     self._pyroRawWireResponse = False
    #     self.__pyroOwnerThread = get_ident()

    # def __copy__(self):
    #     p = object.__new__(type(self))
    #     p.__setstate__(self.__getstate__())
    #     p._pyroTimeout = self._pyroTimeout
    #     p._pyroRawWireResponse = self._pyroRawWireResponse
    #     p._pyroMaxRetries = self._pyroMaxRetries
    #     return p


    # def __dir__(self):
    #     result = dir(self.__class__) + list(self.__dict__.keys())
    #     return sorted(set(result) | self._pyroMethods | self._pyroAttrs)

    # # When special methods are invoked via special syntax (e.g. obj[index] calls
    # # obj.__getitem__(index)), the special methods are not looked up via __getattr__
    # # for efficiency reasons; instead, their presence is checked directly.
    # # Thus we need to define them here to force (remote) lookup through __getitem__.
    
    # def __len__(self): return self.__getattr__('__len__')()
    # def __getitem__(self, index): return self.__getattr__('__getitem__')(index)
    # def __setitem__(self, index, val): return self.__getattr__('__setitem__')(index, val)
    # def __delitem__(self, index): return self.__getattr__('__delitem__')(index)

    # def __iter__(self):
    #     try:
    #         # use remote iterator if it exists
    #         yield from self.__getattr__('__iter__')()
    #     except AttributeError:
    #         # fallback to indexed based iteration
    #         try:
    #             yield from (self[index] for index in range(sys.maxsize))
    #         except (StopIteration, IndexError):
    #            return

    
    def load_remote_object(self):
        """
        Get metadata from server (methods, parameters...) and remember them in some attributes of the proxy.
        Usually this will already be known due to the default behavior of the connect handshake, where the
        connect response also includes the metadata.
        """
        fetch = _RemoteMethod(self._client, f'/{self.instance_name}/resources/object-proxy/read')
        reply : SingleLevelNestedJSON = fetch()[5]["returnValue"]

        for name, data in reply.items():
            data = ProxyResourceData(**data)
            if data.what == CALLABLE:
                _add_method(self, _RemoteMethod(self._client, data.instruction), data)
            elif data.what == ATTRIBUTE:
                _add_parameter(self, _RemoteParameter(self._client, data.instruction), data)
            elif data.what == EVENT:
                pass 
       
    # def _pyroInvokeBatch(self, calls, oneway=False):
    #     flags = protocol.FLAGS_BATCH
    #     if oneway:
    #         flags |= protocol.FLAGS_ONEWAY
    #     return self._pyroInvoke("<batch>", calls, None, flags)

  

class _RemoteMethod:
    """method call abstraction"""

    def __init__(self, client : SyncZMQClient, instruction : str) -> None:
        self._client = client
        self._instruction = instruction
        self._loop = asyncio.get_event_loop()
    
    def __del__(self):
        self._client = None # remove ref, as of now weakref is not used. 

    @property # i.e. cannot have setter
    def last_return_value(self):
        return self._last_return_value
    
    def oneway(self, *args, **kwargs) -> None:
        self._client.execute(self._instruction, kwargs)

    def __call__(self, *args, **kwargs) -> typing.Any:
        self._last_return_value : typing.Dict = self._client.execute(self._instruction, kwargs, 
                                                                raise_client_side_exception=True)
        return self._last_return_value
           
    async def async_call(self, *args, **kwargs) -> typing.Any:
        self._last_return_value : typing.Dict = self._client.execute(self._instruction, kwargs, 
                                                                raise_client_side_exception=True)
        return self._last_return_value

    
class _RemoteParameter:
    """parameter set & get abstraction"""

    def __init__(self, client : SyncZMQClient, instruction : str):
        self._client = client
        self._read_instruction = instruction + '/read'
        self._write_instruction = instruction + '/write'

    def __del__(self):
        self._client = None 

    @property # i.e. cannot have setter
    def last_value(self):
        return self._last_value
    
    def set(self, value : typing.Any) -> typing.Any:
        self._last_value : typing.Dict = self._client.execute(self._write_instruction, dict(value=value),
                                                        raise_client_side_exception=True)
     
    def get(self):
        self._last_value : typing.Dict = self._client.execute(self._read_instruction,
                                                raise_client_side_exception=True)
        return self._last_value
    
    async def async_set(self, value : typing.Any) -> typing.Any:
        self._last_value : typing.Dict = await self._client.execute(self._write_instruction, dict(value=value),
                                                        raise_client_side_exception=True)
    
    async def async_get(self):
        self._last_value : typing.Dict = await self._client.execute(self._read_instruction,
                                                raise_client_side_exception=True)
        return self._last_value
  

class _Event:
    """event streaming"""

    def __init__(self, client : SyncZMQClient, event_name : str, event_socket : str) -> None:
        self._client = client 
        self._event_name = event_name
        self._event_socket = event_socket

    def _subscribe(self, callback : typing.Callable):
        self._event_consumer = EventConsumer(request.path, event_info.socket_address, 
                                f"{request.path}_HTTPEvent@"+current_datetime_ms_str())
        self._cb = callback 
        self._subscribed = True
        self._thread = threading.Thread(target=self.listen)
        self._thread.start()

    def listen(self):
        while self._subscribed:
            try:
                data = self._event_consumer.receive_event(deserialize=True)
                self._cb(data)
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

def _add_method(client_obj : ObjectProxy, method : _RemoteMethod, func_info : ProxyResourceData) -> None:
    for dunder in SERIALIZABLE_WRAPPER_ASSIGNMENTS:
        if dunder == '__qualname__':
            info = '{}.{}'.format(client_obj.__class__.__name__, func_info.get_dunder_attr(dunder).split('.')[1])
        else:
            info = func_info.get_dunder_attr(dunder)
        setattr(method, dunder, info)
    client_obj.__setattr__(method.__name__, method)

def _add_parameter(client_obj : ObjectProxy, parameter : _RemoteParameter, parameter_info : ProxyResourceData) -> None:
    for attr in ['doc', 'name']: 
        # just to imitate _add_method logic
        setattr(parameter, attr, getattr(parameter_info, attr))
    client_obj.__setattr__(parameter_info.name, parameter)

def _add_event(client_obj : ObjectProxy, event, event_info) -> None:
    pass 


__all__ = ['ObjectProxy']

