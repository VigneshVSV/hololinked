import logging 
import typing 
import datetime
import threading
import asyncio
import time 
from collections import deque

from .constants import HTTP_METHODS
from .events import Event
from .property import Property
from .properties import Integer, Number
from .thing import Thing as RemoteObject
from .action import action as remote_method



class ListHandler(logging.Handler):
    """
    log history handler
    """

    def __init__(self, log_list : typing.Optional[typing.List] = None):
        super().__init__()
        self.log_list : typing.List[typing.Dict] = [] if not log_list else log_list
    
    def emit(self, record : logging.LogRecord):
        log_entry = self.format(record)
        self.log_list.insert(0, {
            'level' : record.levelname,
            'timestamp' : datetime.datetime.fromtimestamp(record.created).strftime("%Y-%m-%dT%H:%M:%S.%f"),
            'message' : record.msg
        })



class RemoteAccessHandler(logging.Handler, RemoteObject):
    """
    Log handler with remote access attached to ``Thing``'s logger if logger_remote_access is True.

    Parameters
    ----------
    maxlen: int, default 500
        history of log entries to store in RAM
    stream_interval: float, default 1.0
        when streaming logs using log-events endpoint, this value is the stream interval.
    """

    def __init__(self, instance_name : str = 'logger', maxlen : int = 500, stream_interval : float = 1.0, 
                    **kwargs) -> None:
        logging.Handler.__init__(self)
        RemoteObject.__init__(self, instance_name=instance_name, **kwargs)
        # self._last_time = datetime.datetime.now()
        self.stream_interval = stream_interval # datetime.timedelta(seconds=1.0) if not emit_interval else datetime.timedelta(seconds=emit_interval)
        self.maxlen = maxlen
        self.event = Event('log-events')
        self.diff_logs = []
        self._push_events = False
        self._events_thread = None

    stream_interval = Number(default=1.0, bounds=(0.01, 60.0), crop_to_bounds=True, step=0.01,
                        URL_path='/stream-interval', doc="interval at which logs should be published to a client.")
    
    def get_maxlen(self):
        return self._maxlen 
    
    def set_maxlen(self, value):
        self._maxlen = value
        self._debug_logs = deque(maxlen=value/5)
        self._info_logs = deque(maxlen=value/5)
        self._warn_logs = deque(maxlen=value/5)
        self._error_logs = deque(maxlen=value/5)
        self._critical_logs = deque(maxlen=value/5)
        self._execution_logs = deque(maxlen=value)

    maxlen = Integer(default=100, bounds=(1, None), crop_to_bounds=True, URL_path='/maxlen',
                fget=get_maxlen, fset=set_maxlen, doc="length of history to store")


    @remote_method(http_method=HTTP_METHODS.POST, URL_path='/events/start')
    def push_events(self, type : str = 'threaded', interval : float = 1):
        self.stream_interval = interval # datetime.timedelta(seconds=interval)
        self._push_events = True 
        if type == 'asyncio':
            asyncio.get_event_loop().call_soon(lambda : asyncio.create_task(self.async_push_diff_logs()))
        elif self._events_thread is not None:
            self._events_thread = threading.Thread(target=self.push_diff_logs)
            self._events_thread.start()

    @remote_method(http_method=HTTP_METHODS.POST, URL_path='/events/stop')
    def stop_events(self):
        self._push_events = False 
        if self._events_thread: # No need to cancel asyncio event separately 
            self._events_thread.join()
            self._events_thread = None
            self._owner.logger.debug(f"joined log event source with thread-id {self._events_thread.ident}")
    
    def emit(self, record : logging.LogRecord):
        log_entry = self.format(record)
        info = {
            'level' : record.levelname,
            'timestamp' : datetime.datetime.fromtimestamp(record.created).strftime("%Y-%m-%dT%H:%M:%S.%f"),
            'message' : record.msg
        }
        if record.levelno < logging.INFO:
            self._debug_logs.appendleft(info)
        elif record.levelno >= logging.INFO and record.levelno < logging.WARN:
            self._info_logs.appendleft(info)
        elif record.levelno >= logging.WARN and record.levelno < logging.ERROR:
            self._warn_logs.appendleft(info)
        elif record.levelno >= logging.ERROR and record.levelno < logging.CRITICAL:
            self._error_logs.appendleft(info)
        elif record.levelno >= logging.CRITICAL:
            self._critical_logs.appendleft(info)
        self._execution_logs.appendleft(info)

        if self._push_events: 
            self.diff_logs.insert(0, info)

    def push_diff_logs(self):
        while self._push_events:
            time.sleep(self.stream_interval)
            self.event.push(self.diff_logs) 
            self.diff_logs.clear()
        # give time to collect final logs with certainty
        self._owner.logger.info(f"ending log event source with thread-id {threading.get_ident()}")

    async def async_push_diff_logs(self):
        while self._push_events:
            await asyncio.sleep(self.stream_interval)
            self.event.push(self.diff_logs) 
            self.diff_logs.clear()
           
    debug_logs = Property(readonly=True, URL_path='/logs/debug', fget=lambda self: self._debug_logs,
                            doc="logs at logging.DEBUG level")
    
    warn_logs = Property(readonly=True, URL_path='/logs/warn', fget=lambda self: self._warn_logs,
                            doc="logs at logging.WARN level")
    
    info_logs = Property(readonly=True, URL_path='/logs/info', fget=lambda self: self._info_logs,
                            doc="logs at logging.INFO level")
       
    error_logs = Property(readonly=True, URL_path='/logs/error', fget=lambda self: self._error_logs,
                            doc="logs at logging.ERROR level")
 
    critical_logs = Property(readonly=True, URL_path='/logs/critical', fget=lambda self: self._critical_logs,
                            doc="logs at logging.CRITICAL level")
  
    execution_logs = Property(readonly=True, URL_path='/logs/execution', fget=lambda self: self._execution_logs,
                            doc="logs at all levels accumulated in order of collection/execution")
    


__all__ = [
    ListHandler.__name__, 
    RemoteAccessHandler.__name__
]