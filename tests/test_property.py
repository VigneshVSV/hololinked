import logging
import unittest
from hololinked.client import ObjectProxy
from hololinked.server import action
from hololinked.server.properties import Number, String, Selector

try:
    from .utils import TestCase, TestRunner
    from .things import TestThing, start_thing_in_separate_process
except ImportError:
    from utils import TestCase, TestRunner
    from things import TestThing, start_thing_in_separate_process



class TestThing(TestThing):

    number_prop = Number()
    string_prop = String(default='hello', regex='^[a-z]+')
    int_prop = Number(default=5, step=2, bounds=(0, 100))
    selector_prop = Selector(objects=['a', 'b', 'c', 1], default='a')
    non_remote_number_prop = Number(default=5, remote=False)

    @action()
    def print_props(self):
        print(f'number_prop: {self.number_prop}')
        print(f'string_prop: {self.string_prop}')
        print(f'int_prop: {self.int_prop}')
        print(f'non_remote_number_prop: {self.non_remote_number_prop}')



class TestProperty(TestCase):

    @classmethod
    def setUpClass(self):
        self.thing_cls = TestThing
        start_thing_in_separate_process(self.thing_cls, instance_name='test-property',
                                    log_level=logging.WARN)
        self.thing_client = ObjectProxy('test-property') # type: TestThing

    @classmethod
    def tearDownClass(cls):
        cls.thing_client.exit()


    def test_1_client_api(self):
        # Test read
        self.assertEqual(self.thing_client.number_prop, TestThing.number_prop.default)
        # Test write 
        self.thing_client.string_prop = 'world'
        self.assertEqual(self.thing_client.string_prop, 'world')
        # Test exception propagation to client
        with self.assertRaises(ValueError):
            self.thing_client.string_prop = 'WORLD'
        with self.assertRaises(TypeError):
            self.thing_client.int_prop = '5'

        # Test non remote prop availability
        with self.assertRaises(AttributeError):
            self.thing_client.non_remote_number_prop


    def test_2_RW_multiple_properties(self):
        self.thing_client.set_properties(
                number_prop=15, 
                string_prop='foobar'
            )
        self.assertEqual(self.thing_client.number_prop, 15)
        self.assertEqual(self.thing_client.string_prop, 'foobar')
        # check prop that was not set in multiple properties
        self.assertEqual(self.thing_client.int_prop, TestThing.int_prop.default)
      
        self.thing_client.selector_prop = 'b'
        self.thing_client.number_prop = -15
        props = self.thing_client.get_properties(names=['selector_prop', 'int_prop', 
                                                    'number_prop', 'string_prop'])
        self.assertEqual(props['selector_prop'], 'b')
        self.assertEqual(props['int_prop'], TestThing.int_prop.default)
        self.assertEqual(props['number_prop'], -15)
        self.assertEqual(props['string_prop'], 'foobar')


if __name__ == '__main__':
    unittest.main(testRunner=TestRunner())