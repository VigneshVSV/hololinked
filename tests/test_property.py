import datetime
import logging
import unittest
import time
import os
from hololinked.client import ObjectProxy
from hololinked.server import action, Thing, global_config
from hololinked.server.properties import Number, String, Selector, List, Integer
from hololinked.server.database import BaseDB
try:
    from .utils import TestCase, TestRunner
    from .things import start_thing_forked
except ImportError:
    from utils import TestCase, TestRunner
    from things import start_thing_forked




class TestThing(Thing):

    number_prop = Number(doc="A fully editable number property")
    string_prop = String(default='hello', regex='^[a-z]+',
                        doc="A string property with a regex constraint to check value errors")
    int_prop = Integer(default=5, step=2, bounds=(0, 100),
                        doc="An integer property with step and bounds constraints to check RW")
    selector_prop = Selector(objects=['a', 'b', 'c', 1], default='a',
                        doc="A selector property to check RW")
    observable_list_prop = List(default=None, allow_None=True, observable=True,
                        doc="An observable list property to check observable events on write operations")
    observable_readonly_prop = Number(default=0, readonly=True, observable=True,
                        doc="An observable readonly property to check observable events on read operations")
    db_commit_number_prop = Number(default=0, db_commit=True,
                        doc="A fully editable number property to check commits to db on write operations")
    db_init_int_prop = Integer(default=1, db_init=True,
                        doc="An integer property to check initialization from db")
    db_persist_selector_prop = Selector(objects=['a', 'b', 'c', 1], default='a', db_persist=True,
                        doc="A selector property to check persistence to db on write operations")
    non_remote_number_prop = Number(default=5, remote=False,
                        doc="A non remote number property to check non-availability on client")

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
        print(f'observable_readonly_prop: {self.observable_readonly_prop}')
        print(f'db_commit_number_prop: {self.db_commit_number_prop}')
        print(f'db_init_int_prop: {self.db_init_int_prop}')
        print(f'db_persist_selctor_prop: {self.db_persist_selector_prop}')
        print(f'non_remote_number_prop: {self.non_remote_number_prop}')




class TestProperty(TestCase):

    @classmethod
    def setUpClass(self):
        print("test property")
        self.thing_cls = TestThing
        start_thing_forked(self.thing_cls, instance_name='test-property',
                                    log_level=logging.WARN)
        self.thing_client = ObjectProxy('test-property') # type: TestThing

    @classmethod
    def tearDownClass(self):
        print("tear down test property")
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
        self.thing_client.write_multiple_properties(
                number_prop=15,
                string_prop='foobar'
            )
        self.assertEqual(self.thing_client.number_prop, 15)
        self.assertEqual(self.thing_client.string_prop, 'foobar')
        # check prop that was not set in multiple properties
        self.assertEqual(self.thing_client.int_prop, 5)

        self.thing_client.selector_prop = 'b'
        self.thing_client.number_prop = -15
        props = self.thing_client.read_multiple_properties(names=['selector_prop', 'int_prop',
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
        time.sleep(3)
        # Calm down for event publisher to connect fully as there is no handshake for events
        for value in propective_values:
            self.thing_client.observable_list_prop = value

        for i in range(20):
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
        time.sleep(3)
        # Calm down for event publisher to connect fully as there is no handshake for events
        for _ in propective_values:
            self.thing_client.observable_readonly_prop

        for i in range(20):
            if attempt == len(propective_values):
                break
            # wait for the callback to be called
            time.sleep(0.1)

        self.thing_client.unsubscribe_event('observable_readonly_prop_change_event')
        self.assertEqual(result, propective_values)


    def test_4_db_operations(self):
        # remove old file path first
        file_path = f'{BaseDB.get_temp_dir_for_class_name(TestThing.__name__)}/test-db-operations.db'
        try:
            os.remove(file_path)
        except (OSError, FileNotFoundError):
            pass
        self.assertTrue(not os.path.exists(file_path))
    	
        # test db commit property
        thing = TestThing(instance_name='test-db-operations', use_default_db=True, log_level=logging.WARN)
        self.assertEqual(thing.db_commit_number_prop, 0) # 0 is default just for reference
        thing.db_commit_number_prop = 100
        self.assertEqual(thing.db_commit_number_prop, 100)
        self.assertEqual(thing.db_engine.get_property('db_commit_number_prop'), 100)

        # test db persist property
        self.assertEqual(thing.db_persist_selector_prop, 'a') # a is default just for reference
        thing.db_persist_selector_prop = 'c'
        self.assertEqual(thing.db_persist_selector_prop, 'c')
        self.assertEqual(thing.db_engine.get_property('db_persist_selector_prop'), 'c')

        # test db init property
        self.assertEqual(thing.db_init_int_prop, 1) # 1 is default just for reference
        thing.db_init_int_prop = 50
        self.assertEqual(thing.db_init_int_prop, 50)
        self.assertNotEqual(thing.db_engine.get_property('db_init_int_prop'), 50)
        self.assertEqual(thing.db_engine.get_property('db_init_int_prop'), TestThing.db_init_int_prop.default)
        del thing

        # delete thing and reload from database 
        thing = TestThing(instance_name='test-db-operations', use_default_db=True, log_level=logging.WARN)
        self.assertEqual(thing.db_init_int_prop, TestThing.db_init_int_prop.default)
        self.assertEqual(thing.db_persist_selector_prop, 'c')
        self.assertNotEqual(thing.db_commit_number_prop, 100)
        self.assertEqual(thing.db_commit_number_prop, TestThing.db_commit_number_prop.default)

        # check db init prop with a different value in database apart from default
        thing.db_engine.set_property('db_init_int_prop', 101)
        del thing
        thing = TestThing(instance_name='test-db-operations', use_default_db=True, log_level=logging.WARN)
        self.assertEqual(thing.db_init_int_prop, 101)


if __name__ == '__main__':
    unittest.main(testRunner=TestRunner())
