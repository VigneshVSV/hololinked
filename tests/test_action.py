import asyncio
import unittest
import logging
from hololinked.server.dataklasses import ActionInfoValidator
from hololinked.server.thing import Thing, action
from hololinked.server.utils import isclassmethod
from utils import TestCase


class TestThing(Thing):

    def get_protocols(self):
        protocols = []
        if self.rpc_server.inproc_server is not None and self.rpc_server.inproc_server.socket_address.startswith('inproc://'):
            protocols.append('INPROC')
        if self.rpc_server.ipc_server is not None and self.rpc_server.ipc_server.socket_address.startswith('ipc://'): 
            protocols.append('IPC')
        if self.rpc_server.tcp_server is not None and self.rpc_server.tcp_server.socket_address.startswith('tcp://'): 
            protocols.append('TCP')
        return protocols

    def test_echo(self, value):
        return value

    @classmethod
    def test_echo_with_classmethod(self, value):
        return value
    
    async def test_echo_async(self, value):
        await asyncio.sleep(0.1)
        return value
    
    @classmethod
    async def tesc_echo_async_with_classmethod(self, value):
        await asyncio.sleep(0.1)
        return value
    

class TestAction(TestCase):

    @classmethod
    def setUpClass(self):
        self.thing_cls = TestThing 

    def test_action(self):
        # instance method can be decorated with action
        self.assertEqual(self.thing_cls.test_echo, action()(self.thing_cls.test_echo))
        # classmethod can be decorated with action
        self.assertEqual(self.thing_cls.test_echo_with_classmethod, action()(self.thing_cls.test_echo_with_classmethod))
        self.assertTrue(isclassmethod(self.thing_cls.test_echo_with_classmethod))
        # async methods can be decorated with action    
        self.assertEqual(self.thing_cls.test_echo_async, action()(self.thing_cls.test_echo_async))
        # async classmethods can be decorated with action
        self.assertEqual(self.thing_cls.tesc_echo_async_with_classmethod, 
                         action()(self.thing_cls.tesc_echo_async_with_classmethod))
        # parameterized function can be decorated with action


    def test_action_info(self):
        # basic check if the remote_info is correct
        remote_info = self.thing_cls.test_echo._remote_info
        self.assertIsInstance(remote_info, ActionInfoValidator)
        assert isinstance(remote_info, ActionInfoValidator) # type definition
        self.assertTrue(remote_info.isaction)
        self.assertFalse(remote_info.isproperty)
        self.assertFalse(remote_info.isparameterized)
        self.assertFalse(remote_info.iscoroutine)

        remote_info = self.thing_cls.test_echo_async._remote_info
        self.assertIsInstance(remote_info, ActionInfoValidator)
        assert isinstance(remote_info, ActionInfoValidator) # type definition
        self.assertTrue(remote_info.isaction)
        self.assertTrue(remote_info.iscoroutine)
        self.assertFalse(remote_info.isproperty)
        self.assertFalse(remote_info.isparameterized)

        remote_info = self.thing_cls.test_echo_async._remote_info
        self.assertIsInstance(remote_info, ActionInfoValidator)
        assert isinstance(remote_info, ActionInfoValidator) # type definition
        self.assertTrue(remote_info.isaction)
        self.assertTrue(remote_info.iscoroutine)
        self.assertFalse(remote_info.isproperty)
        self.assertFalse(remote_info.isparameterized)





if __name__ == '__main__':
    try:
        from utils import TestRunner
    except ImportError:
        from .utils import TestRunner

    unittest.main(testRunner=TestRunner())