import typing
from .Button import ButtonBase
from ...basecomponents import ReactBaseComponent, MUIBaseComponent
from ...baseprops import (StringProp, SelectorProp, ComponentName, NumberProp, 
                    Prop, IntegerProp, BooleanProp, ObjectProp, NodeProp, UnsupportedProp)
from ...actions import ActionListProp, BaseAction



class Radio(ButtonBase):
    """
    Visit https://mui.com/material-ui/api/radio/ for React MUI docs

    checked : bool
    checkedIcon : component
    color : None
    disabled : bool
    disableRipple : bool
    icon : component
    id : str
    inputProps : dict
    inputRef : unsupported
    name : str
    onChange : BaseAction
    required : bool
    size : None
    value : any
    """
    checked = BooleanProp(default=None, allow_None=True,
                        doc="If true, the component is checked.")
    checkedIcon = NodeProp(class_=(ReactBaseComponent, str), default=None, allow_None=True,
                        doc="The icon to display when the component is checked.")
    color = SelectorProp(objects=['default', 'primary', 'secondary', 'error', 'info', 'success', 'warning'], 
                        default='primary', allow_None=False,
                        doc="The color of the component. It supports both default and custom theme colors, which can be added as shown in the palette customization guide.")
    disabled = BooleanProp(default=None, allow_None=True,
                        doc="If true, the component is disabled.")
    disableRipple = BooleanProp(default=False, allow_None=False,
                        doc="If true, the ripple effect is disabled.")
    icon = NodeProp(class_=(ReactBaseComponent, str), default=None, allow_None=True,
                        doc="The icon to display when the component is unchecked.")
    id = StringProp(default=None, allow_None=True,
                        doc="The id of the input element.")
    inputProps = ObjectProp(default=None, allow_None=True,
                        doc="Attributes applied to the input element.")
    inputRef = UnsupportedProp()
    name = StringProp(default=None, allow_None=True,
                        doc="Name attribute of the input element.")
    onChange = ActionListProp(default=None,
                        doc="Callback fired when the state is changed.")
    required = BooleanProp(default=False, allow_None=False,
                        doc="If true, the input element is required.")
    size = SelectorProp(objects=['medium', 'small'], default='medium', allow_None=False,
                        doc="The size of the component. small is equivalent to the dense radio styling.")
    value = Prop(default=None,
                        doc="The value of the component. The DOM API casts this to a string.")
    componentName = ComponentName(default='ContextfulMUIRadio')

    def __init__(self, id : str, checked : bool = None, checkedIcon : ReactBaseComponent = None, 
                classes : dict = None, color : str = 'primary', disabled : bool = None, disableRipple : bool = False, 
                icon : ReactBaseComponent = None, inputProps : dict = None,
                name : str = None, onChange : BaseAction = None, required : bool = False, size : str = 'medium', 
                sx : typing.Dict[str, typing.Any] = None, value : str = None) -> None:
        super().__init__(id=id, checked=checked, checkedIcon=checkedIcon, classes=classes, color=color, 
                disabled=disabled, disableRipple=disableRipple, icon=icon, inputProps=inputProps, 
                name=name, onChange=onChange, required=required, size=size, sx=sx, value=value)

