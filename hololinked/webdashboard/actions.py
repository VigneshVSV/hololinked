from typing import List, Union, Any, Dict

from ..param.parameters import String, ClassSelector, TypedList
from .baseprops import ComponentName, StringProp, StubProp, ActionID
from .utils import unique_id
from .constants import url_regex
from .valuestub import NumberStub, ObjectStub, BooleanStub



class BaseAction:

    actionType = ComponentName(default=__qualname__) 
    id         = ActionID()

    def __init__(self) -> None:
        self.id = unique_id(prefix='actionid_')

    def json(self):
        return dict(type=self.actionType, id=self.id)
        

class ActionProp(ClassSelector):

    def __init__(self, default=None, **kwargs):
        super().__init__(class_=BaseAction, default=default, 
                        per_instance_descriptor=True, deepcopy_default=True, allow_None=True, 
                        **kwargs)
        
class ActionListProp(TypedList):

    def __init__(self, default : Union[List, None] = None, **params):
        super().__init__(default, item_type=BaseAction, **params)


class ComponentOutputProp(ClassSelector):

    def __init__(self):
        super().__init__(default=None, allow_None=True, constant=True, class_=ComponentOutput)


class setLocation(BaseAction):

    actionType = ComponentName(default="setLocation")
    path       = StringProp(default='/')

    def json(self):
        return dict(**super().json(), path=self.path)


class setGlobalLocation(setLocation):

    actionType = ComponentName(default='setGlobalLocation')
 
 
class EventSource(BaseAction):

    actionType = ComponentName(default='SSE')
    url        = StringProp(default = None, allow_None=True, regex=url_regex )
    response   = StubProp(doc="""response value of the SSE (symbolic JSON specification based pointer - the actual value is in the browser).
                        Index it to access specific fields within the response.""" )
    readyState = StubProp(doc="0 - connecting, 1 - open, 2 - closed, use it for comparisons")
    withCredentials = StubProp(doc="")
    onerror = ActionListProp(doc="actions to execute when event source produces error")
    onopen  = ActionListProp(doc="actions to execute when event source is subscribed and connected")

    def __init__(self, URL : str) -> None:
        super().__init__()
        self.response = ObjectStub(self.id)
        self.readyState = NumberStub(self.id)
        self.withCredentials = BooleanStub(self.id)
        self.URL = URL 

    def json(self):
        return dict(**super().json(), URL=self.URL)
    
    def close(self):
        return Cancel(self.id)
    

class Cancel(BaseAction):

    actionType = ComponentName(default='Cancel')
    
    def __init__(self, id_or_action : str) -> None:
        super().__init__()
        if isinstance(id_or_action, BaseAction):
            self.cancel_id = id_or_action.id
        else:
            self.cancel_id = id_or_action
            
    def json(self) -> Dict[str, Any]:
        return dict(**super().json(), cancelID=self.cancel_id)  
       
    
class SSEVideoSource(EventSource):

    actionType = ComponentName( 'SSEVideo' )


class SetState(BaseAction):

    actionType  = ComponentName(default='setSimpleFSMState')
    componentID = String (default=None, allow_None=True)
    state = String (default=None, allow_None=True)

    def __init__(self, componentID : str, state : str) -> None:
        super().__init__()
        self.componentID = componentID 
        self.state = state 

    def json(self) -> Dict[str, Any]:
        return dict(**super().json(),
            componentID=self.componentID, 
            state=self.state
        )

def setState(componentID : str, state : str) -> SetState:
    return SetState(componentID, state)



class ComponentOutput(BaseAction):

    actionType = ComponentName(default='componentOutput')

    def __init__(self, outputID : str):
        super().__init__()
        self.outputID = outputID

    def json(self) -> Dict[str, Any]:
        return dict(**super().json(),
            outputID=self.outputID, 
        )

    
__all__ = ['setGlobalLocation', 'setLocation', 'setGlobalLocation', 'EventSource', 
        'Cancel', 'setState', 'SSEVideoSource']
     
