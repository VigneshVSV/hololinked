import typing 
from dataclasses import asdict, field

from sqlalchemy import Integer, String, JSON, ARRAY, Boolean, BLOB
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase, MappedAsDataclass

from ..server.constants import JSONSerializable


class HololinkedHostTableBase(DeclarativeBase):
    pass 
    
class Pages(HololinkedHostTableBase, MappedAsDataclass):
    __tablename__ = "pages"

    name : Mapped[str] = mapped_column(String(1024), primary_key=True, nullable=False)
    URL  : Mapped[str] = mapped_column(String(1024), unique=True, nullable=False)
    description : Mapped[str] = mapped_column(String(16384))
    json_specfication : Mapped[typing.Dict[str, typing.Any]] = mapped_column(JSON, nullable=True)

    def json(self):
        return {
            "name" : self.name,
            "URL" : self.URL,
            "description" : self.description,
            "json_specification" : self.json_specfication
        }

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
    https : Mapped[bool] = mapped_column(Boolean) 
  
    def json(self):
        return {
            "hostname" : self.hostname,
            "type" : self.type, 
            "port" : self.port, 
            "IPAddress" : self.IPAddress,
            "https" : self.https
        }
    
  

class HololinkedHostInMemoryTableBase(DeclarativeBase):
    pass 

class UserSession(HololinkedHostInMemoryTableBase, MappedAsDataclass):
    __tablename__ = "user_sessions"

    email : Mapped[str] = mapped_column(String)
    session_key : Mapped[BLOB] = mapped_column(BLOB, primary_key=True)
    origin : Mapped[str] = mapped_column(String)
    user_agent : Mapped[str] = mapped_column(String)
    remote_IP : Mapped[str] = mapped_column(String)

        

__all__ = [
    HololinkedHostTableBase.__name__,
    HololinkedHostInMemoryTableBase.__name__,
    Pages.__name__,
    AppSettings.__name__,
    LoginCredentials.__name__,
    Server.__name__,
    UserSession.__name__
]