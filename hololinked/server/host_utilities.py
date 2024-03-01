import secrets
import os 
import base64
import socket
import json
import asyncio
import ssl
import typing
import getpass
from dataclasses import dataclass, asdict, field
from argon2 import PasswordHasher

from sqlalchemy import Engine, Integer, String, JSON, ARRAY, Boolean
from sqlalchemy import select, create_engine
from sqlalchemy.orm import Session, sessionmaker, Mapped, mapped_column, DeclarativeBase, MappedAsDataclass
from sqlalchemy.ext import asyncio as asyncio_ext
from sqlalchemy_utils import database_exists, create_database, drop_database
from tornado.httpclient import AsyncHTTPClient, HTTPRequest
from tornado.web import RequestHandler, Application, authenticated
from tornado.httpserver import HTTPServer as TornadoHTTP1Server

from .constants import JSONSerializable
from .serializers import JSONSerializer
from .database import BaseDB
from .remote_parameters import TypedList
from .zmq_message_brokers import MessageMappedZMQClientPool
from .webserver_utils import get_IP_from_interface, update_resources_using_client
from .utils import unique_id
from .http_methods import post, get, put, delete
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



global_engine : typing.Optional[Engine] = None
global_session : typing.Optional[Session] = None



class HololinkedHostTableBase(DeclarativeBase):
    pass 
    
class Dashboards(HololinkedHostTableBase, MappedAsDataclass):
    __tablename__ = "dashboards"

    name : Mapped[str] = mapped_column(String(1024), primary_key=True)
    URL  : Mapped[str] = mapped_column(String(1024), unique=True)
    description : Mapped[str] = mapped_column(String(16384))
    json_specfication : Mapped[typing.Dict[str, typing.Any]] = mapped_column(JSON)

    def json(self):
        return asdict(self)

class AppSettings(HololinkedHostTableBase, MappedAsDataclass):
    __tablename__ = "appsettings"

    field : Mapped[str] = mapped_column(String(8192), primary_key=True)
    value : Mapped[typing.Dict[str, typing.Any]] = mapped_column(JSON)

    def json(self):
        return asdict(self)

class LoginCredentials(HololinkedHostTableBase, MappedAsDataclass):
    __tablename__ = "login_credentials"

    email : Mapped[str] = mapped_column(String(1024), primary_key=True)
    password : Mapped[str] = mapped_column(String(1024), unique=True)

class Server(HololinkedHostTableBase, MappedAsDataclass):
    __tablename__ = "http_servers"

    hostname : Mapped[str] = mapped_column(String, primary_key=True)
    type : Mapped[str] = mapped_column(String)
    port : Mapped[int] = mapped_column(Integer)
    IPAddress : Mapped[str] = mapped_column(String)
    remote_objects : Mapped[typing.List[str]] = mapped_column(ARRAY(String))
    https : Mapped[bool] = mapped_column(Boolean) 
    qualifiedIP : Mapped[str] = field(init = False)

    def __post_init__(self):
        self.qualifiedIP = '{}:{}'.format(self.hostname, self.port)

    def json(self):
        return asdict(self)
    
class RemoteObjectInformation(HololinkedHostTableBase, MappedAsDataclass):
    __tablename__ = "remote_objects"

    instance_name  : Mapped[str] = mapped_column(String, primary_key=True)
    class_name     : Mapped[str] = mapped_column(String)
    script         : Mapped[str] = mapped_column(String)
    kwargs         : Mapped[JSONSerializable] = mapped_column(JSON)
    eventloop_instance_name : Mapped[str] = mapped_column(String)
    http_server    : Mapped[str] = mapped_column(String)
    level          : Mapped[int] = mapped_column(Integer)
    level_type     : Mapped[str] = mapped_column(String)

    def json(self):
        return asdict(self)



def for_authenticated_user(method):
    def authenticated_method(self : RequestHandler):
        if not self.current_user:
            self.set_status(403)
            self.set_header("Access-Control-Allow-Origin", "https://127.0.0.1:5173")
            self.finish()
            return
        else:
            print("current user is : ", self.current_user)
        return method(self)
    return authenticated_method


