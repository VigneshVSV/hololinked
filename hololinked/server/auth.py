from sqlalchemy import select, delete, update
from sqlalchemy import Integer, String, JSON, ARRAY, Boolean, BLOB
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase, MappedAsDataclass, Session


class TableBase(DeclarativeBase):
    pass 

class LoginCredentials(TableBase, MappedAsDataclass):
    __tablename__ = "login_credentials"

    email : Mapped[str] = mapped_column(String(1024), primary_key=True)
    password : Mapped[str] = mapped_column(String(1024), unique=True)


class InMemoryTableBase(DeclarativeBase):
    pass 

class UserSession(InMemoryTableBase, MappedAsDataclass):
    __tablename__ = "user_sessions"

    email : Mapped[str] = mapped_column(String)
    session_key : Mapped[BLOB] = mapped_column(BLOB, primary_key=True)
    origin : Mapped[str] = mapped_column(String)
    user_agent : Mapped[str] = mapped_column(String)
    remote_IP : Mapped[str] = mapped_column(String)