import typing 
from dataclasses import asdict, field

from sqlalchemy import Integer, String, JSON, ARRAY, Boolean, BLOB
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase, MappedAsDataclass

from ..server.constants import JSONSerializable


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
    Dashboards.__name__,
    AppSettings.__name__,
    LoginCredentials.__name__,
    Server.__name__,
    RemoteObjectInformation.__name__,
    UserSession.__name__
]