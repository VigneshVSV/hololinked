from hololinked.server import Thing, Property, action, Event

class Spectrometer(Thing):
    """
    add class doc here
    """
    def __init__(self, instance_name, serial_number, autoconnect, **kwargs):
        super().__init__(instance_name=instance_name, **kwargs)
        self.serial_number = serial_number
        if autoconnect:
            self.connect()

    def connect(self):
        """implemenet device driver logic to connect to hardware"""
        pass
    