class SystemHostHandler(RequestHandler):

    def check_headers(self):
        content_type = self.request.headers.get("Content-Type", None)
        if content_type and content_type != "application/json":
            self.set_status(500)
            self.write({ "error" : "request body is not JSON." })
            self.finish()

    def get_current_user(self) -> typing.Any:
        return self.get_signed_cookie('user')
        
    def set_default_headers(self) -> None:
        return super().set_default_headers()
        
    async def options(self):
        self.set_status(200)
        self.set_header("Access-Control-Allow-Origin", "https://127.0.0.1:5173")
        self.set_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.set_header("Access-Control-Allow-Headers", "*")
        self.finish()


class UsersHandler(SystemHostHandler):

    async def post(self):
        self.set_status(200)
        self.finish() 

    async def get(self):
        self.set_status(200)
        self.finish()

    
class LoginHandler(SystemHostHandler):

    async def post(self):
        self.check_headers()
        try:
            body = JSONSerializer.generic_loads(self.request.body)
            email = body["email"]
            password = body["password"]
            async with global_session() as session: 
                stmt = select(LoginCredentials).filter_by(email=email)
                data = await session.execute(stmt)
                data : LoginCredentials = data.scalars().all()
            if len(data) == 0:
                self.set_status(403, "authentication failed")
                self.write({"reason" : "no username found"})        
            else:
                ph = PasswordHasher(time_cost=500)
                if ph.verify(data[0].password, password):
                    self.set_status(200)
                    self.set_signed_cookie("user", email)
                else:
                    self.set_status(403, "authentication failed")
                    self.write({"reason" : ""})
        except Exception as ex:
            self.set_status(500, str(ex))
        self.set_header("Access-Control-Allow-Origin", "https://127.0.0.1:5173")
        self.finish()

    async def options(self):
        self.set_status(200)
        self.set_header("Access-Control-Allow-Origin", "https://127.0.0.1:5173")
        self.set_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.set_header("Access-Control-Allow-Headers", "*")
        self.set_header("Access-Control-Allow-Credentials", True)
        self.finish()
    

class AppSettingsHandler(SystemHostHandler):

    @for_authenticated_user
    async def post(self):
        self.check_headers()
        try:
            value = JSONSerializer.generic_loads(self.request.body["value"])
            async with global_session() as session, session.begin():
                session.add(AppSettings(
                        field = field, 
                        value = {"value" : value}
                    )
                )
                await session.commit()
            self.set_status(200)
        except Exception as ex:
            self.set_status(500)
        self.finish()

    @for_authenticated_user
    async def patch(self):
        self.check_headers()
        try:
            value = JSONSerializer.generic_loads(self.request.body)
            field = value["field"]
            value = value["value"]
            async with global_session() as session, session.begin():
                stmt = select(AppSettings).filter_by(field = field)
                data = await session.execute(stmt)
                setting : AppSettings = data.scalar()
                setting.value = {"value" : value}
                await session.commit()
            self.set_status(200)
        except Exception as ex:
            self.set_status(500)
        self.finish()

    @for_authenticated_user
    async def get(self):
        self.check_headers()
        try:
            async with global_session() as session:
                stmt = select(AppSettings)
                data = await session.execute(stmt)
                serialized_data = JSONSerializer.generic_dumps({result[AppSettings.__name__].field : result[AppSettings.__name__].value["value"] 
                    for result in data.mappings().all()})
            self.set_status(200)
            self.set_header("Content-Type", "application/json")
            self.write(serialized_data)            
        except Exception as ex:
            self.set_status(500, str(ex))
        self.finish()

    
class DashboardsHandler(SystemHostHandler):

    @for_authenticated_user
    async def post(self):
        self.check_headers()
        try:
            data = JSONSerializer.generic_loads(self.request.body)
            async with global_session() as session, session.begin():
                session.add(Dashboards(**data))
                await session.commit()
            self.set_status(200)
            self.set_header("Access-Control-Allow-Origin", "https://127.0.0.1:5173")
        except Exception as ex:
            self.set_status(500, str(ex))
        self.finish()

    @for_authenticated_user
    async def get(self):
        self.check_headers()
        try:
            async with global_session() as session:
                stmt = select(Dashboards)
                data = await session.execute(stmt)
                serialized_data = JSONSerializer.generic_dumps([result[Dashboards.__name__]._json() for result 
                                               in data.mappings().all()])           
            self.set_status(200)
            self.set_header("Content-Type", "application/json")
            self.set_header("Access-Control-Allow-Origin", "https://127.0.0.1:5173")
            self.write(serialized_data)
        except Exception as ex:
            self.set_status(500, str(ex))
        self.finish()


