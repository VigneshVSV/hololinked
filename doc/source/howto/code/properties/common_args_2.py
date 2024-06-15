from hololinked.server import RemoteObject, RemoteParameter
from enum import IntEnum


class ErrorCodes(IntEnum):
    IS_NO_SUCCESS = -1
    IS_SUCCESS = 0
    IS_INVALID_CAMERA_HANDLE = 1
    IS_CANT_OPEN_DEVICE = 3
    IS_CANT_CLOSE_DEVICE = 4

    @classmethod
    def json(self):
        # code to code name - opposite of enum definition
        return {value.value : name for name, value in vars(self).items() if isinstance(
                                                                        value, self)}
   

class IDSCamera(RemoteObject):
    """
    Spectrometer example object 
    """
    error_codes = RemoteParameter(readonly=True, default=ErrorCodes.json(), 
                       class_member=True, 
                       doc="error codes raised by IDS library")
    
    def __init__(self, instance_name : str):
        super().__init__(instance_name=instance_name)
        print("error codes", IDSCamera.error_codes) # prints error codes


if __name__ == '__main__':
    IDSCamera(instance_name='test')