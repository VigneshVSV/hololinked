import typing
from ...basecomponents import ReactBaseComponent
from ...baseprops import (ComponentName, BooleanProp, StringProp, 
                NodeProp, SelectorProp, ObjectProp, UnsupportedProp, StubProp)
from ...valuestub import StringStub
from ...actions import ActionListProp, ComponentOutput, BaseAction
from .Button import ButtonBase


class Checkbox(ButtonBase):
    """
    Visit https://mui.com/material-ui/api/checkbox/ for React MUI docs

    checked : bool
    checkedIcon : component
    color : None
    defaultChecked : bool
    disabled : bool
    disableRipple : bool
    icon : component
    id : str
    indeterminate : bool
    indeterminateIcon : component
    inputProps : dict
    inputRef : unsupported
    onChange : BaseAction
    required : bool
    size : None
    value : any
    """
    checked = BooleanProp(default=None, allow_None=True,
        doc="If true, the component is checked.")
    checkedIcon = NodeProp(class_=(ReactBaseComponent, str), default="CheckBoxIcon", 
        allow_None=False, doc="The icon to display when the component is checked.")
    color = SelectorProp(objects=['default', 'primary', 'secondary', 'error', 
                'info', 'success', 'warning'], default='primary', allow_None=False,
        doc="The color of the component. It supports both default and \
            custom theme colors, which can be added as shown in the palette customization guide.")
    defaultChecked = BooleanProp(default=None, allow_None=True,
        doc="The default checked state. Use when the component is not controlled.")
    disabled = BooleanProp(default=False, allow_None=False,
        doc="If true, the component is disabled.")
    disableRipple = BooleanProp(default=False, allow_None=False,
        doc="If true, the ripple effect is disabled.")
    icon = NodeProp(class_=(ReactBaseComponent, str), default="CheckBoxOutlineBlankIcon", 
        allow_None=False, doc="The icon to display when the component is unchecked.")
    input_element_id = StringProp(default=None, allow_None=True,
        doc="The id of the input element.")
    indeterminate = BooleanProp(default=False, allow_None=False,
        doc="If true, the component appears indeterminate. This does not set \
            the native input element to indeterminate due to inconsistent behavior across browsers. \
            However, we set a data-indeterminate attribute on the input.")
    indeterminateIcon = NodeProp(class_=(ReactBaseComponent, str), 
        default="IndeterminateCheckBoxIcon", allow_None=False,
        doc="The icon to display when the component is indeterminate.")
    inputProps = ObjectProp(default=None, allow_None=True,
        doc="Attributes applied to the input element.")
    inputRef = UnsupportedProp()
    onChange : typing.List[BaseAction] = ActionListProp(default=None,
        doc="Callback fired when the state is changed.")
    required = BooleanProp(default=False, allow_None=False,
        doc="If true, the input element is required.")
    size = SelectorProp(objects=['medium', 'small'], default='medium', allow_None=False,
        doc="The size of the component. small is equivalent to the dense checkbox styling.")
    value = StubProp(default=None,
        doc="The value of the component. The DOM API casts this to a string. \
            The browser uses on as the default value.")
    componentName = ComponentName(default='ContextfulMUICheckbox')

    def __init__(self, id : str, checked : bool = False, checkedIcon : str = 'CheckboxIcon', color : str = 'primary',
                defaultChecked : bool = False, disabled : bool = False, disableRipple : bool = False,
                icon : str = 'CheckedOutlineBlankIcon', input_element_id : typing.Optional[str] = None, 
                indeterminate : bool = False, indeterminateIcon : str = 'IndeterminateCheckBoxIcon',
                inputProps : typing.Optional[dict] = None, onChange : typing.Optional[BaseAction] = None,
                required : bool = False, size : str = 'medium'):
        self.value = StringStub()
        self.onChange = onChange
        self.onChange.append(ComponentOutput())
        super().__init__(id=id, checked=checked, checkedIcon=checkedIcon, color=color,
            defaultChecked=defaultChecked, disabled=disabled, disableRipple=disableRipple, icon=icon,
            input_element_id=input_element_id, indeterminate=indeterminate, indeterminateIcon=indeterminateIcon,
            inputProps=inputProps, onChange=self.onChange, required=required, size=size) 