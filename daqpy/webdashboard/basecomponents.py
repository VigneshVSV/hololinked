import typing

from ..param.parameters import TypedList as TypedListProp, String, ClassSelector
from ..param.exceptions import raise_ValueError
from ..param import edit_constant, Parameterized, Parameter

from .baseprops import (TypedListProp, NodeProp, StringProp, HTMLid, ComponentName, SelectorProp, 
                    StubProp, dataGrid, ObjectProp, IntegerProp, BooleanProp, NumberProp,
                    TupleSelectorProp)
from .actions import ComponentOutput, ComponentOutputProp
from .exceptions import *
from .statemachine import StateMachineProp
from .valuestub import ValueStub
from .utils import unique_id




UICOMPONENTS = 'UIcomponents'
ACTIONS = 'actions'
NODES = 'nodes'

class ReactBaseComponent(Parameterized):
    """
    Validator class that serves as the information container for all components in the React frontend. The 
    parameters of this class are serialized to JSON, deserialized at frontend and applied onto components as props, 
    i.e. this class is a JSON specfication generator. 

    Attributes:

    id : The html id of the component, allowed characters are <
    tree : read-only, used for generating unique key prop for components, it denotes the nesting of the component based on id.
    repr : read-only, used for raising meaningful Exceptions 
    stateMachine : specify state machine for front end components
    """
    componentName = ComponentName(default='ReactBaseComponent')
    id = HTMLid(default=None) 
    tree = String(default=None, allow_None=True, constant=True) 
    stateMachine = StateMachineProp(default=None, allow_None=True) 
    # outputID           = ActionID()  
    
    def __init__(self, id : str, **params):
        # id separated in kwargs to force the user to give it 
        self.id = id # & also be set as the first parameter before all other parameters
        super().__init__(**params)
        parameters = self.parameters.descriptors
        with edit_constant(parameters['tree']):
            self.tree = id
        try:
            """
            Multiple action_result stubs are possible however, only one internal action stub is possible.
            For example, a button's action may be to store the number of clicks, make request etc., however 
            only number of clicks can be an internal action although any number of other stubs may access this value.
            """
            self.action_id = unique_id('actionid_')     
            # if self.outputID is None:
            #     with edit_constant(parameters['outputID']):
            #         self.outputID = action_id   
            for param in parameters.values():
                if isinstance(param, StubProp):
                    stub = param.__get__(self, type(self))
                    stub.create_base_info(self.action_id)
            for param in parameters.values():
                if isinstance(param, ComponentOutputProp):
                    output_action = ComponentOutput(outputID=self.action_id)
                    param.__set__(self, output_action)
                    stub.create_base_info(output_action.id)
        except Exception as ex:
            raise RuntimeError(f"stub information improperly configured for component {self.componentName} : received exception : {str(ex)}")

    def validate(self):
        """
        use this function in a child component to perform type checking and assignment which is appropriate at JSON creation time i.e.
        the user has sufficient space to manipulate parts of the props of the component until JSON is created. 
        Dont forget to call super().secondStagePropCheck as its mandatory to ensure state machine of the
        """
        if self.id is None:
            raise_ValueError("ID cannot be None for {}".format(self.componentName), self)
        
    def __str__(self):
        if self.id is not None:
            return "{} with HTML id : {}".format(self.componentName, self.id)
        else: 
            return self.componentName
        
    def json(self, JSON : typing.Dict[str, typing.Any] = {}) -> typing.Dict[str, typing.Any]:
        self.validate()
        JSON[UICOMPONENTS].update({self.id : self.parameters.serialize(mode='FrontendJSONSpec')})
        JSON[ACTIONS].update(JSON[UICOMPONENTS][self.id].pop(ACTIONS, {}))
        return JSON
    


class BaseComponentWithChildren(ReactBaseComponent):

    children = TypedListProp(doc="children of the component",
                        item_type=(ReactBaseComponent, ValueStub, str))
  
    def addComponent(self, *args : ReactBaseComponent) -> None:
        for component in args:
            if component.componentName == 'ReactApp':
                raise TypeError("ReactApp can never be child of any component")
            if self.children is None:
                self.children = [component] 
            else:
                self.children.append(component)

    def json(self, JSON: typing.Dict[str, typing.Any] = {UICOMPONENTS : {}, ACTIONS : {}}) -> typing.Dict[str, typing.Any]:
        super().json(JSON)
        if self.children != None and len(self.children) > 0:
            for child in self.children:
                if isinstance(child, ReactBaseComponent):
                    with edit_constant(child.parameters.descriptors['tree']):
                        if child.id is None:
                            raise_PropError(AttributeError("object {} id is None, cannot create JSON".format(child)), 
                                            self, 'children')
                        child.tree = self.tree + '/' + child.id
                    child.json(JSON)
        return JSON
    

