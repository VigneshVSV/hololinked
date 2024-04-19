import os
from sqlite3 import DatabaseError
import threading
import typing
from sqlalchemy import create_engine, select, inspect as inspect_database
from sqlalchemy.ext import asyncio as asyncio_ext
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Integer, String, JSON, LargeBinary
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase, MappedAsDataclass
from dataclasses import dataclass

from ..param import Parameterized
from .constants import JSONSerializable
from .config import global_config
from .utils import pep8_to_dashed_URL
from .serializers import PythonBuiltinJSONSerializer as JSONSerializer, BaseSerializer
from .remote_parameter import RemoteParameter



class RemoteObjectTableBase(DeclarativeBase):
    pass 
    
class SerializedParameter(MappedAsDataclass, RemoteObjectTableBase):
    __tablename__ = "parameters"

    instance_name  : Mapped[str] = mapped_column(String)
    name : Mapped[str] = mapped_column(String, primary_key=True)
    serialized_value : Mapped[bytes] = mapped_column(LargeBinary) 


class RemoteObjectInformation(MappedAsDataclass, RemoteObjectTableBase):
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
        return {
            "instance_name" : self.instance_name,
            "class_name" : self.class_name,
            "script" : self.script,
            "kwargs" : self.kwargs,
            "eventloop_instance_name" : self.eventloop_instance_name,
            "http_server" : self.http_server,
            "level" : self.level, 
        }

@dataclass 
class DeserializedParameter: # not part of database
    """
    Parameter with deserialized value
    """
    instance_name : str
    name : str 
    value : typing.Any



class BaseDB:

    def __init__(self, instance : Parameterized, serializer : typing.Optional[BaseSerializer] = None, 
                config_file : typing.Union[str, None] = None) -> None:
        self.remote_object_instance = instance
        self.instance_name = instance.instance_name
        self.serializer = serializer
        self.URL = self.create_URL(config_file)
        self._context = {}


    @classmethod
    def load_conf(cls, config_file : str) -> typing.Dict[str, typing.Any]:
        """
        load configuration file using JSON serializer
        """
        if not config_file:
            conf = {}
        elif config_file.endswith('.json'):
            file = open(config_file, 'r')
            conf = JSONSerializer.load(file)
        else:
            raise ValueError("config files of extension - {} expected, given file name {}".format(["json"], config_file))
        return conf
            
    def create_URL(self, config_file : str) -> str:
        """
        auto chooses among the different supported databases based on config file
        and creates the URL 
        """
        if config_file is None:
            folder = f'{global_config.TEMP_DIR}{os.sep}databases{os.sep}{pep8_to_dashed_URL(self.remote_object_instance.__class__.__name__.lower())}'
            if not os.path.exists(folder):
                os.makedirs(folder)
            return BaseDB.create_sqlite_URL(**dict(file=f'{folder}{os.sep}{self.instance_name}.db'))
        conf = BaseDB.load_conf(config_file)
        if conf.get('server', None):
            return BaseDB.create_postgres_URL(conf=conf)
        else:
            return BaseDB.create_sqlite_URL(conf=conf)
    
    @classmethod
    def create_postgres_URL(cls, conf : str = None, database : typing.Optional[str] = None, 
                use_dialect : typing.Optional[bool] = False) -> str:
        """
        create a postgres URL
        """
        server = conf.get('server', None) 
        database = conf.get('database', database)
        host = conf.get("host", 'localhost')
        port = conf.get("port", 5432)
        user = conf.get('user', 'postgres')
        password = conf.get('password', '')
        if use_dialect:
            dialect = conf.get('dialect', None)
            if dialect:
                return f"{server}+{dialect}://{user}:{password}@{host}:{port}/{database}"      
        return f"{server}://{user}:{password}@{host}:{port}/{database}"
     
    @classmethod
    def create_sqlite_URL(self, **conf : typing.Dict[str, JSONSerializable]) -> str:
        """
        create sqlite URL
        """
        in_memory = conf.get('in_memory', False)
        dialect = conf.get('dialect', 'pysqlite')
        if not in_memory:
            file = conf.get('file', f'{global_config.TEMP_DIR}{os.sep}databases{os.sep}default.db')
            return f"sqlite+{dialect}:///{file}"
        else: 
            return f"sqlite+{dialect}:///:memory:"

    @property
    def in_context(self):
        return threading.get_ident() in self._context


