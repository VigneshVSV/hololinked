import typing
import inspect
from argon2 import PasswordHasher

from sqlalchemy import select, delete, update
from sqlalchemy.orm import Session
from sqlalchemy.ext import asyncio as asyncio_ext
from tornado.web import RequestHandler, HTTPError, authenticated

from .models import *
from ..server.serializers import JSONSerializer
from ..server.config import global_config
from ..server.utils import uuid4_in_bytes 



def for_authenticated_user(method):
    async def authenticated_method(self : "SystemHostHandler") -> None:
        if self.current_user_valid:
            return await method(self)
        self.set_status(403)
        self.set_custom_default_headers()
        self.finish()
        return
    return authenticated_method


class SystemHostHandler(RequestHandler):
    """
    Base Request Handler for all requests directed to system host server. Implements CORS & credential checks. 
    """

    def initialize(self, CORS : typing.List[str], disk_session : Session, mem_session : asyncio_ext.AsyncSession) -> None:
        self.CORS = CORS 
        self.disk_session = disk_session
        self.mem_session = mem_session

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
        For credential login, access control allow origin cannot be *,
        See: https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS#examples_of_access_control_scenarios
        """
        origin = self.request.headers.get("Origin")
        if origin is not None and (origin in self.CORS or origin + '/' in self.CORS):
            self.set_header("Access-Control-Allow-Origin", origin)
             
    def set_access_control_allow_headers(self) -> None:
        """
        For credential login, access control allow headers cannot be *. 
        See: https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS#examples_of_access_control_scenarios
        """
        headers = ", ".join(self.request.headers.keys())
        if self.request.headers.get("Access-Control-Request-Headers", None):
            headers += ", " + self.request.headers["Access-Control-Request-Headers"]
        self.set_header("Access-Control-Allow-Headers", headers)
   
    def set_custom_default_headers(self) -> None:
        """
        sets access control allow origin, allow headers and allow credentials 
        """
        self.set_access_control_allow_origin()
        self.set_access_control_allow_headers()
        self.set_header("Access-Control-Allow-Credentials", "true")
      
    async def options(self):
        self.set_status(200)
        self.set_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
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
    Performs login and supplies a signed cookie for session
    """
    async def post(self):
        self.check_headers()
        try:
            body = JSONSerializer.generic_loads(self.request.body)
            email = body["email"]
            password = body["password"]
            async with self.disk_session() as session: 
                session : asyncio_ext.AsyncSession
                stmt = select(LoginCredentials).filter_by(email=email)
                data = await session.execute(stmt)
                data = data.scalars().all() # type: typing.List[LoginCredentials]
            if len(data) == 0:
                self.set_status(403, "authentication failed - no username found")    
            else:
                data = data[0] # type: LoginCredentials
                ph = PasswordHasher(time_cost=global_config.PWD_HASHER_TIME_COST)
                if ph.verify(data.password, password):
                    self.set_status(200)
                    cookie_value = uuid4_in_bytes()
                    self.set_signed_cookie("user", cookie_value, httponly=True,  
                                secure=True, samesite="strict", domain="localhost",
                                expires_days=None)
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
            self.set_status(500, f"authentication failed - {str(ex)}")
        self.set_custom_default_headers()
        self.finish()
        
    async def options(self):
        self.set_status(200)
        self.set_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.set_custom_default_headers()
        self.finish()


class LogoutHandler(SystemHostHandler):
    """
    Performs login and supplies a signed cookie for session
    """
    async def post(self):
        self.check_headers()
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
                self.set_status(200, "logged out")
                self.clear_cookie("user")   
        except Exception as ex:
            self.set_status(500, f"logout failed - {str(ex)}")
        self.set_custom_default_headers()
        self.finish()
        
    async def options(self):
        self.set_status(200)
        self.set_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.set_custom_default_headers()
        self.finish()


    

class AppSettingsHandler(SystemHostHandler):

    @for_authenticated_user
    async def post(self):
        self.check_headers()
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
        except Exception as ex:
            self.set_status(500, str(ex))
        self.set_custom_default_headers()
        self.finish()

    @for_authenticated_user
    async def patch(self):
        self.check_headers()
        try:
            value = JSONSerializer.generic_loads(self.request.body)
            field = value["field"]
            value = value["value"]
            async with self.disk_session() as session, session.begin():
                stmt = select(AppSettings).filter_by(field = field)
                data = await session.execute(stmt)
                setting : AppSettings = data.scalar()
                setting.value = {"value" : value}
                await session.commit()
            self.set_status(200)
        except Exception as ex:
            self.set_status(500, str(ex))
        self.set_custom_default_headers()
        self.finish()

    @for_authenticated_user
    async def get(self):
        self.check_headers()
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

    
class DashboardsHandler(SystemHostHandler):

    @for_authenticated_user
    async def post(self):
        self.check_headers()
        try:
            data = JSONSerializer.generic_loads(self.request.body)
            async with self.disk_session() as session, session.begin():
                session.add(Dashboards(**data))
                await session.commit()
            self.set_status(200)
        except Exception as ex:
            self.set_status(500, str(ex))
        self.set_custom_default_headers()
        self.finish()

    @for_authenticated_user
    async def get(self):
        self.check_headers()
        try:
            async with self.disk_session() as session:
                stmt = select(Dashboards)
                data = await session.execute(stmt)
                serialized_data = JSONSerializer.generic_dumps([result[Dashboards.__name__]._json() for result 
                                               in data.mappings().all()])           
            self.set_status(200)
            self.set_header("Content-Type", "application/json")
            self.write(serialized_data)
        except Exception as ex:
            self.set_status(500, str(ex))
        self.set_custom_default_headers()
        self.finish()


class SubscribersHandler(SystemHostHandler):

    @for_authenticated_user
    async def post(self):
        if self.request.headers["Content-Type"] == "application/json":
            self.set_status(200)
            server = SubscribedHTTPServers(**JSONSerializer.generic_loads(self.request.body))
            async with self.disk_session() as session, session.begin():
                session.add(server)
                await session.commit()
            self.finish()

    @for_authenticated_user
    async def get(self):
        self.set_status(200)
        self.set_header("Content-Type", "application/json")
        async with self.disk_session() as session:
            result = select(Server)
            self.write(JSONSerializer.generic_dumps(result.scalars().all()))


class SubscriberHandler(SystemHostHandler):

    async def get(self):
        pass
    


class MainHandler(SystemHostHandler):

    async def get(self):
        self.check_headers()
        self.set_status(200)
        self.set_custom_default_headers()
        self.write("<p>I am alive!!!<p>")
        self.finish()



__all__ = [
    SystemHostHandler.__name__,
    UsersHandler.__name__,
    AppSettingsHandler.__name__,
    LoginHandler.__name__,
    DashboardsHandler.__name__,
    SubscribersHandler.__name__,
    MainHandler.__name__,
    LogoutHandler.__name__
]