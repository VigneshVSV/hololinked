from ...basecomponents import MUIBaseComponent, ReactBaseComponent
from ...baseprops import (NodeProp, ComponentName, Prop, IntegerProp, NumberProp, 
                        StringProp, BooleanProp, StubProp)
from ...actions import ActionListProp, ComponentOutput
from ...valuestub import StringStub



class FormGroup(MUIBaseComponent):
    """
    Visit https://mui.com/material-ui/api/form-group/ for React MUI docs

    row : bool
    """
    row = BooleanProp(default=False, allow_None=False,
            doc="Display group of elements in a compact row.")
    componentName = ComponentName(default="ContextfulMUIFormGroup")



class RadioGroup(FormGroup):
    """
    Visit https://mui.com/material-ui/api/radio-group/ for React MUI docs
    defaultValue : any
    name : str
    onChange : list of actions, please only append after init. 
    value : stub 
    """
    defaultValue = Prop(default=None,
        doc="The default value. Use when the component is not controlled.")
    name = StringProp(default=None, allow_None=True,
        doc="The name used to reference the value of the control. \
        If you don't provide this prop, it falls back to a randomly generated name.")
    onChange = ActionListProp(default=None,
        doc="Callback fired when a radio button is selected.")
    value = StubProp(default=None,
         doc="Value of the selected radio button. The DOM API casts this to a string.")
    componentName = ComponentName(default="ContextfulMUIRadioGroup")

    def __init__(self, id: str, **params):
        self.value = StringStub()
        super().__init__(id=id, **params)
        self.onChange = [ComponentOutput(outputID=self.action_id)] + params.get('onChange', [])