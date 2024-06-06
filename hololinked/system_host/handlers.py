import os
import socket
import uuid
import typing
import copy
from typing import List
from argon2 import PasswordHasher

from sqlalchemy import select, delete, update
from sqlalchemy.orm import Session
from sqlalchemy.ext import asyncio as asyncio_ext
from sqlalchemy.exc import SQLAlchemyError
from tornado.web import RequestHandler, HTTPError, authenticated 


from .models import *
from ..server.serializers import JSONSerializer
from ..server.config import global_config
from ..server.utils import get_IP_from_interface


def for_authenticated_user(method):
    async def authenticated_method(self : "SystemHostHandler", *args, **kwargs) -> None:
        if self.current_user_valid:
            return await method(self, *args, **kwargs)
        self.set_status(403)
        self.set_custom_default_headers()
        self.finish()
        return
    return authenticated_method


class SystemHostHandler(RequestHandler):
    """
    Base Request Handler for all requests directed to system host server. Implements CORS & credential checks. 
    Use built in swagger-ui for request handler documentation for other paths. 
    """

    def initialize(self, CORS : typing.List[str], disk_session : Session, mem_session : asyncio_ext.AsyncSession) -> None:
        self.CORS = CORS 
        self.disk_session = disk_session
        self.mem_session = mem_session

    @property
    def headers_ok(self):
        """
        check suitable values for headers before processing the request
        """
        content_type = self.request.headers.get("Content-Type", None)
        if content_type and content_type != "application/json":
            self.set_status(400, "request body is not JSON.")
            self.finish()
            return False 
        return True

    @property
    def current_user_valid(self) -> bool:
        """
        check if current user is a valid user for accessing authenticated resources
        """
        user = self.get_signed_cookie('user', None) 
        if user is None:
            return False
        with self.mem_session() as session:
            session : Session
            stmt = select(UserSession).filter_by(session_key=user)
            data = session.execute(stmt)
            data = data.scalars().all()
            if len(data) == 0:
                return False
            if len(data) > 1:
                raise HTTPError("session ID not unique, internal logic error - contact developers (https://github.com/VigneshVSV/hololinked/issues)") 
            data = data[0]
            if (data.session_key == user and data.origin == self.request.headers.get("Origin") and
                    data.user_agent == self.request.headers.get("User-Agent") and data.remote_IP == self.request.remote_ip):
                return True        
            
    def get_current_user(self) -> typing.Any:
        """
        gets the current logged in user - call after ``current_user_valid``
        """
        return self.get_signed_cookie('user', None) 
      
    def set_access_control_allow_origin(self) -> None:
        """
        For credential login, access control allow origin cannot be '*',
        See: https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS#examples_of_access_control_scenarios
        """
        origin = self.request.headers.get("Origin")
        if origin is not None and (origin in self.CORS or origin + '/' in self.CORS):
            self.set_header("Access-Control-Allow-Origin", origin)
             
    def set_access_control_allow_headers(self) -> None:
        """
        For credential login, access control allow headers cannot be '*'. 
        See: https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS#examples_of_access_control_scenarios
        """
        headers = ", ".join(self.request.headers.keys())
        if self.request.headers.get("Access-Control-Request-Headers", None):
            headers += ", " + self.request.headers["Access-Control-Request-Headers"]
        self.set_header("Access-Control-Allow-Headers", headers)

    def set_access_control_allow_methods(self) -> None:
        """
        sets methods allowed so that options method can be reused in all children
        """
        self.set_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
   
    def set_custom_default_headers(self) -> None:
        """
        sets access control allow origin, allow headers and allow credentials 
        """
        self.set_access_control_allow_origin()
        self.set_access_control_allow_headers()
        self.set_header("Access-Control-Allow-Credentials", "true")
      
    async def options(self):
        self.set_status(204)
        self.set_access_control_allow_methods()
        self.set_custom_default_headers()
        self.finish()


class UsersHandler(SystemHostHandler):

    async def post(self):
        self.set_status(200)
        self.finish() 

    async def get(self):
        self.set_status(200)
        self.finish()

    
