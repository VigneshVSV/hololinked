import typing
from enum import Enum

from ..param.parameterized import Parameter, ClassParameters
from .data_classes import RemoteResourceInfoValidator
from .constants import USE_OBJECT_NAME, HTTP_METHODS



class Property(Parameter):
    """
    Initialize a new Property object and store the supplied attributes:

    Parameters
    ----------

    default: None or corresponding to parameter type 
        The default value of the parameter. This is owned by class for the attribute 
        represented by the Property, which is overridden in an instance after 
        setting the parameter.

    doc: str, default empty
        docstring explaining what this parameter represents.

    constant: bool, default False
        if true, the Property value can be changed only at
        the class level or in a Parameterized constructor call. The
        value is otherwise constant on the Parameterized instance,
        once it has been constructed.

    readonly: bool, default False
        if true, the Property value cannot ordinarily be
        changed by setting the attribute at the class or instance
        levels at all. The value can still be changed in code by
        temporarily overriding the value of this slot and then
        restoring it, which is useful for reporting values that the
        _user_ should never change but which do change during code
        execution.

    allow_None: bool, default False 
        if True, None is accepted as a valid value for
        this Property, in addition to any other values that are
        allowed. If the default value is defined as None, allow_None
        is set to True automatically.

    URL_path: str, uses object name by default
        resource locator under which the attribute is accessible through 
        HTTP. when remote is True and no value is supplied, the variable name 
        is used and underscores and replaced with dash

    remote: bool, default True
        set to false to make the parameter local

    http_method: tuple, default (GET, PUT)
        http methods for read and write respectively 

    state: str | Enum, default None
        state of state machine where write can be executed

    db_persist: bool, default False
        if True, every read and write is stored in database 
        and persists instance destruction and creation. 
    
    db_init: bool, default False
        if True, only the first read is loaded from database.
        Further reads and writes not written to database. if db_persist
        is True, this value is ignored. 

    db_commit: bool,
        if True, all write values are stored to database. if db_persist
        is True, this value is ignored. 

    remote: bool, default True
        set False to avoid exposing the variable for remote read 
        and write

    metadata: dict, default None
        store your own JSON compatible metadata for the parameter 
        which gives useful (and modifiable) information about the parameter. 

    label: str, default extracted from object name
        optional text label to be used when this Property is
        shown in a listing. If no label is supplied, the attribute name
        for this parameter in the owning Parameterized object is used.

    fget: Callable, default None
        custom getter method, mandatory when setter method is also custom.

    fset: Callable, default None
        custom setter method
    
    fdel: Callable, default None
        custom deleter method
        
    per_instance_descriptor: bool, default False 
        whether a separate Property instance will be
        created for every Parameterized instance. True by default.
        If False, all instances of a Parameterized class will share
        the same Property object, including all validation
        attributes (bounds, etc.). See also deep_copy, which is
        conceptually similar but affects the Property value rather
        than the Property object.

    deepcopy_default: bool, default False 
        controls whether the value of this Property will
        be deepcopied when a Parameterized object is instantiated (if
        True), or if the single default value will be shared by all
        Parameterized instances (if False). For an immutable Property
        value, it is best to leave deep_copy at the default of
        False, so that a user can choose to change the value at the
        Parameterized instance level (affecting only that instance) or
        at the Parameterized class or superclass level (affecting all
        existing and future instances of that class or superclass). For
        a mutable Property value, the default of False is also appropriate
        if you want all instances to share the same value state, e.g. if
        they are each simply referring to a single global object like
        a singleton. If instead each Parameterized should have its own
        independently mutable value, deep_copy should be set to
        True, but note that there is then no simple way to change the
        value of this Property at the class or superclass level,
        because each instance, once created, will then have an
        independently deepcopied value.

    class_member : bool, default False
        when True, parameter is set on class instead of instance. 

    precedence: float, default None
        a numeric value, usually in the range 0.0 to 1.0,
        which allows the order of Properties in a class to be defined in
        a listing or e.g. in GUI menus. A negative precedence indicates
        a parameter that should be hidden in such listings.

    """

    __slots__ = ['db_persist', 'db_init', 'db_commit', 'metadata', '_remote_info', 'observable']

    def __init__(self, default: typing.Any = None, *, doc : typing.Optional[str] = None, constant : bool = False, 
                readonly : bool = False, allow_None : bool = False, 
                URL_path : str = USE_OBJECT_NAME, remote : bool = True, observable : bool = False, 
                http_method : typing.Tuple[typing.Optional[str], typing.Optional[str]] = (HTTP_METHODS.GET, HTTP_METHODS.PUT), 
                state : typing.Optional[typing.Union[typing.List, typing.Tuple, str, Enum]] = None,
                db_persist : bool = False, db_init : bool = False, db_commit : bool = False, 
                class_member : bool = False, fget : typing.Optional[typing.Callable] = None, 
                fset : typing.Optional[typing.Callable] = None, fdel : typing.Optional[typing.Callable] = None, 
                deepcopy_default : bool = False, per_instance_descriptor : bool = False, 
                precedence : typing.Optional[float] = None, metadata : typing.Optional[typing.Dict] = None
            ) -> None:
        
        super().__init__(default=default, doc=doc, constant=constant, readonly=readonly, allow_None=allow_None,
                    per_instance_descriptor=per_instance_descriptor, deepcopy_default=deepcopy_default,
                    class_member=class_member, fget=fget, fset=fset, fdel=fdel, precedence=precedence)
        self.db_persist = db_persist
        self.db_init    = db_init
        self.db_commit  = db_commit
        self.metadata = metadata
        self.observable = observable
        if remote:
            self._remote_info = RemoteResourceInfoValidator(
                http_method=http_method,
                URL_path=URL_path,
                state=state,
                isparameter=True
            )
        else:
            self._remote_info = None
        
    def _post_slot_set(self, slot : str, old : typing.Any, value : typing.Any) -> None:
        if slot == 'owner' and self.owner is not None:
            if self._remote_info is not None:
                if self._remote_info.URL_path == USE_OBJECT_NAME:
                    self._remote_info.URL_path = '/' + self.name
                elif not self._remote_info.URL_path.startswith('/'): 
                    self._remote_info.URL_path = f'/{self._remote_info.URL_path}',
                self._remote_info.obj_name = self.name
            # In principle the above could be done when setting name itself however to simplify
            # we do it with owner. So we should always remember order of __set_name__ -> 1) attrib_name, 
            # 2) name and then 3) owner
        super()._post_slot_set(slot, old, value)

    def _post_value_set(self, obj, value : typing.Any) -> None:
        if (self.db_persist or self.db_commit) and hasattr(obj, 'db_engine'):
            from .thing import Thing
            assert isinstance(obj, Thing), f"database parameter {self.name} bound to a non Thing, currently not supported"
            obj.db_engine.set_parameter(self, value)
        return super()._post_value_set(obj, value)

    


