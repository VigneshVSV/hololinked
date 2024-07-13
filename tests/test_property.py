import logging
import unittest
import time
from hololinked.client import ObjectProxy
from hololinked.server import action, Thing
from hololinked.server.properties import Number, String, Selector, List, Integer
try:
    from .utils import TestCase, TestRunner
    from .things import start_thing_forked
except ImportError:
    from utils import TestCase, TestRunner
    from things import start_thing_forked



class TestThing(Thing):

    number_prop = Number()
    string_prop = String(default='hello', regex='^[a-z]+', db_init=True)
    int_prop = Integer(default=5, step=2, bounds=(0, 100), observable=True,
                    db_commit=True)
    selector_prop = Selector(objects=['a', 'b', 'c', 1], default='a',
                        db_persist=True)
    observable_list_prop = List(default=None, allow_None=True, observable=True)
    observable_readonly_prop = Number(default=0, readonly=True, observable=True)
    non_remote_number_prop = Number(default=5, remote=False)

    @observable_readonly_prop.getter
    def get_observable_readonly_prop(self):
        if not hasattr(self, '_observable_readonly_prop'):
            self._observable_readonly_prop = 0
        self._observable_readonly_prop += 1
        return self._observable_readonly_prop


    @action()
    def print_props(self):
        print(f'number_prop: {self.number_prop}')
        print(f'string_prop: {self.string_prop}')
        print(f'int_prop: {self.int_prop}')
        print(f'selector_prop: {self.selector_prop}')
        print(f'observable_list_prop: {self.observable_list_prop}')
        print(f'non_remote_number_prop: {self.non_remote_number_prop}')



class TestProperty(TestCase):

    @classmethod
    def setUpClass(self):
        self.thing_cls = TestThing
        start_thing_forked(self.thing_cls, instance_name='test-property',
                                    log_level=logging.WARN)
        self.thing_client = ObjectProxy('test-property') # type: TestThing

    @classmethod
    def tearDownClass(self):
        self.thing_client.exit()


    def test_1_client_api(self):
        # Test read
        self.assertEqual(self.thing_client.number_prop, 0)
        # Test write 
        self.thing_client.string_prop = 'world'
        self.assertEqual(self.thing_client.string_prop, 'world')
        # Test exception propagation to client
        with self.assertRaises(ValueError):
            self.thing_client.string_prop = 'WORLD'
        with self.assertRaises(TypeError):
            self.thing_client.int_prop = '5'
        # Test non remote prop (non-)availability on client
        with self.assertRaises(AttributeError):
            self.thing_client.non_remote_number_prop


    def test_2_RW_multiple_properties(self):
        # Test partial list of read write properties
        self.thing_client.set_properties(
                number_prop=15, 
                string_prop='foobar'
            )
        self.assertEqual(self.thing_client.number_prop, 15)
        self.assertEqual(self.thing_client.string_prop, 'foobar')
        # check prop that was not set in multiple properties
        self.assertEqual(self.thing_client.int_prop, 5)
      
        self.thing_client.selector_prop = 'b'
        self.thing_client.number_prop = -15
        props = self.thing_client.get_properties(names=['selector_prop', 'int_prop', 
                                                    'number_prop', 'string_prop'])
        self.assertEqual(props['selector_prop'], 'b')
        self.assertEqual(props['int_prop'], 5)
        self.assertEqual(props['number_prop'], -15)
        self.assertEqual(props['string_prop'], 'foobar')


    def test_3_observability(self):
        # req 1 - observable events come due to writing a property
        propective_values = [
            [1, 2, 3, 4, 5],
            ['a', 'b', 'c', 'd', 'e'],
            [1, 'a', 2, 'b', 3]
        ]
        result = []
        attempt = 0
        def cb(value):
            nonlocal attempt, result
            self.assertEqual(value, propective_values[attempt])
            result.append(value)
            attempt += 1

        self.thing_client.subscribe_event('observable_list_prop_change_event', cb)
        for value in propective_values:
            self.thing_client.observable_list_prop = value
         
        for i in range(10):
            if attempt == len(propective_values):
                break
            # wait for the callback to be called
            time.sleep(0.1)
        self.thing_client.unsubscribe_event('observable_list_prop_change_event')
        
        self.assertEqual(result, propective_values)

        # req 2 - observable events come due to reading a property
        propective_values = [1, 2, 3, 4, 5]
        result = []
        attempt = 0
        def cb(value):
            nonlocal attempt, result
            self.assertEqual(value, propective_values[attempt])
            result.append(value)
            attempt += 1

        self.thing_client.subscribe_event('observable_readonly_prop_change_event', cb)
        for _ in propective_values:
            self.thing_client.observable_readonly_prop

        for i in range(10):
            if attempt == len(propective_values):
                break
            # wait for the callback to be called
            time.sleep(0.1)

        self.thing_client.unsubscribe_event('observable_readonly_prop_change_event')
        self.assertEqual(result, propective_values)


    def test_4_db_operations(self):
        thing = TestThing(instance_name='test-db-operations', use_default_db=True)
        thing.number_prop = 5
        

if __name__ == '__main__':
    unittest.main(testRunner=TestRunner())
 