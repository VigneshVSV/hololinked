from sqlalchemy_utils import create_database, database_exists
import logging

from ..param.parameters import String, TypedList
from .HTTPServer import HTTPServer
from .eventloop import Consumer
from .host_utilities import (ReactClientUtilities, PrimaryHostUtilities, create_client_tables, create_server_tables,
                        SERVER_INSTANCE_NAME, CLIENT_HOST_INSTANCE_NAME)
from .database import create_DB_URL



class PCHostServer(HTTPServer):

    consumers = TypedList(item_type=Consumer, default=None, allow_None=True, 
                   doc="""Remote Object to be directly served within the HTTP server""")
    
    db_config_file = String(default='')

    def __init__(self, *, port = 8080, address = '0.0.0.0', log_level = logging.INFO, 
                db_config_file = 'host_db_config.json', json_serializer = None, protocol_version = 2, **kwargs):
        super().__init__(
            consumers = None, 
            port = port, 
            address = address, 
            logger = kwargs.get('logger', None), 
            log_level = log_level, 
            json_serializer = json_serializer, 
            protocol_version = protocol_version
        )



class PrimaryHostServer(HTTPServer):

    consumers = TypedList(item_type=Consumer, default=None, allow_None=True, 
                    doc="""Remote Object to be directly served within the HTTP server""")
    
    db_config_file = String(default='')

    def __init__(self, *, port = 8080, address = '0.0.0.0', log_level = logging.INFO, 
                db_config_file = 'host_db_config.json', json_serializer = None, protocol_version = 2, **kwargs):
        super().__init__(
            consumers = None, 
            port = port, 
            address = address, 
            logger = kwargs.get('logger', None), 
            log_level = log_level, 
            json_serializer = json_serializer, 
            protocol_version = protocol_version
        )
        self.db_config_file = db_config_file
        self.create_databases()

    @property
    def all_ok(self, boolean=False):
        super().all_ok
        react_client_utilities = Consumer(ReactClientUtilities, db_config_file = self.db_config_file,
                                            instance_name = CLIENT_HOST_INSTANCE_NAME, logger = self.logger)
        server_side_utilities  = Consumer(PrimaryHostUtilities, db_config_file = self.db_config_file, 
                                            instance_name = SERVER_INSTANCE_NAME, server_network_interface = 'Wi-Fi',
                                            port = self.port, logger = self.logger)
        self.consumers = [react_client_utilities, server_side_utilities]
        return True

    def create_databases(self):
        URL = create_DB_URL(self.db_config_file)
        serverDB = f"{URL}/scadapyserver"
        if not database_exists(serverDB): 
            create_database(serverDB)
            create_server_tables(serverDB)
        clientDB = f"{URL}/scadapyclient"
        if not database_exists(clientDB):
            create_database(clientDB)
            create_client_tables(clientDB)

    

__all__ = ['PCHostServer', 'PrimaryHostServer']