class SubscribersHandler(SystemHostHandler):

    @for_authenticated_user
    async def post(self):
        if self.request.headers["Content-Type"] == "application/json":
            self.set_status(200)
            server = SubscribedHTTPServers(**JSONSerializer.generic_loads(self.request.body))
            async with global_session() as session, session.begin():
                session.add(server)
                await session.commit()
            self.finish()

    @for_authenticated_user
    async def get(self):
        self.set_status(200)
        self.set_header("Content-Type", "application/json")
        async with global_session() as session:
            result = select(Server)
            self.write(JSONSerializer.generic_dumps(result.scalars().all()))


class SubscriberHandler(SystemHostHandler):

    async def get(self):
        pass
    


class MainHandler(SystemHostHandler):

    async def get(self):
        self.check_headers()
        self.set_status(200)
        self.set_header("Access-Control-Allow-Origin", "https://127.0.0.1:5173")
        self.write("<p>I am alive!!!<p>")
        self.finish()


def create_primary_host(config_file : str, ssl_context : ssl.SSLContext, **server_settings) -> TornadoHTTP1Server:
    URL = BaseDB.create_URL(config_file, database="hololinked-host")
    if not database_exists(URL): 
        try:
            create_database(URL)
            sync_engine = create_engine(URL)
            HololinkedHostTableBase.metadata.create_all(sync_engine)
            create_tables(sync_engine)
            create_credentials(sync_engine)
        except Exception as ex:
            drop_database(URL)
            raise ex from None

    global global_engine, global_session
    global_engine = asyncio_ext.create_async_engine(URL, echo=True)
    global_session = sessionmaker(global_engine, expire_on_commit=True, 
                                    class_=asyncio_ext.AsyncSession) # type: ignore

    app = Application([
        (r"/", MainHandler),
        (r"/users", UsersHandler),
        (r"/dashboards", DashboardsHandler),
        (r"/settings", AppSettingsHandler),
        (r"/subscribers", SubscribersHandler),
        # (r"/remote-objects", RemoteObjectsHandler),
        (r"/login", LoginHandler)
    ], cookie_secret=base64.b64encode(os.urandom(32)).decode('utf-8'), 
    **server_settings)
    
    return TornadoHTTP1Server(app, ssl_options=ssl_context)
 


def create_tables(engine):
    with Session(engine) as session, session.begin():
        file = open("default_host_settings.json", 'r')
        default_settings = JSONSerializer.generic_load(file)
        for name, settings in default_settings.items():
            session.add(AppSettings(
                field = name,
                value = settings
            ))
    session.commit()


def create_credentials(sync_engine):
    """
    create name and password for a new user in a database 
    """
    
    print("Requested primary host seems to use a new database. Give username and password (not for database server, but for client logins from hololinked-portal) : ")
    email = input("email-id (not collected anywhere else excepted your own database) : ")
    while True:
        password = getpass.getpass("password : ")
        password_confirm = getpass.getpass("repeat-password : ")
        if password != password_confirm:
            print("password & repeat password not the same. Try again.")
            continue
        with Session(sync_engine) as session, session.begin():
            ph = PasswordHasher(time_cost=500)
            session.add(LoginCredentials(email=email, password=ph.hash(password)))
        session.commit()
        return 
    raise RuntimeError("password not created, aborting database creation.")


@dataclass 
class NonDBRemoteObjectInfo:
    instance_name : str
    classname : str
    script : str 

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
    

class SystemHost(HTTPServer):
    """
    HTTPServerUtilities provide functionality to instantiate, kill or get current status of 
    existing remote-objects attached to this server, ability to subscribe to a Primary Host Server 
    which brings remote-objects to the web UI & spawn new event loops   
    """

    type : str = 'NORMAL_REMOTE_OBJECT_SERVER'

    remote_object_info = TypedList(default=None, allow_None=True, 
                                URL_path='/remote-object-info') 

    def __init__(self, db_config_file : typing.Union[str, None], zmq_client_pool : MessageMappedZMQClientPool, 
                remote_object_info , **kwargs) -> None:
        RemoteObject.__init__(self, **kwargs)
        BaseAsyncDB.__init__(self, database='scadapyserver', serializer=self.json_serializer, config_file=db_config_file)
        self.zmq_client_pool = zmq_client_pool
        self.server_resources = None
        self.remote_object_info = remote_object_info
        self._uninstantiated_remote_objects : typing.Dict[str, UninstantiatedRemoteObject] = {}
        
    @post('/subscribe')
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



__all__ = ['create_primary_host']