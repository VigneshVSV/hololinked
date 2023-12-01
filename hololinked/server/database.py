import typing
from sqlalchemy.ext import asyncio as asyncio_ext
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

from .serializers import JSONSerializer, BaseSerializer


def create_DB_URL(file_name : str, asynch : bool = False):
    if file_name.endswith('.json'):
        file = open(file_name, 'r')
        conf = JSONSerializer.general_load(file)
    else:
        raise ValueError("config files of extension - {} expected, given file name {}".format(["json"], file_name))
    
    host = conf.get("host", 'localhost')
    port = conf.get("port", 5432)
    user     = conf.get('user', 'postgres')
    password = conf.get('password', '')
    
    if asynch:
        return f"postgresql+asyncpg://{user}:{password}@{host}:{port}"
    else:
        return f"postgresql://{user}:{password}@{host}:{port}"
        
    

class BaseAsyncDB:
    
    def __init__(self, database : str, serializer : BaseSerializer, config_file : typing.Union[str, None] = None) -> None:
        if config_file:
            URL = f"{create_DB_URL(config_file, True)}/{database}"
            self.engine = asyncio_ext.create_async_engine(URL, echo = True)
            self.async_session = sessionmaker(self.engine, expire_on_commit=True, class_= asyncio_ext.AsyncSession) # type: ignore
        self.serializer = serializer


class BaseSyncDB:

    def __init__(self, database : str, serializer : BaseSerializer, config_file : typing.Union[str, None] = None) -> None:
        if config_file:
            URL = f"{create_DB_URL(config_file, False)}/{database}"
            self.engine = create_engine(URL, echo = True)
            self.sync_session = sessionmaker(self.engine, expire_on_commit=True)
        self.serializer = serializer


  
__all__ = ['BaseAsyncDB']