class BaseAsyncDB(BaseDB):
    """
    Base class for an async database engine, implements configuration file reader, 
    sqlalchemy engine & session creation.

    Parameters
    ----------
    database: str
        The database to open in the database server specified in config_file (see below)
    serializer: BaseSerializer
        The serializer to use for serializing and deserializing data (for example
        parameter serializing before writing to database). Will be the same as
        serializer supplied to ``RemoteObject``.
    config_file: str
        absolute path to database server configuration file
    """
    
    def __init__(self, instance : Parameterized, 
                serializer : typing.Optional[BaseSerializer] = None, 
                config_file : typing.Union[str, None] = None) -> None:
        super().__init__(instance=instance, serializer=serializer, config_file=config_file)
        self.engine = asyncio_ext.create_async_engine(self.URL, echo=True)
        self.async_session = sessionmaker(self.engine, expire_on_commit=True, 
                        class_=asyncio_ext.AsyncSession)
        RemoteObjectTableBase.metadata.create_all(self.engine)



class BaseSyncDB(BaseDB):
    """
    Base class for an synchronous (blocking) database engine, implements 
    configuration file reader, sqlalchemy engine & session creation.

    Parameters
    ----------
    database: str
        The database to open in the database server specified in config_file (see below)
    serializer: BaseSerializer
        The serializer to use for serializing and deserializing data (for example
        parameter serializing into database for storage). Will be the same as
        serializer supplied to ``RemoteObject``.
    config_file: str
        absolute path to database server configuration file
    """

    def __init__(self, instance : Parameterized, 
                serializer : typing.Optional[BaseSerializer] = None, 
                config_file : typing.Union[str, None] = None) -> None:
        super().__init__(instance=instance, serializer=serializer, config_file=config_file)
        self.engine = create_engine(self.URL, echo=True)
        self.sync_session = sessionmaker(self.engine, expire_on_commit=True)
        RemoteObjectTableBase.metadata.create_all(self.engine)
        
        