class LoginHandler(SystemHostHandler):
    """
    performs login and supplies a signed cookie for session
    """
    async def post(self):
        if not self.headers_ok: 
            return
        try:
            body = JSONSerializer.generic_loads(self.request.body)
            email = body["email"]
            password = body["password"]
            rememberme = body["rememberme"]
            async with self.disk_session() as session: 
                session : asyncio_ext.AsyncSession
                stmt = select(LoginCredentials).filter_by(email=email)
                data = await session.execute(stmt)
                data = data.scalars().all() # type: typing.List[LoginCredentials]
            if len(data) == 0:
                self.set_status(404, "authentication failed - username not found")    
            else:
                data = data[0] # type: LoginCredentials
                ph = PasswordHasher(time_cost=global_config.PWD_HASHER_TIME_COST)
                if ph.verify(data.password, password):
                    self.set_status(204, "logged in")
                    cookie_value = bytes(str(uuid.uuid4()), encoding = 'utf-8')
                    self.set_signed_cookie("user", cookie_value, httponly=True,  
                                            secure=True, samesite="strict", 
                                            expires_days=30 if rememberme else None)
                with self.mem_session() as session:
                    session : Session
                    session.add(UserSession(email=email, session_key=cookie_value,
                            origin=self.request.headers.get("Origin"),
                            user_agent=self.request.headers.get("User-Agent"),
                            remote_IP=self.request.remote_ip
                        )
                    )
                    session.commit()
        except Exception as ex:
            ex_str = str(ex)
            if ex_str.startswith("password does not match"):
                ex_str = "username or password not correct"
            self.set_status(500, f"authentication failed - {ex_str}")
        self.set_custom_default_headers()
        self.finish()
        
    def set_access_control_allow_methods(self) -> None:
        self.set_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")


class LogoutHandler(SystemHostHandler):
    """
    Performs logout and clears the signed cookie of session
    """

    @for_authenticated_user
    async def post(self):
        if not self.headers_ok: 
            return
        try:
            if not self.current_user_valid:
                self.set_status(409, "not a valid user to logout")
            else: 
                user = self.get_current_user() 
                with self.mem_session() as session:
                    session : Session 
                    stmt = delete(UserSession).filter_by(session_key=user)
                    result = session.execute(stmt)
                    if result.rowcount != 1:
                        self.set_status(500, "found user but could not logout") # never comes here
                    session.commit()
                self.set_status(204, "logged out")
                self.clear_cookie("user")   
        except Exception as ex:
            self.set_status(500, f"logout failed - {str(ex)}")
        self.set_custom_default_headers()
        self.finish()
        
    def set_access_control_allow_methods(self) -> None:
        self.set_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        

class WhoAmIHandler(SystemHostHandler):

    @for_authenticated_user
    async def get(self):
        
        with self.mem_session() as session:
            session : Session
            stmt = select(UserSession).filter_by(session_key=user)
            data = session.execute(stmt)
            data = data.scalars().all()
    
            user = self.get_current_user() 
            with self.mem_session() as session:
                session : Session 
                stmt = delete(UserSession).filter_by(session_key=user)
                result = session.execute(stmt)
                if result.rowcount != 1:
                    self.set_status(500, "found user but could not logout") # never comes here
                session.commit()
            self.set_status(204, "logged out")
            self.clear_cookie("user")   



class AppSettingsHandler(SystemHostHandler):

    @for_authenticated_user
    async def get(self, field : typing.Optional[str] = None):
        if not self.headers_ok:
            return  
        try:
            async with self.disk_session() as session:
                session : asyncio_ext.AsyncSession
                stmt = select(AppSettings)
                data = await session.execute(stmt)
                serialized_data = JSONSerializer.generic_dumps({
                    result[AppSettings.__name__].field : result[AppSettings.__name__].value
                    for result in data.mappings().all()})
            self.set_status(200)
            self.set_header("Content-Type", "application/json")
            self.write(serialized_data)            
        except Exception as ex:
            self.set_status(500, str(ex))
        self.set_custom_default_headers()
        self.finish()

    async def options(self, name : typing.Optional[str] = None):
        self.set_status(204)
        self.set_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.set_custom_default_headers()
        self.finish()  
    

