import socket
import json
import asyncio
import typing
from dataclasses import dataclass, asdict, field

from sqlalchemy import Integer, String, JSON, ARRAY, Boolean
from sqlalchemy import select, create_engine
from sqlalchemy.orm import Session
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase
from argon2 import PasswordHasher
from tornado.httputil import HTTPServerRequest
from tornado.httpclient import AsyncHTTPClient, HTTPRequest

from .serializers import JSONSerializer
from .remote_parameters import TypedList
from .zmq_message_brokers import MessageMappedZMQClientPool
from .webserver_utils import get_IP_from_interface, update_resources_using_client
from .utils import unique_id
from .decorators import post, get, put, delete
from .eventloop import Consumer, EventLoop, fork_empty_eventloop
from .remote_object import RemoteObject, RemoteObjectDB, RemoteObjectMetaclass
from .database import BaseAsyncDB


SERVER_INSTANCE_NAME = 'server-util'
CLIENT_HOST_INSTANCE_NAME = 'dashboard-util'


# /* 
# We want to be able to do the following 

# 1) Add and remove server

# 2) Each server
#     - can be designated as host 
#         - allows DB operations specific to the client
#         - only one such server can exist 
#     - or as normal instrument server 
#         - create new eventloop
#         - create new device
#         - create new HTTP servers
#         - raw input output
#         - have GUI JSON 
# */


class ReactClientUtilities(BaseAsyncDB, RemoteObject): 

    class TableBase(DeclarativeBase):
        pass 
    
    class dashboards(TableBase):
        __tablename__ = "dashboards"

        name : Mapped[str] = mapped_column(String(1024), primary_key = True)
        URL  : Mapped[str] = mapped_column(String(1024), unique = True)
        description : Mapped[str] = mapped_column(String(16384))

        def json(self):
            return {
                "name" : self.name, 
                "URL"  : self.URL, 
                "description" : self.description
            }

    class appsettings(TableBase):
        __tablename__ = "appsettings"

        field : Mapped[str] = mapped_column(String(8192), primary_key = True)
        value : Mapped[typing.Dict[str, typing.Any]] = mapped_column(JSON)

        def json(self):
            return {
                "field" : self.field, 
                "value" : self.value
            }

    class login_credentials(TableBase):
        __tablename__ = "login_credentials"

        username : Mapped[str] = mapped_column(String(1024), primary_key = True)
        password : Mapped[str] = mapped_column(String(1024), unique = True)

    def __init__(self, db_config_file : str, **kwargs) -> None:
        RemoteObject.__init__(self, **kwargs)
        BaseAsyncDB.__init__(self, database='scadapyclient', serializer=self.json_serializer, 
                            config_file=db_config_file)

    @post('/user/add')
    async def add_user(self, username : str, password : str):
        pass 

    @post('/login')
    async def login(self, username : str, password : str):
        async with self.async_session() as session: 
            ph = PasswordHasher(time_cost = 500, memory_cost = 2)
            stmt = select(self.login_credentials).filter_by(username = username)
            data = await session.execute(stmt)
            if data["password"] == ph.hash(password):
                return True
        return False 
    
    @post("/app/settings")
    async def create_app_setting(self, field : str, value : typing.Any):
        async with self.async_session() as session, session.begin():
            session.add(self.appsettings(
                    field = field, 
                    value = {"value" : value}
                )
            )
            session.commit()

    @put("/app/settings")
    async def edit_app_setting(self, field : str, value : typing.Any):
        async with self.async_session() as session, session.begin():
            stmt = select(self.appsettings).filter_by(field = field)
            data = await session.execute(stmt)
            setting = data.scalar()
            setting.value = {"value" : value}
            session.commit()
            return setting

    @get('/app/settings')
    async def all_app_settings(self):
        async with self.async_session() as session:
            stmt = select(self.appsettings)
            data = await session.execute(stmt)
            return {result[self.appsettings.__name__].field : result[self.appsettings.__name__].value["value"] 
                    for result in data.mappings().all()}
        
    @get('/app')
    async def all_app_settings(self):
        async with self.async_session() as session:
            stmt = select(self.appsettings)
            data = await session.execute(stmt)
            return {
                "appsettings" : {result[self.appsettings.__name__].field : result[self.appsettings.__name__].value["value"] 
                    for result in data.mappings().all()}
            }

    @post('/dashboards')
    async def add_dashboards(self, name : str, URL : str, description : str):
        async with self.async_session() as session, session.begin():
            session.add(self.dashboards(
                name = name, 
                URL = URL, 
                description = description
            ))
            await session.commit()

    @get('/dashboards')
    async def query_pages(self):
        async with self.async_session() as session:
            stmt = select(self.dashboards)
            data = await session.execute(stmt)
            return [result[self.dashboards.__name__] for result in data.mappings().all()]           



