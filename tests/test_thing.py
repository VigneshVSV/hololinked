import unittest
import logging
import warnings

from hololinked.server import Thing
from hololinked.server.serializers import JSONSerializer, PickleSerializer, MsgpackSerializer
from hololinked.server.utils import get_default_logger 
from hololinked.server.logger import RemoteAccessHandler


class TestThing(unittest.TestCase):
    
    def test_instance_name(self):
        print() # dont concatenate with results printed by unit test

        # instance name must be a string and cannot be changed after set
        thing = Thing(instance_name="test_instance_name", log_level=logging.WARN)
        self.assertEqual(thing.instance_name, "test_instance_name")
        with self.assertRaises(ValueError):
            thing.instance_name = "new_instance"
        with self.assertRaises(NotImplementedError):
            del thing.instance_name


    def test_logger(self):
        print() 

        # logger must have remote access handler if logger_remote_access is True
        logger = get_default_logger("test_logger", log_level=logging.WARN)
        thing = Thing(instance_name="test_logger_remote_access", logger=logger, logger_remote_access=True)
        self.assertEqual(thing.logger, logger)
        self.assertTrue(any(isinstance(handler, RemoteAccessHandler) for handler in thing.logger.handlers))

        # Therefore also check the false condition
        logger = get_default_logger("test_logger_2", log_level=logging.WARN)
        thing = Thing(instance_name="test_logger_without_remote_access", logger=logger, logger_remote_access=False)
        self.assertFalse(any(isinstance(handler, RemoteAccessHandler) for handler in thing.logger.handlers))
        # NOTE - logger is modifiable after instantiation 
        # What if user gives his own remote access handler?
        

    def test_JSON_serializer(self):
        print()

        # req 1 - if serializer is not provided, default is JSONSerializer and http and zmq serializers are same
        thing = Thing(instance_name="test_serializer_when_not_provided", log_level=logging.WARN)
        self.assertIsInstance(thing.zmq_serializer, JSONSerializer)
        self.assertEqual(thing.http_serializer, thing.zmq_serializer)

        # req 2 - similarly, serializer keyword argument creates same serialitzer for both zmq and http transports
        serializer = JSONSerializer()
        thing = Thing(instance_name="test_common_serializer", serializer=serializer, log_level=logging.WARN)
        self.assertEqual(thing.zmq_serializer, serializer)
        self.assertEqual(thing.http_serializer, serializer)

        # req 3 - serializer keyword argument must be JSONSerializer only, because this keyword should 
        # what is common to both zmq and http
        with self.assertRaises(TypeError) as ex:
            serializer = PickleSerializer()
            thing = Thing(instance_name="test_common_serializer_nonJSON", serializer=serializer, log_level=logging.WARN)
            self.assertTrue(str(ex), "serializer key word argument must be JSONSerializer")

        # req 4 - zmq_serializer and http_serializer is differently instantiated if zmq_serializer and http_serializer 
        # keyword arguments are provided, albeit the same serializer type
        serializer = JSONSerializer()
        thing = Thing(instance_name="test_common_serializer", zmq_serializer=serializer, log_level=logging.WARN)
        self.assertEqual(thing.zmq_serializer, serializer)
        self.assertNotEqual(thing.http_serializer, serializer) # OR, same as line below
        self.assertNotEqual(thing.http_serializer, thing.zmq_serializer)
        self.assertIsInstance(thing.http_serializer, JSONSerializer)
    

    def test_other_serializers(self):
        print()

        # req 1 - http_serializer cannot be anything except than JSON
        with self.assertRaises(ValueError) as ex:
            # currenty this has written this as ValueError although TypeError is more appropriate
            serializer = PickleSerializer()
            thing = Thing(instance_name="test_http_serializer_nonJSON", http_serializer=serializer, 
                        log_level=logging.WARN)
            self.assertTrue(str(ex), "invalid JSON serializer option")
        # test the same with MsgpackSerializer
        with self.assertRaises(ValueError) as ex:
            # currenty this has written this as ValueError although TypeError is more appropriate
            serializer = MsgpackSerializer()
            thing = Thing(instance_name="test_http_serializer_nonJSON", http_serializer=serializer, 
                        log_level=logging.WARN)
            self.assertTrue(str(ex), "invalid JSON serializer option")

        # req 2 - http_serializer and zmq_serializer can be different
        warnings.filterwarnings("ignore", category=UserWarning)
        http_serializer = JSONSerializer()
        zmq_serializer = PickleSerializer()
        thing = Thing(instance_name="test_different_serializers_1", http_serializer=http_serializer, 
                    zmq_serializer=zmq_serializer, log_level=logging.WARN)
        self.assertNotEqual(thing.http_serializer, thing.zmq_serializer)
        self.assertEqual(thing.http_serializer, http_serializer)
        self.assertEqual(thing.zmq_serializer, zmq_serializer)
        warnings.resetwarnings()

        # try the same with MsgpackSerializer
        http_serializer = JSONSerializer()
        zmq_serializer = MsgpackSerializer()
        thing = Thing(instance_name="test_different_serializers_2", http_serializer=http_serializer, 
                    zmq_serializer=zmq_serializer, log_level=logging.WARN)
        self.assertNotEqual(thing.http_serializer, thing.zmq_serializer)
        self.assertEqual(thing.http_serializer, http_serializer)
        self.assertEqual(thing.zmq_serializer, zmq_serializer)

        # req 3 - pickle serializer should raise warning
        http_serializer = JSONSerializer()
        zmq_serializer = PickleSerializer()
        with self.assertWarns(expected_warning=UserWarning): 
            thing = Thing(instance_name="test_pickle_serializer_warning", http_serializer=http_serializer, 
                    zmq_serializer=zmq_serializer, log_level=logging.WARN)
       



    # def test_schema_validator(self):
    #     # Test the schema_validator property
    #     validator = JsonSchemaValidator()
    #     thing = Thing(instance_name="test_instance", schema_validator=validator)
    #     self.assertEqual(thing.schema_validator, validator)

    def test_state(self):
        print()
        # req 1 - state property must be None when no state machine is present
        thing = Thing(instance_name="test_no_state_machine", log_level=logging.WARN)
        self.assertIsNone(thing.state)
        self.assertFalse(hasattr(thing, 'state_machine'))

    # def test_httpserver_resources(self):
    #     # Test the httpserver_resources property
    #     thing = Thing(instance_name="test_instance")
    #     self.assertIsInstance(thing.httpserver_resources, dict)

    # def test_rpc_resources(self):
    #     # Test the rpc_resources property
    #     thing = Thing(instance_name="test_instance")
    #     self.assertIsInstance(thing.rpc_resources, dict)

    # def test_gui_resources(self):
    #     # Test the gui_resources property
    #     thing = Thing(instance_name="test_instance")
    #     self.assertIsInstance(thing.gui_resources, dict)

    # def test_object_info(self):
    #     # Test the object_info property
    #     thing = Thing(instance_name="test_instance")
    #     self.assertIsInstance(thing.object_info, ThingInformation)

    # def test_run(self):
    #     # Test the run method
    #     thing = Thing(instance_name="test_instance")
    #     thing.run()

    # def test_run_with_http_server(self):
    #     # Test the run_with_http_server method
    #     thing = Thing(instance_name="test_instance")
    #     thing.run_with_http_server()

    # def test_set_properties(self):
    #     # Test the _set_properties action
    #     thing = Thing(instance_name="test_instance")
    #     thing._set_properties(property1="value1", property2="value2")
    #     self.assertEqual(thing.properties.property1, "value1")
    #     self.assertEqual(thing.properties.property2, "value2")

    # def test_add_property(self):
    #     # Test the _add_property action
    #     thing = Thing(instance_name="test_instance")
    #     property_name = "new_property"
    #     property_value = "new_value"
    #     thing._add_property(property_name, property_value)
    #     self.assertEqual(getattr(thing.properties, property_name), property_value)

    # def test_load_properties_from_DB(self):
    #     # Test the load_properties_from_DB action
    #     thing = Thing(instance_name="test_instance")
    #     thing.load_properties_from_DB()
    #     # Add assertions here to check if properties are loaded correctly from the database

    # def test_get_postman_collection(self):
    #     # Test the get_postman_collection action
    #     thing = Thing(instance_name="test_instance")
    #     postman_collection = thing.get_postman_collection()
    #     # Add assertions here to check if the postman_collection is generated correctly

    # def test_get_thing_description(self):
    #     # Test the get_thing_description action
    #     thing = Thing(instance_name="test_instance")
    #     thing_description = thing.get_thing_description()
    #     # Add assertions here to check if the thing_description is generated correctly

    # def test_exit(self):
    #     # Test the exit action
    #     thing = Thing(instance_name="test_instance")
    #     thing.exit()
    #     # Add assertions here to check if the necessary cleanup is performed


if __name__ == '__main__':
    try:
        from utils import TestRunner
    except ImportError:
        from .utils import TestRunner
    unittest.main(testRunner=TestRunner())
