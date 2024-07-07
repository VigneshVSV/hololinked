import unittest
import multiprocessing 
import logging

from hololinked.server import Thing
from hololinked.client import ObjectProxy



class TestThingRun(unittest.TestCase):

    def setUp(self):
        self.thing_cls = Thing 

    def test_thing_run_and_exit(self):
        # should be able to start and end with exactly the specified protocols
        multiprocessing.Process(target=start_thing, args=('test-run', ), daemon=True).start()
        thing_client = ObjectProxy('test-run', log_level=logging.WARN) # type: Thing
        self.assertEqual(thing_client.get_protocols(), ['IPC']) 
        thing_client.exit()
        
        multiprocessing.Process(target=start_thing, args=('test-run-2', ['IPC', 'INPROC'],), daemon=True).start()
        thing_client = ObjectProxy('test-run-2', log_level=logging.WARN) # type: Thing
        self.assertEqual(thing_client.get_protocols(), ['INPROC', 'IPC']) # order should reflect get_protocols() action
        thing_client.exit()
        
        multiprocessing.Process(target=start_thing, args=('test-run-3', ['IPC', 'INPROC', 'TCP'], 'tcp://*:60000'), 
                                    daemon=True).start()
        thing_client = ObjectProxy('test-run-3', log_level=logging.WARN) # type: Thing
        self.assertEqual(thing_client.get_protocols(), ['INPROC', 'IPC', 'TCP'])
        thing_client.exit()
      


def start_thing(instance_name, protocols=['IPC'], tcp_socket_address = None):
    from hololinked.server import Thing, action

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

        # @action()
        # def test_echo(self, value):
        #     return value

    thing = TestThing(instance_name=instance_name)# , log_level=logging.WARN)
    thing.run(zmq_protocols=protocols, tcp_socket_address=tcp_socket_address)
   

if __name__ == '__main__':
    try:
        from utils import TestRunner
    except ImportError:
        from .utils import TestRunner
    unittest.main(testRunner=TestRunner())