class RemoteObjectDB(BaseSyncDB):
    """
    Database engine composed within ``RemoteObject``, carries out database 
    operations like storing object information, paramaters etc. 

    Parameters
    ----------
    instance_name: str
        ``instance_name`` of the ``RemoteObject```
    serializer: BaseSerializer
        serializer used by the ``RemoteObject``. The serializer to use for 
        serializing and deserializing data (for example parameter serializing 
        into database for storage).
    config_file: str
        configuration file of the database server
    """

    def fetch_own_info(self): # -> RemoteObjectInformation:
        """
        fetch ``RemoteObject`` instance's own information, for schema see 
        ``RemoteObjectInformation``.

        Returns
        -------
        info: RemoteObject
        """
        if not inspect_database(self.engine).has_table("remote_objects"):
            return
        with self.sync_session() as session:
            stmt = select(RemoteObjectInformation).filter_by(instance_name=self.instance_name)
            data = session.execute(stmt)
            data = data.scalars().all()
            if len(data) == 0:
                return None 
            elif len(data) == 1:
                return data[0]
            else:
                raise DatabaseError("Multiple remote objects with same instance name found, either cleanup database/detach/make new")
            
    def get_all_parameters(self, deserialized : bool = True) -> typing.Sequence[
                            typing.Union[SerializedParameter, DeserializedParameter]]:
        """
        read all paramaters of the ``RemoteObject`` instance.

        Parameters
        ----------
        deserialized: bool, default True
            deserilize the parameters if True
        """
        with self.sync_session() as session:
            stmt = select(SerializedParameter).filter_by(instance_name=self.instance_name)
            data = session.execute(stmt)
            existing_params = data.scalars().all() #type: typing.Sequence[SerializedParameter]
            if not deserialized:
                return existing_params
            params_data = []
            for param in existing_params:
                params_data.append(DeserializedParameter(
                    instance_name=self.instance_name,
                    name = param.name, 
                    value = self.serializer.loads(param.serialized_value)
                ))
            return params_data
        
    def create_missing_parameters(self, parameters : typing.Dict[str, RemoteParameter],
                            get_missing_parameters : bool = False) -> None:
        """
        create any and all missing remote parameters of ``RemoteObject`` instance
        in database.

        Parameters
        ----------
        parameters: Dict[str, RemoteParamater]
            descriptors of the parameters

        Returns
        -------
        List[str]
            list of missing parameters if get_missing_paramaters is True
        """
        missing_params = []
        with self.sync_session() as session:
            existing_params = self.get_all_parameters()
            existing_names = [p.name for p in existing_params]
            for name, new_param in parameters.items():
                if name not in existing_names: 
                    param = SerializedParameter(
                        instance_name=self.instance_name, 
                        name=new_param.name, 
                        serialized_value=self.serializer.dumps(getattr(self.remote_object_instance, 
                                                                new_param.name))
                    )
                    session.add(param)
                    missing_params.append(name)
            session.commit()
        if get_missing_parameters:
            return missing_params
        
    def get_parameter(self, parameter : typing.Union[str, RemoteParameter], 
                        deserialized : bool = True) -> typing.Sequence[typing.Union[SerializedParameter, DeserializedParameter]]:
        """
        read a paramater of the ``RemoteObject`` instance.

        Parameters
        ----------
        parameter: str | RemoteParameter
            string name or descriptor object
        deserialized: bool, default True
            deserilize the parameters if True
        """
        with self.sync_session() as session:
            name = parameter if isinstance(parameter, str) else parameter.name
            stmt = select(SerializedParameter).filter_by(instance_name=self.instance_name, name=name)
            data = session.execute(stmt)
            param = data.scalars().all() #type: typing.Sequence[SerializedParameter]
            if len(param) == 0:
                raise DatabaseError("parameter {name} not found in datanbase ")
            elif len(param) > 1:
                raise DatabaseError("multiple parameters with same name found") # Impossible actually
            if not deserialized:
                return param[0]
            return DeserializedParameter(
                    instance_name=param[0].instance_name,
                    name = param[0].name, 
                    value = self.serializer.loads(param[0].serialized_value)
                )
          
    def set_parameter(self, parameter : typing.Union[str, RemoteParameter], value : typing.Any) -> None:
        """
        change the value of an already existing parameter

        Parameters
        ----------
        parameter: RemoteParameter
            descriptor of the parameter
        value: Any
            value of the parameter
        """
        if self.in_context:
            self._context[threading.get_ident()][parameter.name] = value
            return
        with self.sync_session() as session:
            name = parameter if isinstance(parameter, str) else parameter.name
            stmt = select(SerializedParameter).filter_by(instance_name=self.instance_name, 
                                                name=name)
            data = session.execute(stmt)
            param = data.scalars().all()
            if len(param) > 1:
                raise DatabaseError("")
            if len(param) == 1:
                param = param[0]
                param.serialized_value = self.serializer.dumps(value)
            else:
                param = SerializedParameter(
                        instance_name=self.instance_name, 
                        name=name,
                        serialized_value=self.serializer.dumps(getattr(self.remote_object_instance, name))
                    )
                session.add(param)
            session.commit()
                

    def set_parameters(self, parameters : typing.Dict[typing.Union[str, RemoteParameter], typing.Any]) -> None:
        """
        change the value of an already existing parameter

        Parameters
        ----------
        parameter: RemoteParameter
            descriptor of the parameter
        value: Any
            value of the parameter
        """
        if self.in_context:
            for obj, value in parameters.items():
                name = obj if isinstance(obj, str) else obj.name
                self._context[threading.get_ident()][name] = value
            return
        with self.sync_session() as session:
            names = []
            for obj in parameters.keys():
                names.append(obj if isinstance(obj, str) else obj.name)
            stmt = select(SerializedParameter).filter_by(instance_name=self.instance_name).filter(
                                    SerializedParameter.name.in_(names))
            data = session.execute(stmt)
            db_params = data.scalars().all()
            for obj, value in parameters.items():
                name = obj if isinstance(obj, str) else obj.name
                db_param = list(filter(lambda db_param: db_param.name == name, db_params)) # type: typing.List[SerializedParameter]
                if len(db_param) > 0:
                    db_param = db_param[0]
                    db_param.serialized_value = self.serializer.dumps(value)
                else:
                    param = SerializedParameter(
                        instance_name=self.instance_name, 
                        name=name,
                        serialized_value=self.serializer.dumps(value)
                    )
                    session.add(param)
            session.commit()
     


class batch_db_commit:
    """
    Context manager to write multiple parameters to database at once. Useful for sequential writes 
    to parameters with database settings. 
    """
    def __init__(self, db_engine : RemoteObjectDB) -> None:
        self.db_engine = db_engine

    def __enter__(self) -> None: 
        self.db_engine._context[threading.get_ident()] = dict()
        
    def __exit__(self, exc_type, exc_value, exc_tb) -> None:
        data = self.db_engine._context.pop(threading.get_ident(), dict()) # typing.Dict[str, typing.Any]
        if exc_type is None:
            self.db_engine.set_parameters(data)
            return 
        for name, value in data.items():
            try:
                self.db_engine.set_parameter(name, value)
            except Exception as ex:
                pass


  
__all__ = [
    BaseAsyncDB.__name__,
    BaseSyncDB.__name__,
    RemoteObjectDB.__name__,
    batch_db_commit.__name__
]