class ReactGridLayout(BaseComponentWithChildren): 

    componentName = ComponentName(default="ContextfulRGL")
    width            = IntegerProp(default=300, 
                            doc='This allows setting the initial width on the server side. \
                            This is required unless using the HOC <WidthProvider> or similar')
    autoSize         = BooleanProp(default=False, 
                            doc='If true, the container height swells and contracts to fit contents')
    cols             = IntegerProp(default=300, doc='Number of columns in this layout')
    draggableCancel  = StringProp(default='', 
                            doc='A CSS selector for tags that will not be draggable. \
                                For example: draggableCancel: .MyNonDraggableAreaClassName \
                                If you forget the leading . it will not work. \
                                .react-resizable-handle" is always prepended to this value.')
    draggableHandle  = StringProp(default='', 
                            doc='CSS selector for tags that will act as the draggable handle.\
                                For example: draggableHandle: .MyDragHandleClassName \
                                If you forget the leading . it will not work.')
    compactType      = SelectorProp(default=None, objects=[None, 'vertical', 'horizontal'], 
                            doc='compaction type')
    layout           = ObjectProp(default=None, 
                            doc='Layout is an array of object with the format: \
                                {x: number, y: number, w: number, h: number} \
                                The index into the layout must match the key used on each item component. \
                                If you choose to use custom keys, you can specify that key in the layout \
                                array objects like so: \
                                {i: string, x: number, y: number, w: number, h: number} \
                                If not provided, use data-grid props on children')
    margin           = Parameter(default=[10, 10], doc='')
    isDraggable      = BooleanProp(default=False)
    isResizable      = BooleanProp(default=False)
    isBounded        = BooleanProp(default=False)
    preventCollision = BooleanProp(default=False, 
                            doc="If true, grid items won't change position when being \
                                    dragged over. If `allowOverlap` is still false, \
                                    this simply won't allow one to drop on an existing object.")
    containerPadding = Parameter(default=[10, 10], doc='')
    rowHeight        = IntegerProp(default=300, bounds=(0, None),
                            doc='Rows have a static height, but you can change this based on breakpoints if you like.')
    useCSSTransforms = BooleanProp(default=True, 
                            doc='Uses CSS3 translate() instead of position top/left. \
                                This makes about 6x faster paint performance')
    transformScale   = NumberProp(default=1, doc='')
    resizeHandles    = TupleSelectorProp(default=['se'], objects=['s', 'w', 'e', 'n' , 'sw', 'nw', 'se', 'ne'], 
                            doc='Defines which resize handles should be rendered', accept_list=True)
    resizeHandle     = NodeProp(default=None, class_=ReactBaseComponent, allow_None=True, 
                            doc='Custom component for resize handles')
    
    def validate(self):
        for child in self.children:
            if not hasattr(child, "RGLDataGrid"):
                raise_PropError(AttributeError(
                    "component {} with id '{}' cannot be child of ReactGridLayout. It does not have a built-in dataGrid support.".format(
                        child.__class__.__name__, child.id)), self, "children")
            elif child.RGLDataGrid is None: # type: ignore
                raise_PropError(ValueError(
                    "component {} with id '{}', being child of ReactGridLayout, dataGrid prop cannot be unassigned or None".format(
                        child.__class__.__name__, child.id)), self, "children")
        super().validate()
        

class Page(BaseComponentWithChildren):
    """
    Adds a new page in app. All components by default can be only within a page. Its not possible to
    directly add a component to an app without the page. If only one page exists, its shown automatically. 
    For a list of pages, its possible to set URL paths and show available pages.
    """
    componentName = ComponentName(default="ContextfulPage")
    route = StringProp(default='/', regex=r'^\/[a-zA-Z][a-zA-Z0-9]*$|^\/$', 
                    doc="route for a page, mandatory if there are many pages, must be unique")
    name = StringProp(default=None, allow_None=True, doc="display name for a page")

    def __init__(self, id : str, route : str = '/', name : typing.Optional[str] = None, 
                **params):
        super().__init__(id=id, route=route, name=name, **params)


class RGLBaseComponent(BaseComponentWithChildren):
    """
    All components which can be child of a react-grid-layout grid must be a child of this class,
    """
    componentName = ComponentName (default='ReactGridLayoutBaseComponent' )
    RGLDataGrid = ClassSelector(default=None,  allow_None=True, class_=dataGrid, 
                        doc="use this prop to specify location in a ReactGridLayout component")
    
    def __init__(self, id : str, dataGrid : typing.Optional[dataGrid] = None, **params):
        super().__init__(id=id, RGLDataGrid=dataGrid, **params)
  

class MUIBaseComponent(RGLBaseComponent):
    """
    All material UI components must be a child of this class. sx, styling, classes & 'component' prop
    are already by default available. This component is also react-grid-layout compatible.
    """
    componentName = ComponentName(default="MUIBaseComponent")
    sx = ObjectProp(doc="""The system prop that allows defining system overrides as well as additional CSS styles. 
                    See the `sx` page for more details.""")
    component = NodeProp(class_=(ReactBaseComponent, str), default=None, allow_None=True, 
                        doc="The component used for the root node. Either a string to use a HTML element or a component.")
    styling = ObjectProp() 
    classes = ObjectProp()

    def __init__(self, id : str, dataGrid : typing.Optional[dataGrid] = None, 
                sx : typing.Optional[typing.Dict[str, typing.Any]] = None, 
                component : typing.Optional[typing.Union[str, ReactBaseComponent]] = None,
                styling : typing.Optional[typing.Dict[str, typing.Any]] = None, 
                classes : typing.Optional[typing.Dict[str, typing.Any]] = None, 
                **params):
        super().__init__(id=id, dataGrid=dataGrid, sx=sx, component=component, 
                    styling=styling, classes=classes, **params)




__all__ = ['ReactBaseComponent', 'ReactGridLayout', 'RGLBaseComponent', 'Page', 'MUIBaseComponent',
        'BaseComponentWithChildren']
 