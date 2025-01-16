import asyncio
import typing
import unittest
import logging
import multiprocessing

from hololinked.utils import isclassmethod
from hololinked.param import ParameterizedFunction
from hololinked.server.actions import Action, BoundAction, BoundSyncAction, BoundAsyncAction
from hololinked.server.dataklasses import ActionInfoValidator
from hololinked.server.thing import Thing, action
from hololinked.server.properties import Number, String, ClassSelector
from hololinked.client import ObjectProxy
try:
    from .utils import TestCase, TestRunner
    from .things import TestThing
except ImportError:
    from utils import TestCase, TestRunner
    from things import start_thing_forked 


class TestThing(Thing):

    def action_echo(self, value):
        return value

    @classmethod
    def action_echo_with_classmethod(self, value):
        return value
    
    async def action_echo_async(self, value):
        await asyncio.sleep(0.1)
        return value
    
    @classmethod
    async def action_echo_async_with_classmethod(self, value):
        await asyncio.sleep(0.1)
        return value
    
    class typed_action(ParameterizedFunction):

        arg1 = Number(bounds=(0, 10), step=0.5, default=5, crop_to_bounds=True, 
                    doc='arg1 description')
        arg2 = String(default='hello', doc='arg2 description', regex='[a-z]+')
        arg3 = ClassSelector(class_=(int, float, str),
                            default=5, doc='arg3 description')

        def __call__(self, instance, arg1, arg2, arg3):
            return instance.id, arg1, arg2, arg3


    class typed_action_without_call(ParameterizedFunction):

        arg1 = Number(bounds=(0, 10), step=0.5, default=5, crop_to_bounds=True, 
                    doc='arg1 description')
        arg2 = String(default='hello', doc='arg2 description', regex='[a-z]+')
        arg3 = ClassSelector(class_=(int, float, str),
                            default=5, doc='arg3 description')


    class typed_action_async(ParameterizedFunction):
            
        arg1 = Number(bounds=(0, 10), step=0.5, default=5, crop_to_bounds=True, 
                    doc='arg1 description')
        arg2 = String(default='hello', doc='arg2 description', regex='[a-z]+')
        arg3 = ClassSelector(class_=(int, float, str),
                            default=5, doc='arg3 description')

        async def __call__(self, instance, arg1, arg2, arg3):
            await asyncio.sleep(0.1)
            return instance.id, arg1, arg2, arg3


    def __internal__(self, value):
        return value

    def incorrectly_decorated_method(self, value):
        return value
    
    def not_an_action(self, value):
        return value
    
    async def not_an_async_action(self, value):
        await asyncio.sleep(0.1)
        return value
    


