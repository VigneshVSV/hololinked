import secrets
import os 
import base64
import socket
import json
import asyncio
import ssl
import typing
import getpass
from argon2 import PasswordHasher

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.ext import asyncio as asyncio_ext
from sqlalchemy_utils import database_exists, create_database, drop_database
from tornado.web import Application, StaticFileHandler
from tornado.routing import RuleRouter, PathMatches
from tornado.httpserver import HTTPServer as TornadoHTTP1Server

from ..server.serializers import JSONSerializer
from ..server.database import BaseDB
from ..server.config import global_config
from .models import *
from .handlers import *


def create_system_host(db_config_file : typing.Optional[str] = None, ssl_context : typing.Optional[ssl.SSLContext] = None, 
                    **server_settings) -> TornadoHTTP1Server:
    """
    global function for creating system hosting server using a database configuration file, SSL context & certain 
    server settings. Currently supports only one server per process due to usage of some global variables. 

    Parameters
    ----------

    """
    disk_DB_URL = BaseDB.create_postgres_URL(db_config_file, database='hololinked-host', use_dialect=False)
    if not database_exists(disk_DB_URL): 
        try:
            create_database(disk_DB_URL)
            sync_disk_db_engine = create_engine(disk_DB_URL)
            HololinkedHostTableBase.metadata.create_all(sync_disk_db_engine)
            # create_tables(sync_disk_db_engine)
            create_credentials(sync_disk_db_engine)
        except Exception as ex:
            if disk_DB_URL.startswith("sqlite"):
                os.remove(disk_DB_URL.split('/')[-1])
            else:
                drop_database(disk_DB_URL)
            raise ex from None
        finally:
            sync_disk_db_engine.dispose()
            
    disk_DB_URL = BaseDB.create_postgres_URL(db_config_file, database='hololinked-host', use_dialect=True)
    disk_engine = asyncio_ext.create_async_engine(disk_DB_URL, echo=True)
    disk_session = sessionmaker(disk_engine, expire_on_commit=True, 
                                    class_=asyncio_ext.AsyncSession) # type: asyncio_ext.AsyncSession
    
    mem_DB_URL = BaseDB.create_sqlite_URL(in_memory=True)
    mem_engine = create_engine(mem_DB_URL, echo=True) 
    mem_session = sessionmaker(mem_engine, expire_on_commit=True, 
                                    class_=Session) # type: Session
    HololinkedHostInMemoryTableBase.metadata.create_all(mem_engine)
    
    CORS = server_settings.pop("CORS", [])
    if not isinstance(CORS, (str, list)):
        raise TypeError("CORS should be a list of strings or a string")
    if isinstance(CORS, str):
        CORS = [CORS]
    kwargs = dict(
        CORS=CORS,
        disk_session=disk_session,
        mem_session=mem_session
    )

    app = Application([
        (r"/", MainHandler, dict(IP="https://localhost:8080", swagger=True, **kwargs)),
        (r"/users", UsersHandler, kwargs),
        (r"/dashboards", DashboardsHandler, kwargs),
        (r"/app-settings", AppSettingsHandler, kwargs),
        (r"/subscribers", SubscribersHandler, kwargs),
        # (r"/remote-objects", RemoteObjectsHandler),
        (r"/login", LoginHandler, kwargs),
        (r"/logout", LogoutHandler, kwargs),
        (r"/swagger-ui", SwaggerUIHandler, kwargs),
        (r"/(.*)", StaticFileHandler, { "path" : os.path.join(os.path.dirname(__file__),
                    f"assets{os.sep}hololinked-server-swagger-api{os.sep}system-host-api") }),
    ], 
    cookie_secret=base64.b64encode(os.urandom(32)).decode('utf-8'), 
    **server_settings)
    
    return TornadoHTTP1Server(app, ssl_options=ssl_context, auto)
 


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
            ph = PasswordHasher(time_cost=global_config.PWD_HASHER_TIME_COST)
            session.add(LoginCredentials(email=email, password=ph.hash(password)))
        session.commit()
        return 
    raise RuntimeError("password not created, aborting database creation.")


def delete_database(db_config_file):
    # config_file = str(Path(os.path.dirname(__file__)).parent) + "\\assets\\db_config.json"
    URL = BaseDB.create_URL(db_config_file, database="hololinked-host", use_dialect=False)
    drop_database(URL)



__all__ = ['create_system_host']