@dataclass 
class NonDBRemoteObjectInfo:
    instance_name : str
    classname : str
    script : str 

    def json(self):
        return asdict(self)


@dataclass
class SubscribedHTTPServers:
    hostname : str 
    IPAddress : typing.Any
    port : int 
    type : str
    https : bool 
    qualifiedIP : str = field(init = False)

    def __post_init__(self):
        self.qualifiedIP = '{}:{}'.format(self.hostname, self.port)

    def json(self):
        return asdict(self)


@dataclass
class UninstantiatedRemoteObject:
    consumer : RemoteObjectMetaclass
    file_name : str 
    object_name : str
    eventloop_name : str
    id : str 

    def json(self):
        return dict (
            id = self.id, 
            file_name = self.file_name, 
            object_name = self.object_name,
            eventloop_name = self.eventloop_name
        )
    

class HTTPServerUtilities(BaseAsyncDB, RemoteObject):
    """
    HTTPServerUtilities provide functionality to instantiate, kill or get current status of 
    existing remote-objects attached to this server, ability to subscribe to a Primary Host Server 
    which brings remote-objects to the web UI & spawn new event loops   
    """

    type : str = 'NORMAL_REMOTE_OBJECT_SERVER'

    remote_object_info = TypedList(default=None, allow_None=True, item_type=(RemoteObjectDB.RemoteObjectInfo),
                                URL_path='/remote-object-info') 

    def __init__(self, db_config_file : typing.Union[str, None], zmq_client_pool : MessageMappedZMQClientPool, 
                remote_object_info , **kwargs) -> None:
        RemoteObject.__init__(self, **kwargs)
        BaseAsyncDB.__init__(self, database='scadapyserver', serializer=self.json_serializer, config_file=db_config_file)
        self.zmq_client_pool = zmq_client_pool
        self.server_resources = None
        self.remote_object_info = remote_object_info
        self._uninstantiated_remote_objects : typing.Dict[str, UninstantiatedRemoteObject] = {}
        
    @post('/subscribers')
    async def subscribe_to_host(self, host : str, port : int):
        client = AsyncHTTPClient()
        try:
            R = await client.fetch(HTTPRequest(
                    url = "{}/{}/{}".format(host, SERVER_INSTANCE_NAME, 'subscription'),
                    method = 'POST',
                    body = JSONSerializer.general_dumps(dict(
                        hostname=socket.gethostname(),
                        port=port, 
                        type=self.type,
                        https=True
                    ))
                ))
        except Exception as E:
            self.logger.error(f"Could not subscribe to host {host}. error : {str(E)}, error type : {type(E)}.")
            raise
        if R.code == 200 or R.code == 202:
            self.logger.info(f"subsribed successfully to host {host}")
        else:
            raise RuntimeError(f"could not subsribe to host {host}. response {json.loads(R.body)}")
        # we lose the client anyway so we close it. if we decide to reuse the client, changes needed
        client.close() 
    
    @post('/eventloop/new')
    def new_eventloop(self, instance_name, proxy_serializer, json_serializer):
        fork_empty_eventloop(instance_name = instance_name)
        self.zmq_client_pool.register_client(instance_name)
        self.zmq_client_pool[instance_name].handshake()

    @post('/remote-object/import')
    async def import_remote_object(self, file_name : str, object_name : str, eventloop_name : str):
        consumer = EventLoop.import_remote_object(file_name, object_name)
        id = unique_id().decode()
        db_params = consumer.parameters.remote_objects_webgui_info(consumer.parameters.load_at_init_objects())
        self._uninstantiated_remote_objects[id] = UninstantiatedRemoteObject(
            consumer = consumer,
            file_name = file_name, 
            object_name = object_name,
            eventloop_name = eventloop_name,
            id = id
        )
        return {
            "id" : id, 
            "db_params" : db_params
        }

    @delete('/remote-object/import')
    async def del_imported_remote_object(self, id : str):
        obj = self._uninstantiated_remote_objects.get(id, None)
        if obj is None:
            return False 
        elif isinstance(obj, str):
            return await self.zmq_client_pool.async_execute(instance_name = obj, instruction = '/remote-object/import', 
                                            arguments = dict(id = obj) )
        else:  
            self.uninstantiated_remote_objects.pop(id)
            return True
        
    @post('/remote-object/instantiate')
    async def new_remote_object(self, id : str, kwargs : typing.Dict[str, typing.Any], db_params : typing.Dict[str, typing.Any]):
        uninstantiated_remote_object = self._uninstantiated_remote_objects[id]
        consumer = uninstantiated_remote_object.consumer 
        init_params = consumer.param_descriptors.load_at_init_objects()
        for name, value in db_params.items():
            init_params[name].validate_and_adapt(value)
        if uninstantiated_remote_object.eventloop_name not in self.zmq_client_pool:
            fork_empty_eventloop(instance_name = uninstantiated_remote_object.eventloop_name)
            self.zmq_client_pool.register_client(uninstantiated_remote_object.eventloop_name)
            await self.zmq_client_pool[uninstantiated_remote_object.eventloop_name].handshake_complete()
        await self.zmq_client_pool[uninstantiated_remote_object.eventloop_name].async_execute(
            '/remote-object/instantiate', arguments = dict(
                file_name = uninstantiated_remote_object.file_name,
                object_name = uninstantiated_remote_object.object_name, 
                kwargs = kwargs), raise_client_side_exception = True
        )
        if not kwargs.get('instance_name') in self.zmq_client_pool:
            self.zmq_client_pool.register_client(kwargs.get('instance_name'))
        await self.zmq_client_pool[kwargs.get('instance_name')].handshake_complete()
        await update_resources_using_client(self.server_resources,
                            self.remote_object_info, self.zmq_client_pool[kwargs.get('instance_name')])
        await update_resources_using_client(self.server_resources,
                            self.remote_object_info, self.zmq_client_pool[uninstantiated_remote_object.eventloop_name])
        self._uninstantiated_remote_objects.pop(id, None)

    @get('/remote_objects/ping')
    async def ping_consumers(self):
        return await self.zmq_client_pool.ping_all_servers()

    @get('/remote_objects/state')
    async def consumers_state(self):
        return await self.zmq_client_pool.async_execute_in_all_remote_objects('/state', context = {
            "plain_reply" : True    
        })

    @get('/uninstantiated-remote-objects')
    async def uninstantiated_remote_objects(self):
        organised_reply = await self.zmq_client_pool.async_execute_in_all_eventloops('/uninstantiated-remote-objects/read',
                                                                                     context = {
            "plain_reply" : True    
        })
        organised_reply[self.instance_name] = self._uninstantiated_remote_objects
        return organised_reply
    
    @get('/info/all')
    async def info(self):
        consumers_state, uninstantiated_remote_objects  = await asyncio.gather(self.consumers_state(), 
                                                            self.uninstantiated_remote_objects())
        return dict(
            remoteObjectState = consumers_state,
            remoteObjectInfo  = self.remote_object_info,
            uninstantiatedRemoteObjects = uninstantiated_remote_objects
        )
    



