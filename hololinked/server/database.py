import typing
from sqlalchemy import create_engine, select
from sqlalchemy.ext import asyncio as asyncio_ext
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Integer, String, JSON, LargeBinary
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase, MappedAsDataclass
from dataclasses import dataclass, asdict

from ..param import Parameterized
from .serializers import JSONSerializer, BaseSerializer
from .constants import JSONSerializable
from .remote_parameter import RemoteParameter



class RemoteObjectTableBase(DeclarativeBase):
    pass 
    
class SerializedParameter(MappedAsDataclass, RemoteObjectTableBase):
    __tablename__ = "parameters"

    id : Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    instance_name  : Mapped[str] = mapped_column(String)
    name : Mapped[str] = mapped_column(String)
    serialized_value : Mapped[bytes] = mapped_column(LargeBinary) 

@dataclass 
class DeserializedParameter: # not part of database
    name : str 
    value : typing.Any



class BaseDB:

    def __init__(self, instance : Parameterized, serializer : typing.Optional[BaseSerializer] = None, 
                config_file : typing.Union[str, None] = None) -> None:
        self.remote_object_instance = instance
        self.instance_name = instance.instance_name
        self.serializer = serializer
        self.URL = self.create_URL(config_file)
            
    @classmethod
    def create_URL(cls, file_name : str = None, database : typing.Optional[str] = None) -> str:
        if not file_name:
            conf = {}
        elif file_name.endswith('.json'):
            file = open(file_name, 'r')
            conf = JSONSerializer.generic_load(file)
        else:
            raise ValueError("config files of extension - {} expected, given file name {}".format(["json"], file_name))
        
        dialect = conf.get('dialect', None)
        server = conf.get('server', None) 
        if not database:
            database = conf.get('database', 'hololinked')
        if not server:
            file = conf.get('file', 'hololinked.db')
            return f"sqlite+pysqlite://{file}/{database}"
        host = conf.get("host", 'localhost')
        port = conf.get("port", 5432)
        user = conf.get('user', 'postgres')
        password = conf.get('password', '')
        return f"{server}+{dialect}://{user}:{password}@{host}:{port}/{database}"
      
    
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
        self.engine = create_engine(self.URL, echo = True)
        self.sync_session = sessionmaker(self.engine, expire_on_commit=True)
        

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
    def fetch_own_info(self) -> RemoteObjectInformation:
        """
        fetch ``RemoteObject`` instance's own information, for schema see 
        ``RemoteObjectInformation``.

        Returns
        -------
        info: RemoteObject
        """
        with self.sync_session() as session:
            stmt = select(RemoteObjectInformation).filter_by(instance_name=self.instance_name)
            data = session.execute(stmt)
            data = data.scalars().all()
            if len(data) == 0:
                return None 
            return data[0]
            
    def read_all_parameters(self, deserialized : bool = True) -> typing.Sequence[
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
                    name = param.name, 
                    value = self.serializer.loads(param.serialized_value)
                ))
            return params_data
          
    def create_missing_db_parameters(self, 
                    parameters : typing.Dict[str, RemoteParameter]) -> None:
        """
        create any and all missing remote parameters of ``RemoteObject`` instance
        in database.

        Parameters
        ----------
        parameters: Dict[str, RemoteParamater]
            descriptors of the parameters
        """
        with self.sync_session() as session:
            existing_params = self.read_all_parameters()
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
            session.commit()

    def edit_parameter(self, parameter : RemoteParameter, 
                       value : typing.Any) -> None:
        """
        change the parameter value of an already existing parameter

        Parameters
        ----------
        parameter: RemoteParameter
            descriptor of the parameter
        value: Any
            value of the parameter
        """
        with self.sync_session() as session:
            stmt = select(SerializedParameter).filter_by(instance_name=self.instance_name, 
                                                name=parameter.name)
            data = session.execute(stmt)
            param = data.scalar()
            param.serialized_value = self.serializer.dumps(value)
            session.commit()


  
__all__ = [
    'BaseAsyncDB',
    'BaseSyncDB',
    'RemoteObjectDB'
]