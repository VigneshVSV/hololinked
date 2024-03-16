from hololinked.server import RemoteObject


class Spectrometer(RemoteObject):
    """
    add class doc here
    """
    def __init__(self, instance_name, serial_number, connect, **kwargs):
        super().__init__(instance_name=instance_name, **kwargs)
        self.serial_number = serial_number
        if connect:
            self.connect()

    def connect(self):
        # implemenet logic to connect
        return
    