import typing
from inspect import getmro

from ..param import Parameter
from ..param.serializer import Serialization, serializers

from .valuestub import ValueStub, ActionStub
from .basecomponents import ReactBaseComponent
from .actions import BaseAction
from .utils import unique_id



class FrontendJSONSpecSerializer(Serialization):
    """
    Produce a dict of the parameters. 
    This is not strictly a serializer as it returns a dict and not a string.
    Serialization of the return value should be done at the level of calling funcion 
    allowing manipulation before string serialization. 
    """

    excludeKeys  = [ 'name' ] 
    topLevelKeys = [ 
        # General HTML related keys
        'id',
        # custom keys 
        'tree', 'dependents', 'dependentsExist', 'componentName', 'outputID',
        # MUI specific keys
        'component', 'styles', 'classes',
        # React grid layout keys
        # state machine keys
        # plotly 
        'sources', 'plot', 
        ]  
    metadataKeys = [ 'RGLDataGrid', 'styling' ]
    # ignorable keys are ignored when they are None
    ignorableKeys = [ 'dependents', 'dependentsExist', 'stateMachine', 'children', 'styling', 'dataGrid']
    
    propFilter = excludeKeys + topLevelKeys + metadataKeys # Keys which are not in this will generally be props
    
    @classmethod
    def serialize_parameters(cls, pobj : 'ReactBaseComponent', 
                    subset : typing.Union[typing.List, typing.Tuple, None] = None)-> typing.Dict[str, typing.Any]:
        JSONDict = dict(props={})
        pobjtype = type(pobj)
        for key, param in pobj.parameters.descriptors.items():
            if subset is not None and key not in subset:
                pass 
            elif key not in cls.excludeKeys:
                value = param.__get__(pobj, pobjtype)
                if not isinstance(value, ValueStub):
                    value = param.serialize(value)
                cls._assign_dict_heirarchically(pobj, key, value, JSONDict)
        return JSONDict

    @classmethod
    def _assign_dict_heirarchically(cls, pobj : 'ReactBaseComponent', key : str, value : typing.Any, 
                                        JSONDict : typing.Dict[str, typing.Any]) -> None:
        if key in cls.ignorableKeys and value is None:
            return
        if isinstance(value, BaseAction):
            if value.id is None:
                # Just a shield so as to not commit errors in coding. For the user the code should never reach here.
                raise ValueError("no ID has been assigned to action. contact developer.")
            try:
                JSONDict['actions'][value.id] = value
            except KeyError:
                JSONDict['actions'] = {}
                JSONDict['actions'][value.id] = value
            value = ActionStub(value.id)
            # & continue further down the logic to assign the stub to the appropriate field
        if key in cls.topLevelKeys:
            JSONDict[key] = value
        elif key in cls.metadataKeys:
            try:
                JSONDict['metadata'][key] = value 
            except KeyError:
                JSONDict['metadata'] = {}
                JSONDict['metadata'][key] = value 
        elif key == 'stateMachine':
            for state, props in value.states.items():
                for kee, val in props.items():
                    if isinstance(val, BaseAction):
                        if val.id is None:
                            val.id = unique_id(prefix = 'actionid_')  # type: ignore
                        try:
                            JSONDict['actions'][val.id] = val
                        except KeyError:
                            JSONDict['actions'] = {}
                            JSONDict['actions'][val.id] = val
                        props[kee] = ActionStub(val.id)
            JSONDict[key] = value
        elif key == 'children':
            if value is not None:
                if isinstance(value, list) and len(value) > 0:
                    JSONDict[key] = [child.id if isinstance(child, ReactBaseComponent) else child for child in value]
                else: 
                    JSONDict[key] = [value]
        elif key == 'value':
            return
        elif isinstance(value, ReactBaseComponent):
            JSONDict['props'][key] = value.id
            if JSONDict.get('nodes', None) is None:
                JSONDict['nodes'] = {}
            JSONDict['nodes'] 
            value.json(JSONDict)
        elif key not in cls.propFilter:
            JSONDict['props'][key] = value
        else:
            raise NotImplementedError("No implementation of key {} for serialization.".format(key))
        
serializers['FrontendJSONSpec'] = FrontendJSONSpecSerializer # type: ignore


__all__ = ['FrontendJSONSpecSerializer']