class AppSettingHandler(SystemHostHandler):

    @for_authenticated_user
    async def post(self):
        if not self.headers_ok: 
            return
        try:
            value = JSONSerializer.generic_loads(self.request.body["value"])
            async with self.disk_session() as session:
                session : asyncio_ext.AsyncSession
                session.add(AppSettings(
                    field = field, 
                    value = {"value" : value}
                ))
                await session.commit()
            self.set_status(200)
        except SQLAlchemyError as ex:
            self.set_status(500, "Database error - check message on server")
        except Exception as ex:
            self.set_status(500, str(ex))
        self.set_custom_default_headers()
        self.finish()

    @for_authenticated_user
    async def patch(self, field : str):
        if not self.headers_ok: 
            return
        try:
            value = JSONSerializer.generic_loads(self.request.body)
            if field == 'remote-object-viewer':
                field = 'remoteObjectViewer'
            async with self.disk_session() as session, session.begin():
                session : asyncio_ext.AsyncSession
                stmt = select(AppSettings).filter_by(field=field)
                data = await session.execute(stmt)
                setting : AppSettings = data.scalar()
                new_value = copy.deepcopy(setting.value)
                self.deepupdate_dict(new_value, value)
                setting.value = new_value
                await session.commit()
            self.set_status(200)
        except Exception as ex:
            self.set_status(500, str(ex))
        self.set_custom_default_headers()
        self.finish()

    async def options(self, name : typing.Optional[str] = None):
        self.set_status(204)
        self.set_header("Access-Control-Allow-Methods", "POST, PATCH, OPTIONS")
        self.set_custom_default_headers()
        self.finish()

    def deepupdate_dict(self, d : dict, u : dict):
        for k, v in u.items():
            if isinstance(v, dict):
                d[k] = self.deepupdate_dict(d.get(k, {}), v)
            else:
                d[k] = v
        return d

    
class PagesHandler(SystemHostHandler):
    """
    get all pages - endpoint /pages
    """

    @for_authenticated_user
    async def get(self):
        if not self.headers_ok:
            return 
        try:
            async with self.disk_session() as session:
                session : asyncio_ext.AsyncSession
                stmt = select(Pages)
                data = await session.execute(stmt)
                serialized_data = JSONSerializer.generic_dumps([result[Pages.__name__].json() for result 
                                               in data.mappings().all()])           
            self.set_status(200)
            self.set_header("Content-Type", "application/json")
            self.write(serialized_data)
        except SQLAlchemyError as ex:
            self.set_status(500, "database error - check message on server")
        except Exception as ex:
            self.set_status(500, str(ex))
        self.set_custom_default_headers()
        self.finish()


class PageHandler(SystemHostHandler):
    """
    add or edit a single page. endpoint - /pages/{name}
    """

    @for_authenticated_user
    async def post(self, name):
        if not self.headers_ok:
            return 
        try:
            data = JSONSerializer.generic_loads(self.request.body)
            # name = self.request.arguments
            async with self.disk_session() as session, session.begin():
                session : asyncio_ext.AsyncSession
                session.add(Pages(name=name, **data))
                await session.commit()
            self.set_status(201)
        except SQLAlchemyError as ex:
            self.set_status(500, "Database error - check message on server")
        except Exception as ex:
            self.set_status(500, str(ex))
        self.set_custom_default_headers()
        self.finish()

    @for_authenticated_user
    async def put(self, name):
        if not self.headers_ok:
            return 
        try:
            updated_data = JSONSerializer.generic_loads(self.request.body)
            async with self.disk_session() as session, session.begin():
                session : asyncio_ext.AsyncSession
                stmt = select(Pages).filter_by(name=name)
                page = (await session.execute(stmt)).mappings().all()
                if(len(page) == 0):
                    self.set_status(404, f"no such page with given name {name}") 
                else:
                    existing_data = page[0][Pages.__name__] # type: Pages
                    if updated_data.get("description", None):
                        existing_data.description = updated_data["description"]
                    if updated_data.get("URL", None):
                        existing_data.URL = updated_data["URL"]
                    await session.commit()
                self.set_status(204)
        except SQLAlchemyError as ex:
            self.set_status(500, "Database error - check message on server")
        except Exception as ex:
            self.set_status(500, str(ex))
        self.set_custom_default_headers()
        self.finish()


    @for_authenticated_user
    async def delete(self, name):
        if not self.headers_ok:
            return 
        try:
            async with self.disk_session() as session, session.begin():
                session : asyncio_ext.AsyncSession
                stmt = delete(Pages).filter_by(name=name)
                ret = await session.execute(stmt)
                await session.commit()
            self.set_status(204)
        except SQLAlchemyError as ex:
            self.set_status(500, "Database error - check message on server")
        except Exception as ex:
            self.set_status(500, str(ex))
        self.set_custom_default_headers()
        self.finish()

    async def options(self, name):
        print("name is ", name)
        self.set_status(204)
        self.set_header("Access-Control-Allow-Methods", "POST, PUT, DELETE, OPTIONS")
        self.set_custom_default_headers()
        self.finish()


