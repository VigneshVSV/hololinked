import threading
import typing
import unittest
import multiprocessing 
import logging
import zmq.asyncio

from hololinked.server import Thing, action
from hololinked.client import ObjectProxy
from hololinked.server.eventloop import EventLoop



class TestThingRun(unittest.TestCase):

    def setUp(self):
        self.thing_cls = Thing 

    def test_thing_run_and_exit(self):
        # should be able to start and end with exactly the specified protocols
        done_queue = multiprocessing.Queue()
        multiprocessing.Process(target=start_thing, args=('test-run', ), kwargs=dict(done_queue=done_queue), 
                            daemon=True).start()
        thing_client = ObjectProxy('test-run', log_level=logging.WARN) # type: Thing
        self.assertEqual(thing_client.get_protocols(), ['IPC']) 
        thing_client.exit()
        self.assertEqual(done_queue.get(), 'test-run') 
        
        done_queue = multiprocessing.Queue()
        multiprocessing.Process(target=start_thing, args=('test-run-2', ['IPC', 'INPROC'],),
                                kwargs=dict(done_queue=done_queue), daemon=True).start()
        thing_client = ObjectProxy('test-run-2', log_level=logging.WARN) # type: Thing
        self.assertEqual(thing_client.get_protocols(), ['INPROC', 'IPC']) # order should reflect get_protocols() action
        thing_client.exit()
        self.assertEqual(done_queue.get(), 'test-run-2') 
        
        done_queue = multiprocessing.Queue()
        multiprocessing.Process(target=start_thing, args=('test-run-3', ['IPC', 'INPROC', 'TCP'], 'tcp://*:60000'), 
                                kwargs=dict(done_queue=done_queue), daemon=True).start()
        thing_client = ObjectProxy('test-run-3', log_level=logging.WARN) # type: Thing
        self.assertEqual(thing_client.get_protocols(), ['INPROC', 'IPC', 'TCP'])
        thing_client.exit()
        self.assertEqual(done_queue.get(), 'test-run-3')

    
    def test_thing_run_and_exit_with_httpserver(self):
        EventLoop.get_async_loop() # creates the event loop if absent
        context = zmq.asyncio.Context()
        T = threading.Thread(target=start_thing_with_http_server, args=('test-run-4', context), daemon=True)
        T.start()       
        thing_client = ObjectProxy('test-run-4', log_level=logging.WARN, context=context) # type: Thing
        self.assertEqual(thing_client.get_protocols(), ['INPROC']) 
        thing_client.exit()
        T.join()
        

class TestThing(Thing):

    @action()
    def get_protocols(self):
        protocols = []
        if self.rpc_server.inproc_server is not None and self.rpc_server.inproc_server.socket_address.startswith('inproc://'):
            protocols.append('INPROC')
        if self.rpc_server.ipc_server is not None and self.rpc_server.ipc_server.socket_address.startswith('ipc://'): 
            protocols.append('IPC')
        if self.rpc_server.tcp_server is not None and self.rpc_server.tcp_server.socket_address.startswith('tcp://'): 
            protocols.append('TCP')
        return protocols

    @action()
    def test_echo(self, value):
        return value
    

def start_thing(instance_name : str, protocols : typing.List[str] =['IPC'], tcp_socket_address : str = None,
                done_queue : typing.Optional[multiprocessing.Queue] = None) -> None:
    thing = TestThing(instance_name=instance_name) #, log_level=logging.WARN)
    thing.run(zmq_protocols=protocols, tcp_socket_address=tcp_socket_address)
    if done_queue is not None:
        done_queue.put(instance_name)


def start_thing_with_http_server(instance_name : str, context : zmq.asyncio.Context) -> None:
    EventLoop.get_async_loop() # creates the event loop if absent
    thing = TestThing(instance_name=instance_name)# , log_level=logging.WARN)
    thing.run_with_http_server(context=context)


if __name__ == '__main__':
    try:
        from utils import TestRunner
    except ImportError:
        from .utils import TestRunner
    unittest.main(testRunner=TestRunner())