class PCHostUtilities(HTTPServerUtilities):
    
    type : str = 'PC_HOST'

    def __init__(self, db_config_file : str, server_network_interface : str, port : int, **kwargs) -> None:
        super().__init__(db_config_file = db_config_file, zmq_client_pool = None, remote_object_info = None, **kwargs)
        self.subscribers : typing.List[SubscribedHTTPServers] = []
        self.own_info = SubscribedHTTPServers(
            hostname=socket.gethostname(),
            IPAddress=get_IP_from_interface(server_network_interface), 
            port= port, 
            type=self.type,
            https=False
        )

    @post('/subscription')
    def subscription(self, hostname : str, port : int, type : str, https : bool, *, request : HTTPServerRequest):
        server = SubscribedHTTPServers(
            hostname=hostname,
            IPAddress=request.remote_ip,
            port=port,
            type=type,
            https=https
        )
        self.subscribers.append(server)
     
    @get('/subscribers')
    def get_subscribers(self):
        return {"subscribers" : self.subscribers + [self.own_info]} 
    
    @post('/starter/run')
    async def starter(self):
        pass


class PrimaryHostUtilities(PCHostUtilities):

    type : str = 'PRIMARY_HOST'

    class TableBase(DeclarativeBase):
        pass 

    class http_server(TableBase):
        __tablename__ = "http_servers"

        hostname : Mapped[str] = mapped_column(String, primary_key = True)
        type    : Mapped[str] = mapped_column(String)
        port    : Mapped[int] = mapped_column(Integer)
        IPAddress : Mapped[str] = mapped_column(String)
        remote_objects : Mapped[typing.List[str]] = mapped_column(ARRAY(String))

    def __init__(self, db_config_file : str, server_network_interface : str, port : int, **kwargs) -> None:
        super().__init__(db_config_file = db_config_file, server_network_interface = server_network_interface, 
                            port = port, **kwargs)
        self.own_info = SubscribedHTTPServers(
            hostname = socket.gethostname(),
            IPAddress = get_IP_from_interface(server_network_interface), 
            port =  port, 
            type = self.type,
            https=False
        )
    