__parameter_info__ = [
                'allow_None' , 'class_member', 'db_init', 'db_persist', 
                'db_commit', 'deepcopy_default', 'per_instance_descriptor', 
                'default', 'doc', 'constant', 
                'metadata', 'name', 'readonly'
                # 'scada_info', 'parameter_type' # descriptor related info is also necessary
            ]

   
class ClassProperties(ClassParameters):
    """
    Object that holds the namespace and implementation of Parameterized methods as well as any state that is not 
    in __slots__ or the Properties themselves.
    Exists at metaclass level (instantiated by the metaclass). Contains state specific to the class.
    """

    @property
    def db_persisting_objects(self):
        try:
            return getattr(self.owner_cls, f'_{self.owner_cls.__name__}_db_persisting_remote_params')
        except AttributeError: 
            paramdict = self.remote_objects
            db_persisting_remote_params = {}
            for name, desc in paramdict.items():
                if desc.db_persist:
                    db_persisting_remote_params[name] = desc
            setattr(self.owner_cls, f'_{self.owner_cls.__name__}_db_persisting_remote_params', db_persisting_remote_params)
        return getattr(self.owner_cls, f'_{self.owner_cls.__name__}_db_persisting_remote_params')

    @property
    def db_init_objects(self) -> typing.Dict[str, Property]:
        try:
            return getattr(self.owner_cls, f'_{self.owner_cls.__name__}_db_init_remote_params')
        except AttributeError: 
            paramdict = self.remote_objects
            init_load_params = {}
            for name, desc in paramdict.items():
                if desc.db_init or desc.db_persist:
                    init_load_params[name] = desc
            setattr(self.owner_cls, f'_{self.owner_cls.__name__}_db_init_remote_params', init_load_params)
        return getattr(self.owner_cls, f'_{self.owner_cls.__name__}_db_init_remote_params')
        
    @property
    def remote_objects(self) -> typing.Dict[str, Property]:
        try:
            return getattr(self.owner_cls, f'_{self.owner_cls.__name__}_remote_params')
        except AttributeError: 
            paramdict = super().descriptors
            remote_params = {}
            for name, desc in paramdict.items():
                if isinstance(desc, Property):
                    remote_params[name] = desc
            setattr(self.owner_cls, f'_{self.owner_cls.__name__}_remote_params', remote_params)
        return getattr(self.owner_cls, f'_{self.owner_cls.__name__}_remote_params')

    def webgui_info(self, for_remote_params : typing.Union[Property, typing.Dict[str, Property], None] = None):
        info = {}
        if isinstance(for_remote_params, dict):
            objects = for_remote_params 
        elif isinstance(for_remote_params, Property):
            objects = { for_remote_params.name : for_remote_params } 
        else:
            objects = self.remote_objects
        for param in objects.values():
            state = param.__getstate__()
            info[param.name] = dict(
                remote_info = state.get("_remote_info", None).to_dataclass(),
                type = param.__class__.__name__,
                owner = param.owner.__name__
            )
            for field in __parameter_info__:
                info[param.name][field] = state.get(field, None) 
        return info 

    @property
    def visualization_parameters(self):
        from ..webdashboard.visualization_parameters import VisualizationParameter
        try:
            return getattr(self.owner_cls, f'_{self.owner_cls.__name__}_visualization_params')
        except AttributeError: 
            paramdict = super().descriptors
            visual_params = {}
            for name, desc in paramdict.items():
                if isinstance(desc, VisualizationParameter):
                    visual_params[name] = desc
            setattr(self.owner_cls, f'_{self.owner_cls.__name__}_visualization_params', visual_params)
        return getattr(self.owner_cls, f'_{self.owner_cls.__name__}_visualization_params')


  
__all__ = [
    Property.__name__
]