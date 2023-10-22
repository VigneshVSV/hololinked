import typing
from ...basecomponents import MUIBaseComponent, ReactBaseComponent
from ...baseprops import (BooleanProp, UnsupportedProp, NodeProp, ComponentName, 
                        Prop, SelectorProp, ObjectProp)
from ...actions import ActionListProp, BaseAction
from .Radio import Radio


class FormControlLabel(MUIBaseComponent):
    """
    Visit https://mui.com/material-ui/api/form-control-label/ for React MUI docs

    checked : bool
    componentProps : dict[str, Any]
    disabled : bool
    disableTypography : bool
    inputRef : unsupported
    label : component
    labelPlacement : None
    slotProps : dict[str, Any]
    onChange : BaseAction
    required : bool
    value : any
    """
    control = NodeProp(class_=(Radio,), default=None, allow_None=True,
                        doc="control component for the radio")
    checked = BooleanProp(default=None, allow_None=True,
                        doc="If true, the component appears selected.")
    componentProps = ObjectProp(doc="The props used for each slot inside")
    disabled = BooleanProp(default=None, allow_None=True,
                        doc="If true, the control is disabled.")
    disableTypography = BooleanProp(default=None, allow_None=True,
                        doc="If true, the label is rendered as it is passed without an additional typography node.")
    inputRef = UnsupportedProp(doc="Pass a ref to the input element.")
    label = NodeProp(class_=(ReactBaseComponent, str), default=None, allow_None=True,
                        doc="A text or an element to be used in an enclosing label element.")
    labelPlacement = SelectorProp(objects=['bottom', 'end', 'start', 'top'], default='end', allow_None=False,
                        doc="The position of the label.")
    onChange = ActionListProp(default=None,
                        doc="Callback fired when the state is changed.")
    required = BooleanProp(default=None, allow_None=True,
                        doc="If true, the label will indicate that the input is required.")
    slotProps = ObjectProp(doc="The props used for each slot inside.")
    value = Prop(default=None, allow_None=True,
                        doc="The value of the component.")
    componentName = ComponentName(default='ContextfulMUIFormControlLabel')

    def __init__(self, id : str, control : ReactBaseComponent, checked : bool = None, classes : dict = None, 
                componentProps : typing.Dict[str, typing.Any] = None, disabled : bool = None, 
                disableTypography : bool = None, label : ReactBaseComponent = None, labelPlacement : str = 'end', 
                onChange : BaseAction = None, required : bool = None, slotProps : typing.Dict[str, typing.Any] = None, 
                sx : typing.Dict[str, typing.Any] = None, value : str = None) -> None:
        super().__init__(id=id, control=control, checked=checked, classes=classes, disabled=disabled, 
                    disableTypography=disableTypography, 
                    label=label, labelPlacement=labelPlacement, onChange=onChange, required=required, sx=sx,
                    value=value)

