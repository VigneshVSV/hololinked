import secrets
import os 
import base64
import socket
import json
import asyncio
import ssl
import typing
import getpass
from dataclasses import asdict, field
from argon2 import PasswordHasher

from sqlalchemy import Engine, Integer, String, JSON, ARRAY, Boolean, BLOB
from sqlalchemy import select, create_engine
from sqlalchemy.orm import Session, sessionmaker, Mapped, mapped_column, DeclarativeBase, MappedAsDataclass
from sqlalchemy.ext import asyncio as asyncio_ext
from sqlalchemy_utils import database_exists, create_database, drop_database
from tornado.web import RequestHandler, Application, authenticated
from tornado.httpserver import HTTPServer as TornadoHTTP1Server

from .constants import JSONSerializable
from .serializers import JSONSerializer
from .database import BaseDB

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
            self.set_header("Access-Control-Allow-Origin", "https://localhost:5173")
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
        return True
        return self.get_signed_cookie('user')
        
    def set_default_headers(self) -> None:
        return super().set_default_headers()
        
    async def options(self):
        self.set_status(200)
        self.set_header("Access-Control-Allow-Origin", "https://localhost:5173")
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
        self.set_header("Access-Control-Allow-Origin", "https://localhost:5173")
        self.finish()

    async def options(self):
        self.set_status(200)
        self.set_header("Access-Control-Allow-Origin", "https://localhost:5173")
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
            self.set_header("Access-Control-Allow-Origin", "https://localhost:5173")
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
            self.set_header("Access-Control-Allow-Origin", "https://localhost:5173")
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
        self.set_header("Access-Control-Allow-Origin", "https://localhost:5173")
        self.write("<p>I am alive!!!<p>")
        self.finish()


def create_system_host(config_file : typing.Optional[str] = None, ssl_context : typing.Optional[ssl.SSLContext] = None, 
                    **server_settings) -> TornadoHTTP1Server:
    URL = BaseDB.create_URL(config_file, database='hololinked-host', use_dialect=False)
    if not database_exists(URL): 
        try:
            create_database(URL)
            sync_engine = create_engine(URL)
            HololinkedHostTableBase.metadata.create_all(sync_engine)
            create_tables(sync_engine)
            create_credentials(sync_engine)
            sync_engine.dispose()
        except Exception as ex:
            sync_engine.dispose()
            if URL.startswith("sqlite"):
                os.remove(URL.split('/')[-1])
            else:
                drop_database(URL)
            raise ex from None
    URL = BaseDB.create_URL(config_file, database='hololinked-host', use_dialect=True)
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
        file = open(f"{os.path.dirname(os.path.abspath(__file__))}{os.sep}assets{os.sep}default_host_settings.json", 'r')
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



__all__ = ['create_system_host']