class TestAction(TestCase):

    @classmethod
    def setUpClass(self):
        super().setUpClass()
        print("test action")
        self.thing_cls = TestThing 

    def test_1_allowed_actions(self):
        """Test if methods can be decorated with action"""
        # 1. instance method can be decorated with action
        self.assertEqual(Action(self.thing_cls.action_echo), action()(self.thing_cls.action_echo))
        # 2. classmethod can be decorated with action
        self.assertEqual(Action(self.thing_cls.action_echo_with_classmethod), 
                        action()(self.thing_cls.action_echo_with_classmethod))
        self.assertTrue(isclassmethod(self.thing_cls.action_echo_with_classmethod))
        # 3. async methods can be decorated with action    
        self.assertEqual(Action(self.thing_cls.action_echo_async), 
                        action()(self.thing_cls.action_echo_async))
        # 4. async classmethods can be decorated with action
        self.assertEqual(Action(self.thing_cls.action_echo_async_with_classmethod), 
                        action()(self.thing_cls.action_echo_async_with_classmethod))
        self.assertTrue(isclassmethod(self.thing_cls.action_echo_async_with_classmethod))
        # 5. parameterized function can be decorated with action
        self.assertEqual(Action(self.thing_cls.typed_action), 
                            action(safe=True)(self.thing_cls.typed_action))
        self.assertEqual(Action(self.thing_cls.typed_action_without_call), 
                            action(idempotent=True)(self.thing_cls.typed_action_without_call))
        self.assertEqual(Action(self.thing_cls.typed_action_async), 
                            action(synchronous=True)(self.thing_cls.typed_action_async))


    def test_2_bound_method(self):
        """Test if methods decorated with action are correctly bound"""
        thing = self.thing_cls(id='test-action', log_level=logging.ERROR)
        replace_methods_with_actions(thing_cls=self.thing_cls)

        # 1. instance method can be decorated with action
        self.assertIsInstance(thing.action_echo, BoundAction)
        self.assertIsInstance(thing.action_echo, BoundSyncAction)
        self.assertNotIsInstance(thing.action_echo, BoundAsyncAction)
        self.assertIsInstance(self.thing_cls.action_echo, Action)
        self.assertNotIsInstance(self.thing_cls.action_echo, BoundAction)
        # associated attributes of BoundAction
        assert isinstance(thing.action_echo, BoundAction) # type definition
        self.assertEqual(thing.action_echo.name, 'action_echo')
        self.assertEqual(thing.action_echo.owner_inst, thing)
        self.assertEqual(thing.action_echo.owner, self.thing_cls)
        self.assertEqual(thing.action_echo.execution_info, self.thing_cls.action_echo.execution_info)
        self.assertEqual(str(thing.action_echo), 
                        f"<BoundAction({self.thing_cls.__name__}.{thing.action_echo.name} of {thing.id})>") 
        self.assertNotEqual(thing.action_echo, self.thing_cls.action_echo)
        self.assertEqual(thing.action_echo.bound_obj, thing)
          
        # 2. classmethod can be decorated with action
        self.assertIsInstance(thing.action_echo_with_classmethod, BoundAction)
        self.assertIsInstance(thing.action_echo_with_classmethod, BoundSyncAction)
        self.assertNotIsInstance(thing.action_echo_with_classmethod, BoundAsyncAction)
        self.assertIsInstance(self.thing_cls.action_echo_with_classmethod, BoundAction)
        self.assertIsInstance(self.thing_cls.action_echo_with_classmethod, BoundSyncAction)
        self.assertNotIsInstance(self.thing_cls.action_echo_with_classmethod, Action)
        # associated attributes of BoundAction
        assert isinstance(thing.action_echo_with_classmethod, BoundAction)
        self.assertEqual(thing.action_echo_with_classmethod.name, 'action_echo_with_classmethod')
        self.assertEqual(thing.action_echo_with_classmethod.owner_inst, thing)
        self.assertEqual(thing.action_echo_with_classmethod.owner, self.thing_cls)
        self.assertEqual(thing.action_echo_with_classmethod.execution_info, self.thing_cls.action_echo_with_classmethod.execution_info)
        self.assertEqual(str(thing.action_echo_with_classmethod),
                        f"<BoundAction({self.thing_cls.__name__}.{thing.action_echo_with_classmethod.name} of {thing.id})>")
        self.assertEqual(thing.action_echo_with_classmethod, self.thing_cls.action_echo_with_classmethod)
        self.assertEqual(thing.action_echo_with_classmethod.bound_obj, self.thing_cls)
        
        # 3. async methods can be decorated with action
        self.assertIsInstance(thing.action_echo_async, BoundAction)
        self.assertNotIsInstance(thing.action_echo_async, BoundSyncAction)
        self.assertIsInstance(thing.action_echo_async, BoundAsyncAction)
        self.assertIsInstance(self.thing_cls.action_echo_async, Action)
        self.assertNotIsInstance(self.thing_cls.action_echo_async, BoundAction)
        # associated attributes of BoundAction
        assert isinstance(thing.action_echo_async, BoundAction)
        self.assertEqual(thing.action_echo_async.name, 'action_echo_async')
        self.assertEqual(thing.action_echo_async.owner_inst, thing)
        self.assertEqual(thing.action_echo_async.owner, self.thing_cls)
        self.assertEqual(thing.action_echo_async.execution_info, self.thing_cls.action_echo_async.execution_info)
        self.assertEqual(str(thing.action_echo_async),
                        f"<BoundAction({self.thing_cls.__name__}.{thing.action_echo_async.name} of {thing.id})>")
        self.assertNotEqual(thing.action_echo_async, self.thing_cls.action_echo_async)
        self.assertEqual(thing.action_echo_async.bound_obj, thing)
        
        # 4. async classmethods can be decorated with action
        self.assertIsInstance(thing.action_echo_async_with_classmethod, BoundAction)
        self.assertNotIsInstance(thing.action_echo_async_with_classmethod, BoundSyncAction)
        self.assertIsInstance(thing.action_echo_async_with_classmethod, BoundAsyncAction)
        self.assertIsInstance(self.thing_cls.action_echo_async_with_classmethod, BoundAction)
        self.assertIsInstance(self.thing_cls.action_echo_async_with_classmethod, BoundAsyncAction)
        self.assertNotIsInstance(self.thing_cls.action_echo_async_with_classmethod, Action)
        # associated attributes of BoundAction
        assert isinstance(thing.action_echo_async_with_classmethod, BoundAction)
        self.assertEqual(thing.action_echo_async_with_classmethod.name, 'action_echo_async_with_classmethod')
        self.assertEqual(thing.action_echo_async_with_classmethod.owner_inst, thing)
        self.assertEqual(thing.action_echo_async_with_classmethod.owner, self.thing_cls)
        self.assertEqual(thing.action_echo_async_with_classmethod.execution_info, self.thing_cls.action_echo_async_with_classmethod.execution_info)
        self.assertEqual(str(thing.action_echo_async_with_classmethod),
                        f"<BoundAction({self.thing_cls.__name__}.{thing.action_echo_async_with_classmethod.name} of {thing.id})>")
        self.assertEqual(thing.action_echo_async_with_classmethod, self.thing_cls.action_echo_async_with_classmethod)
        self.assertEqual(thing.action_echo_async_with_classmethod.bound_obj, self.thing_cls)

        # 5. parameterized function can be decorated with action
        self.assertIsInstance(thing.typed_action, BoundAction)
        self.assertIsInstance(thing.typed_action, BoundSyncAction)
        self.assertNotIsInstance(thing.typed_action, BoundAsyncAction)
        self.assertIsInstance(self.thing_cls.typed_action, Action)
        self.assertNotIsInstance(self.thing_cls.typed_action, BoundAction)
        # associated attributes of BoundAction
        assert isinstance(thing.typed_action, BoundAction)
        self.assertEqual(thing.typed_action.name, 'typed_action')
        self.assertEqual(thing.typed_action.owner_inst, thing)
        self.assertEqual(thing.typed_action.owner, self.thing_cls)
        self.assertEqual(thing.typed_action.execution_info, self.thing_cls.typed_action.execution_info)
        self.assertEqual(str(thing.typed_action),
                        f"<BoundAction({self.thing_cls.__name__}.{thing.typed_action.name} of {thing.id})>")
        self.assertNotEqual(thing.typed_action, self.thing_cls.typed_action)
        self.assertEqual(thing.typed_action.bound_obj, thing)

        # 6. parameterized function can be decorated with action
        self.assertIsInstance(thing.typed_action_without_call, BoundAction)
        self.assertIsInstance(thing.typed_action_without_call, BoundSyncAction)
        self.assertNotIsInstance(thing.typed_action_without_call, BoundAsyncAction)
        self.assertIsInstance(self.thing_cls.typed_action_without_call, Action)
        self.assertNotIsInstance(self.thing_cls.typed_action_without_call, BoundAction)
        # associated attributes of BoundAction
        assert isinstance(thing.typed_action_without_call, BoundAction)
        self.assertEqual(thing.typed_action_without_call.name, 'typed_action_without_call')
        self.assertEqual(thing.typed_action_without_call.owner_inst, thing)
        self.assertEqual(thing.typed_action_without_call.owner, self.thing_cls)
        self.assertEqual(thing.typed_action_without_call.execution_info, self.thing_cls.typed_action_without_call.execution_info)
        self.assertEqual(str(thing.typed_action_without_call),
                        f"<BoundAction({self.thing_cls.__name__}.{thing.typed_action_without_call.name} of {thing.id})>")
        self.assertNotEqual(thing.typed_action_without_call, self.thing_cls.typed_action_without_call)
        self.assertEqual(thing.typed_action_without_call.bound_obj, thing)

        # 7. parameterized function can be decorated with action
        self.assertIsInstance(thing.typed_action_async, BoundAction)
        self.assertNotIsInstance(thing.typed_action_async, BoundSyncAction)
        self.assertIsInstance(thing.typed_action_async, BoundAsyncAction)
        self.assertIsInstance(self.thing_cls.typed_action_async, Action)
        self.assertNotIsInstance(self.thing_cls.typed_action_async, BoundAction)
        # associated attributes of BoundAction
        assert isinstance(thing.typed_action_async, BoundAction)
        self.assertEqual(thing.typed_action_async.name, 'typed_action_async')
        self.assertEqual(thing.typed_action_async.owner_inst, thing)
        self.assertEqual(thing.typed_action_async.owner, self.thing_cls)
        self.assertEqual(thing.typed_action_async.execution_info, self.thing_cls.typed_action_async.execution_info)
        self.assertEqual(str(thing.typed_action_async),
                        f"<BoundAction({self.thing_cls.__name__}.{thing.typed_action_async.name} of {thing.id})>")
        self.assertNotEqual(thing.typed_action_async, self.thing_cls.typed_action_async)
        self.assertEqual(thing.typed_action_async.bound_obj, thing)


    def test_3_remote_info(self):
        """Test if the validator is working correctly, on which the logic of the action is based"""
        # basic check if the remote_info is correct, although this test is not necessary, not recommended and 
        # neither particularly useful
        remote_info = self.thing_cls.action_echo.execution_info
        self.assertIsInstance(remote_info, ActionInfoValidator)
        assert isinstance(remote_info, ActionInfoValidator) # type definition
        self.assertTrue(remote_info.isaction)
        self.assertFalse(remote_info.isproperty)
        self.assertFalse(remote_info.isparameterized)
        self.assertFalse(remote_info.iscoroutine)
        self.assertFalse(remote_info.safe)  
        self.assertFalse(remote_info.idempotent)
        self.assertFalse(remote_info.synchronous)

        remote_info = self.thing_cls.action_echo_async.execution_info
        self.assertIsInstance(remote_info, ActionInfoValidator)
        assert isinstance(remote_info, ActionInfoValidator) # type definition
        self.assertTrue(remote_info.isaction)
        self.assertTrue(remote_info.iscoroutine)
        self.assertFalse(remote_info.isproperty)
        self.assertFalse(remote_info.isparameterized)
        self.assertFalse(remote_info.safe)
        self.assertFalse(remote_info.idempotent)
        self.assertFalse(remote_info.synchronous)

        remote_info = self.thing_cls.action_echo_with_classmethod.execution_info
        self.assertIsInstance(remote_info, ActionInfoValidator)
        assert isinstance(remote_info, ActionInfoValidator) # type definition
        self.assertTrue(remote_info.isaction)
        self.assertFalse(remote_info.iscoroutine)
        self.assertFalse(remote_info.isproperty)
        self.assertFalse(remote_info.isparameterized)
        self.assertFalse(remote_info.safe)
        self.assertFalse(remote_info.idempotent)
        self.assertFalse(remote_info.synchronous)

        remote_info = self.thing_cls.typed_action.execution_info
        self.assertIsInstance(remote_info, ActionInfoValidator)
        assert isinstance(remote_info, ActionInfoValidator)
        self.assertTrue(remote_info.isaction)
        self.assertFalse(remote_info.iscoroutine)
        self.assertFalse(remote_info.isproperty)
        self.assertTrue(remote_info.isparameterized)
        self.assertTrue(remote_info.safe)
        self.assertFalse(remote_info.idempotent)
        self.assertFalse(remote_info.synchronous)

        remote_info = self.thing_cls.typed_action_without_call.execution_info
        self.assertIsInstance(remote_info, ActionInfoValidator)
        assert isinstance(remote_info, ActionInfoValidator)
        self.assertTrue(remote_info.isaction)
        self.assertFalse(remote_info.iscoroutine)
        self.assertFalse(remote_info.isproperty)
        self.assertTrue(remote_info.isparameterized)
        self.assertFalse(remote_info.safe)
        self.assertTrue(remote_info.idempotent)
        self.assertFalse(remote_info.synchronous)

        remote_info = self.thing_cls.typed_action_async.execution_info
        self.assertIsInstance(remote_info, ActionInfoValidator)
        assert isinstance(remote_info, ActionInfoValidator)
        self.assertTrue(remote_info.isaction)
        self.assertTrue(remote_info.iscoroutine)
        self.assertFalse(remote_info.isproperty)
        self.assertTrue(remote_info.isparameterized)
        self.assertFalse(remote_info.safe)
        self.assertFalse(remote_info.idempotent)
        self.assertTrue(remote_info.synchronous)


    def test_4_api_and_invalid_actions(self):
        """Test if action prevents invalid objects and raises neat errors"""
        # done allow action decorator to be terminated without '()' on a method
        with self.assertRaises(TypeError) as ex:
           action(self.thing_cls.incorrectly_decorated_method)
        self.assertTrue(str(ex.exception).startswith("input schema should be a JSON, not a function/method, did you decorate your action wrongly?"))
        
        # dunder methods cannot be decorated with action
        with self.assertRaises(ValueError) as ex:
            action()(self.thing_cls.__internal__)
        self.assertTrue(str(ex.exception).startswith("dunder objects cannot become remote"))

        # only functions and methods can be decorated with action
        for obj in [self.thing_cls, str, 1, 1.0, 'Str', True, None, object(), type, property]:
            with self.assertRaises(TypeError) as ex:
                action()(obj) # not an action
            self.assertTrue(str(ex.exception).startswith("target for action or is not a function/method."))

        with self.assertRaises(ValueError) as ex:
            action(safe=True, some_kw=1)
        self.assertTrue(str(ex.exception).startswith("Only 'safe', 'idempotent', 'synchronous' are allowed"))


    def _test_4_exposed_actions(self):
        self.assertTrue(hasattr(self.thing_cls.action_echo, '_remote_info'))
        done_queue = multiprocessing.Queue()
        start_thing_forked(self.thing_cls, id='test-action', done_queue=done_queue,
                                        log_level=logging.ERROR+10, prerun_callback=replace_methods_with_actions)

        thing_client = ObjectProxy('test-action', log_level=logging.ERROR) # type: TestThing

        self.assertTrue(thing_client.action_echo(1) == 1)
        self.assertTrue(thing_client.action_echo_async("string") == "string")
        self.assertTrue(thing_client.typed_action(arg1=1, arg2='hello', arg3=5) == ['test-action', 1, 'hello', 5])
        self.assertTrue(thing_client.typed_action_async(arg1=2.5, arg2='hello', arg3='foo') == ['test-action', 2.5, 'hello', 'foo'])

        with self.assertRaises(NotImplementedError) as ex:
            thing_client.typed_action_without_call(arg1=1, arg2='hello', arg3=5), 
        self.assertTrue(str(ex.exception).startswith("Subclasses must implement __call__"))
        
        with self.assertRaises(AttributeError) as ex:
            thing_client.__internal__(1)
        self.assertTrue(str(ex.exception).startswith("'ObjectProxy' object has no attribute '__internal__'"))

        with self.assertRaises(AttributeError) as ex:
            thing_client.not_an_action("foo")
        self.assertTrue(str(ex.exception).startswith("'ObjectProxy' object has no attribute 'not_an_action'"))

        with self.assertRaises(AttributeError) as ex:
            thing_client.not_an_async_action(1)
        self.assertTrue(str(ex.exception).startswith("'ObjectProxy' object has no attribute 'not_an_async_action'"))

        thing_client.exit()

        self.assertTrue(done_queue.get() == 'test-action')



def replace_methods_with_actions(thing_cls):
    thing_cls.action_echo = action()(thing_cls.action_echo)
        # classmethod can be decorated with action   
    thing_cls.action_echo_with_classmethod = action()(thing_cls.action_echo_with_classmethod)   
    # async methods can be decorated with action       
    thing_cls.action_echo_async = action()(thing_cls.action_echo_async)
    # async classmethods can be decorated with action    
    thing_cls.action_echo_async_with_classmethod = action()(thing_cls.action_echo_async_with_classmethod)
    # parameterized function can be decorated with action
    thing_cls.typed_action = action(safe=True)(thing_cls.typed_action)
    thing_cls.typed_action_without_call = action(idempotent=True)(thing_cls.typed_action_without_call)
    thing_cls.typed_action_async = action(synchronous=True)(thing_cls.typed_action_async)



if __name__ == '__main__':
    unittest.main(testRunner=TestRunner())