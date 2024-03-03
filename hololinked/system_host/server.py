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
import uuid
from argon2 import PasswordHasher

from sqlalchemy import Engine
from sqlalchemy import select, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.ext import asyncio as asyncio_ext
from sqlalchemy_utils import database_exists, create_database, drop_database
from tornado.web import RequestHandler, Application
from tornado.httpserver import HTTPServer as TornadoHTTP1Server

from ..server.serializers import JSONSerializer
from ..server.database import BaseDB
from .models import *

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


def for_authenticated_user(method):
    def authenticated_method(self : "SystemHostHandler"):
        if not self.current_user_valid:
            self.set_status(403)
            self.set_header("Access-Control-Allow-Origin", self.CORS)
            self.finish()
            return
        else:
            print("current user is : ", self.current_user)
        return method(self)
    return authenticated_method


class SystemHostHandler(RequestHandler):
    """
    Base Request Handler for all requests directed to system host server. Implements 
    CORS & credential checks. 
    """

    CORS : typing.List[str] 

    def check_headers(self):
        """
        check suitable values for headers before processing the request
        """
        content_type = self.request.headers.get("Content-Type", None)
        if content_type and content_type != "application/json":
            self.set_status(400, "request body is not JSON.")
            self.finish()

    @property
    def current_user_valid(self) -> bool:
        """
        check if current user is a valid user for accessing authenticated resources
        """
        if self.get_signed_cookie('user', None):
            return True 
        
    def get_current_user(self) -> typing.Any:
        return self.get_signed_cookie('user', None)
    
    def set_access_control_allow_origin(self) -> None:
        """
        For credential login, access control allow origin cannot be *,
        See: https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS#examples_of_access_control_scenarios
        """
        origin = self.request.headers.get("Origin")
        if origin is not None and (origin in self.CORS or origin + '/' in self.CORS):
            self.set_header("Access-Control-Allow-Origin", self.CORS)
             
    def set_access_control_allow_headers(self) -> None:
        """
        For credential login, access control allow headers cannot be *. 
        See: https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS#examples_of_access_control_scenarios
        """
        headers = ", ".join(self.request.headers.keys())
        if self.request.headers.get("Access-Control-Request-Headers", None):
            headers += ", " + self.request.headers["Access-Control-Request-Headers"]
        self.set_header("Access-Control-Allow-Headers", headers)
   
    def set_default_headers(self) -> None:
        self.set_access_control_allow_origin()
        self.set_access_control_allow_headers()
        self.set_header("Access-Control-Allow-Credentials", "true")
        return super().set_default_headers()

    async def options(self):
        self.set_status(200)
        # self.set_access_control_allow_origin()
        # self.set_access_control_allow_headers()
        # self.set_header("Access-Control-Allow-Headers", "*")
        # self.set_header("Access-Control-Allow-Origin", self.CORS)
        self.set_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
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
                data = data.scalars().all() # type: typing.List[LoginCredentials]
            if len(data) == 0:
                self.set_status(403, "authentication failed - no username found")    
            else:
                data = data[0] # type: LoginCredentials
                ph = PasswordHasher(time_cost=500)
                if ph.verify(data.password, password):
                    self.set_status(200)
                    self.set_signed_cookie("user", str(uuid.uuid4()), 
                                secure=True, samesite="strict", domain="localhost") # note - CSF can occur
                            # domain=".app.localhost")
        except Exception as ex:
            self.set_status(500, f"authentication failed - {str(ex)}")
        # self.set_header("Access-Control-Allow-Origin", self.CORS)
        # self.set_header("Access-Control-Allow-Credentials", "true")
        self.finish()

    async def options(self):
        self.set_status(200)
        # self.set_header("Access-Control-Allow-Headers", "*")
        # self.set_header("Access-Control-Allow-Origin", self.CORS)
        # self.set_header("Access-Control-Allow-Credentials", "true")
        self.set_header("Access-Control-Allow-Methods", "POST, OPTIONS")
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
            self.set_status(500, str(ex))
        # self.set_header("Access-Control-Allow-Origin", self.CORS)
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
            self.set_status(500, str(ex))
        # self.set_header("Access-Control-Allow-Origin", self.CORS)
        self.finish()

    @for_authenticated_user
    async def get(self):
        self.check_headers()
        try:
            async with global_session() as session:
                stmt = select(AppSettings)
                data = await session.execute(stmt)
                serialized_data = JSONSerializer.generic_dumps({result[AppSettings.__name__].field : result[AppSettings.__name__].value
                    for result in data.mappings().all()})
            self.set_status(200)
            self.set_header("Content-Type", "application/json")
            self.write(serialized_data)            
        except Exception as ex:
            self.set_status(500, str(ex))
        # self.set_header("Access-Control-Allow-Origin", self.CORS)
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
        except Exception as ex:
            self.set_status(500, str(ex))
        # self.set_header("Access-Control-Allow-Origin", self.CORS)
        # self.set_header("Access-Control-Allow-Credentials", "true")
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
            self.write(serialized_data)
        except Exception as ex:
            self.set_status(500, str(ex))
        # self.set_header("Access-Control-Allow-Origin", self.CORS)
        # self.set_header("Access-Control-Allow-Credentials", "true")
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
        # self.set_header("Access-Control-Allow-Origin", self.CORS)
        # self.set_header("Access-Control-Allow-Credentials", "true")
        self.write("<p>I am alive!!!<p>")
        self.finish()


def create_system_host(db_config_file : typing.Optional[str] = None, ssl_context : typing.Optional[ssl.SSLContext] = None, 
                    **server_settings) -> TornadoHTTP1Server:
    """
    global function for creating system hosting server using a database configuration file, SSL context & certain 
    server settings. Currently supports only one server per process due to usage of some global variables. 

    Parameters
    ----------

    """
    URL = BaseDB.create_URL(db_config_file, database='hololinked-host', use_dialect=False)
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
    
    global global_engine, global_session
    URL = BaseDB.create_URL(db_config_file, database='hololinked-host', use_dialect=True)
    global_engine = asyncio_ext.create_async_engine(URL, echo=True)
    global_session = sessionmaker(global_engine, expire_on_commit=True, 
                                    class_=asyncio_ext.AsyncSession) # type: ignore
    
    CORS = server_settings.pop("CORS", [])
    if not isinstance(CORS, (str, list)):
        raise TypeError("CORS should be a list of strings or a string")
    if isinstance(CORS, list):
        CORS = ', '.join(CORS)
    SystemHostHandler.CORS = CORS

    app = Application([
        (r"/", MainHandler),
        (r"/users", UsersHandler),
        (r"/dashboards", DashboardsHandler),
        (r"/app-settings", AppSettingsHandler),
        (r"/subscribers", SubscribersHandler),
        # (r"/remote-objects", RemoteObjectsHandler),
        (r"/login", LoginHandler)
    ], 
    cookie_secret=base64.b64encode(os.urandom(32)).decode('utf-8'), 
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