class SubscribersHandler(SystemHostHandler):

    async def post(self):
        if not self.headers_ok:
            return 
        try: 
            server = Server(**JSONSerializer.generic_loads(self.request.body))
            async with self.disk_session() as session, session.begin():
                session : asyncio_ext.AsyncSession
                session.add(server)
                await session.commit()
            self.set_status(201)
        except SQLAlchemyError as ex:
            self.set_status(500, "Database error - check message on server")
        except Exception as ex:
            self.set_status(500, str(ex))
        self.set_custom_default_headers()
        self.finish()

    async def get(self):
        if not self.headers_ok:
            return 
        try: 
            async with self.disk_session() as session, session.begin():
                session : asyncio_ext.session
                stmt = select(Server)
                result = await session.execute(stmt)
                serialized_data = JSONSerializer.generic_dumps([val[Server.__name__].json() for val in result.mappings().all()])
            self.set_status(200)
            self.set_header("Content-Type", "application/json")
            self.write(serialized_data)
        except SQLAlchemyError as ex:
            self.set_status(500, "Database error - check message on server")
        except Exception as ex: 
            self.set_status(500, str(ex))
        self.set_custom_default_headers()
        self.finish()

    async def put(self):
        if not self.headers_ok:
            return 
        try: 
            server = JSONSerializable.loads(self.request.body)
            async with self.disk_session() as session, session.begin():
                session : asyncio_ext.session
                stmt = select(Server).filter_by(name=server.get("name", None))
                result = (await session.execute(stmt)).mappings().all()
                if len(result) == 0:
                    self.set_status(404)
                else: 
                    result = result[0][Server.__name__] # type: Server
                    await session.commit()            
                    self.set_status(204)
        except SQLAlchemyError as ex:
            self.set_status(500, "Database error - check message on server")
        except Exception as ex: 
            self.set_status(500, str(ex))
        self.set_custom_default_headers()
        self.finish()

    async def delete(self):
        if not self.headers_ok:
            return 
        try: 
            server = JSONSerializable.loads(self.request.body)
            async with self.disk_session() as session, session.begin():
                session : asyncio_ext.session
                stmt = delete(Server).filter_by(name=server.get("name", None))
                ret = await session.execute(stmt)
            self.set_status(204)
        except SQLAlchemyError as ex:
            self.set_status(500, "Database error - check message on server")
        except Exception as ex: 
            self.set_status(500, str(ex))
        self.set_custom_default_headers()
        self.finish()
        
    def set_access_control_allow_methods(self) -> None:
        self.set_header("access-control-allow-methods", "GET, POST, PUT, DELETE, OPTIONS")


class SubscriberHandler(SystemHostHandler):

    async def get(self):
        pass
    

class SwaggerUIHandler(SystemHostHandler):
    
    async def get(self):
        await self.render(
            f"{os.path.dirname(os.path.abspath(__file__))}{os.sep}assets{os.sep}swagger_ui_template.html", 
            swagger_spec_url="/index.yml"
        )


class MainHandler(SystemHostHandler):

    def initialize(self, CORS: List[str], disk_session: Session, 
                   mem_session: asyncio_ext.AsyncSession, swagger : bool = False,
                   IP : str = "") -> None:
        self.swagger = swagger
        self.IP = IP
        return super().initialize(CORS, disk_session, mem_session)

    async def get(self):
        if not self.headers_ok: 
            return
        self.set_status(200)
        self.set_custom_default_headers()
        self.write("<p><h1>I am alive!</h1><p>")
        if self.swagger:
            self.write(f"<p>Visit <a href={self.IP+'/swagger-ui'}>here</a> to login and use my swagger doc</p>")
        self.finish()




    


__all__ = [
    SystemHostHandler.__name__,
    UsersHandler.__name__,
    AppSettingsHandler.__name__,
    AppSettingHandler.__name__,
    LoginHandler.__name__,
    LogoutHandler.__name__,
    WhoAmIHandler.__name__,
    PagesHandler.__name__,
    PageHandler.__name__,
    SubscribersHandler.__name__,
    SwaggerUIHandler.__name__,
    MainHandler.__name__
]