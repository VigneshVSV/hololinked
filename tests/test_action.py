import asyncio
import unittest
import logging
from hololinked.server.dataklasses import ActionInfoValidator
from hololinked.server.thing import Thing, action
from hololinked.server.utils import isclassmethod
from hololinked.param import ParameterizedFunction
from hololinked.server.properties import Number, String, ClassSelector
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
    
    def extra_method(self, value):
        return value
    
    class foo(ParameterizedFunction):

        arg1 = Number(bounds=(0, 10), step=0.5, default=5, crop_to_bounds=True, 
                    doc='arg1 description')
        arg2 = String(default='hello', doc='arg2 description', regex='[a-z]+')
        arg3 = ClassSelector(class_=(int, float, str),
                            default=5, doc='arg3 description')

        def __call__(self, instance, arg1, arg2, arg3):
            return instance.instance_name, arg1, arg2, arg3


    class foobar(ParameterizedFunction):

        arg1 = Number(bounds=(0, 10), step=0.5, default=5, crop_to_bounds=True, 
                    doc='arg1 description')
        arg2 = String(default='hello', doc='arg2 description', regex='[a-z]+')
        arg3 = ClassSelector(class_=(int, float, str),
                            default=5, doc='arg3 description')


    class async_foo(ParameterizedFunction):
            
        arg1 = Number(bounds=(0, 10), step=0.5, default=5, crop_to_bounds=True, 
                    doc='arg1 description')
        arg2 = String(default='hello', doc='arg2 description', regex='[a-z]+')
        arg3 = ClassSelector(class_=(int, float, str),
                            default=5, doc='arg3 description')

        async def __call__(self, instance, arg1, arg2, arg3):
            await asyncio.sleep(0.1)
            return instance.instance_name, arg1, arg2, arg3



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
        self.assertEqual(self.thing_cls.foo, action(safe=True)(self.thing_cls.foo))
        self.assertEqual(self.thing_cls.foobar, action(idempotent=False)(self.thing_cls.foobar))
        self.assertEqual(self.thing_cls.async_foo, action(synchronous=False)(self.thing_cls.async_foo))


    def test_action_info(self):
        # basic check if the remote_info is correct, although this test is not necessary, not recommended and 
        # neither particularly useful
        remote_info = self.thing_cls.test_echo._remote_info
        self.assertIsInstance(remote_info, ActionInfoValidator)
        assert isinstance(remote_info, ActionInfoValidator) # type definition
        self.assertTrue(remote_info.isaction)
        self.assertFalse(remote_info.isproperty)
        self.assertFalse(remote_info.isparameterized)
        self.assertFalse(remote_info.iscoroutine)
        self.assertFalse(remote_info.safe)  

        remote_info = self.thing_cls.test_echo_async._remote_info
        self.assertIsInstance(remote_info, ActionInfoValidator)
        assert isinstance(remote_info, ActionInfoValidator) # type definition
        self.assertTrue(remote_info.isaction)
        self.assertTrue(remote_info.iscoroutine)
        self.assertFalse(remote_info.isproperty)
        self.assertFalse(remote_info.isparameterized)
        self.assertFalse(remote_info.safe)

        remote_info = self.thing_cls.test_echo_async._remote_info
        self.assertIsInstance(remote_info, ActionInfoValidator)
        assert isinstance(remote_info, ActionInfoValidator) # type definition
        self.assertTrue(remote_info.isaction)
        self.assertTrue(remote_info.iscoroutine)
        self.assertFalse(remote_info.isproperty)
        self.assertFalse(remote_info.isparameterized)
        self.assertFalse(remote_info.safe)

        remote_info = self.thing_cls.foo._remote_info
        self.assertIsInstance(remote_info, ActionInfoValidator)
        assert isinstance(remote_info, ActionInfoValidator)
        self.assertTrue(remote_info.isaction)
        self.assertFalse(remote_info.iscoroutine)
        self.assertFalse(remote_info.isproperty)
        self.assertTrue(remote_info.isparameterized)
        self.assertTrue(remote_info.safe)

    def test_api(self):
        # done allow action decorator to be terminated without '()' on a method
        with self.assertRaises(TypeError) as ex:
           action(self.thing_cls.extra_method)
        self.assertTrue(str(ex.exception).startswith("URL_path should be a string, not a function/method, did you decorate"))
        



if __name__ == '__main__':
    try:
        from utils import TestRunner
    except ImportError:
        from .utils import TestRunner

    unittest.main(testRunner=TestRunner())