# remote_object_info = [dict(
#     instance_name = 'server-util',
#     **self.class_info() 
# ),
# dict(
#     instance_name = 'dashboard-util',
#     classname = ReactClientUtilities.__name__, 
#     script =  os.path.dirname(os.path.abspath(inspect.getfile(ReactClientUtilities)))
# )],

# remote_object_info = [dict(
#     instance_name = 'server-util',
#     **self.class_info() 
# )],


   
def create_server_tables(serverDB):
    engine = create_engine(serverDB)
    PrimaryHostUtilities.TableBase.metadata.create_all(engine)
    RemoteObjectDB.TableBase.metadata.create_all(engine)
    engine.dispose()

def create_client_tables(clientDB):
    engine = create_engine(clientDB)
    ReactClientUtilities.TableBase.metadata.create_all(engine)
    with Session(engine) as session, session.begin():
        # Pages
        session.add(ReactClientUtilities.appsettings(
            field = 'dashboardsDeleteWithoutAsking',
            value =  {'value' : True}
        ))
        session.add(ReactClientUtilities.appsettings(
            field = 'dashboardsShowRecentlyUsed',
            value =  {'value' : True}
        ))

        # login page
        session.add(ReactClientUtilities.appsettings(
            field = 'loginFooter',
            value =  {'value' : ''}
        ))
        session.add(ReactClientUtilities.appsettings(
            field = 'loginFooterLink',
            value =  {'value' : ''}
        ))
        session.add(ReactClientUtilities.appsettings(
            field = 'loginDisplayFooter',
            value =  {'value' : True}
        ))

        # server
        session.add(ReactClientUtilities.appsettings(
            field = 'serversAllowHTTP',
            value =  {'value' : False}
        ))

        # remote object wizard 
        session.add(ReactClientUtilities.appsettings(
            field = 'remoteObjectViewerConsoleStringifyOutput',
            value =  {'value' : False}
        ))
        session.add(ReactClientUtilities.appsettings(
            field = 'remoteObjectViewerConsoleDefaultMaxEntries',
            value =  {'value' : 15}
        ))
        session.add(ReactClientUtilities.appsettings(
            field = 'remoteObjectViewerConsoleDefaultWindowSize',
            value =  {'value' : 500}
        ))
        session.add(ReactClientUtilities.appsettings(
            field = 'remoteObjectViewerConsoleDefaultFontSize',
            value =  {'value' : 16}
        ))

        session.add(ReactClientUtilities.appsettings(
            field = 'logViewerStringifyOutput',
            value =  {'value' : False}
        ))
        session.add(ReactClientUtilities.appsettings(
            field = 'logViewerDefaultMaxEntries',
            value =  {'value' : 10}
        ))
        session.add(ReactClientUtilities.appsettings(
            field = 'logViewerDefaultOutputWindowSize',
            value =  {'value' : 1000}
        ))
        session.add(ReactClientUtilities.appsettings(
            field = 'logViewerDefaultFontSize',
            value =  {'value' : 16}
        ))

        session.commit()
    engine.dispose()


__all__ = ['ReactClientUtilities']