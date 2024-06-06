from hololinked.client import ObjectProxy
from hololinked.server import EventLoop

eventloop_proxy = ObjectProxy(instance_name='eventloop', protocol="TCP",
                            socket_address="tcp://192.168.0.10:60000") #type: EventLoop
obj_id = eventloop_proxy.import_remote_object(file_name=r"D:\path\to\file\IDSCamera",
                                    object_name="UEyeCamera")
eventloop_proxy.instantiate(obj_id, instance_name='camera', device_id=3)