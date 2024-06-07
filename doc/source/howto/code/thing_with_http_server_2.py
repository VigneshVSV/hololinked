from hololinked.server import Thing, action, HTTP_METHODS
from hololinked.server.properties import Integer, Selector, Number, Boolean, ClassSelector


class Axis(Thing):
    """
    Represents a single stepper module of a Phytron Phymotion Control Rack
    """

    def get_referencing_run_frequency(self):
        resp = self.execute('P08R')
        return int(resp)

    def set_referencing_run_frequency(self, value):
        self.execute('P08S{}'.format(value))

    referencing_run_frequency = Number(bounds=(0, 40000),             
                        inclusive_bounds=(False, True), step=100,
                        URL_path='/frequencies/referencing-run',
                        fget=get_referencing_run_frequency, 
                        fset=set_referencing_run_frequency,
                        doc="""Run frequency during initializing (referencing), 
                            in Hz (integer value).
                            I1AM0x: 40 000 maximum, I4XM01: 4 000 000 maximum""" 
                    )