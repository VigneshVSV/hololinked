
from ....param import Parameter
from ...basecomponents import MUIBaseComponent, ReactBaseComponent
from ...baseprops import ComponentName, StringProp, BooleanProp, SelectorProp, NodeProp, IntegerProp, StubProp, ObjectProp
from ...valuestub import StringStub
from ...actions import ComponentOutputProp



class FormControl(MUIBaseComponent):
    """
    color          : 'primary' | 'secondary' | 'error' | 'info' | 'success' | 'warning'
    disabled       : bool
    error          : bool
    focused        : bool
    fullWidth      : bool
    hiddenLabel    : bool
    margin         : 'dense' | 'none' | 'normal'
    required       : bool
    size           : 'medium' | 'small'
    variant        : 'filled' | 'outlined' | 'standard'
    componentName  : read-only

    color          :  "The color of the component. It supports both default and custom theme colors, which can be added as shown in the palette customization guide." 
    disabled       :  "If true, the label, input and helper text should be displayed in a disabled state." 
    error          :  "If true, the label is displayed in an error state." 
    focused        :  "If true, the component is displayed in focused state." 
    fullWidth      :  "If true, the component will take up the full width of its container." 
    hiddenLabel    :  "If true, the label is hidden. This is used to increase density for a FilledInput. Be sure to add aria-label to the input element." 
    margin         :  "If dense or normal, will adjust vertical spacing of this and contained components." 
    required       :  "If true, the label will indicate that the input is required." 
    size           :  "The size of the component."
    variant        :  "The variant to use."
    componentName  :  "Constant internal value for mapping classes to components in front-end"
    """
    color          = SelectorProp      ( objects = ['primary', 'secondary', 'error', 'info', 'success', 'warning'], default = 'primary',
                                        doc = "The color of the component. It supports both default and custom theme colors, which can be added as shown in the palette customization guide." )
    disabled       = BooleanProp       ( default = False,
                                        doc = "If true, the label, input and helper text should be displayed in a disabled state." )
    error          = BooleanProp       ( default = False, 
                                        doc = "If true, the label is displayed in an error state." )
    focused        = BooleanProp       ( default = False, 
                                        doc = "If true, the component is displayed in focused state." )
    fullWidth      = BooleanProp       ( default = False, 
                                        doc = "If true, the component will take up the full width of its container." )
    hiddenLabel    = BooleanProp       ( default = False,
                                        doc = "If true, the label is hidden. This is used to increase density for a FilledInput. Be sure to add aria-label to the input element." )
    margin         = SelectorProp      ( objects = ['dense', 'none', 'normal'], default = 'none', 
                                        doc = "If dense or normal, will adjust vertical spacing of this and contained components." )
    required       = BooleanProp       ( default = False,
                                        doc = "If true, the label will indicate that the input is required." )
    size           = SelectorProp      ( objects = [ 'medium', 'small'], default = 'medium',
                                        doc = "The size of the component." )
    variant        = SelectorProp      ( objects = [ 'filled', 'outlined', 'standard'], default = 'outlined',
                                        doc = "The variant to use." )
    componentName  = ComponentName     ( default = "FormControl" )


class TextField(FormControl):
    """
    autoComplete         : str
    autoFocus            : bool
    color                : 'primary' | 'secondary' | 'error' | 'info' | 'success' | 'warning'
    defaultValue         : any
    disabled             : bool
    error                : bool
    FormHelperTextProps  : dict
    fullWidth            : bool
    helperText           : component
    id                   : str
    InputLabelProps      : dict
    inputProps           : dict
    InputProps           : dict
    label                : component
    margin               : 'dense' | 'none' | 'normal'
    maxRows              : float | str
    minRows              : float | str
    multiline            : bool
    name                 : str
    onChange             : AxiosHttp | makeRequest()
    placeholder          : str
    required             : bool
    rows                 : float | str
    select               : bool
    SelectProps          : dict
    size                 : 'medium' | 'small'
    type                 : str
    value                : any
    variant              : 'filled' | 'outlined' | 'standard'
    focused              : bool
    hiddenLabel          : bool
    componentName        : read-only

    autoComplete         :  "This prop helps users to fill forms faster, especially on mobile devices. The name can be confusing, as it's more like an autofill. You can learn more about it following the specification." 
    autoFocus            :  "If true, the input element is focused during the first mount." 
    color                :  "The color of the component. It supports both default and custom theme colors, which can be added as shown in the palette customization guide." 
    defaultValue         :  "The default value. Use when the component is not controlled."
    disabled             :  "If true, the component is disabled." 
    error                :  "If true, the label is displayed in an error state." 
    FormHelperTextProps  :  "Props applied to the FormHelperText element." 
    fullWidth            :  "If true, the input will take up the full width of its container." 
    helperText           :  "The helper text content."
    id                   :  "The id of the input element. Use this prop to make label and helperText accessible for screen readers." 
    InputLabelProps      :  "Props applied to the InputLabel element. Pointer events like onClick are enabled if and only if shrink is true." 
    inputProps           :  "Attributes applied to the input element." 
    InputProps           :  "Props applied to the Input element. It will be a FilledInput, OutlinedInput or Input component depending on the variant prop value." 
    label                :  "The label content."
    margin               :  "If dense or normal, will adjust vertical spacing of this and contained components." 
    maxRows              :  "Maximum number of rows to display when multiline option is set to true."
    minRows              :  "Minimum number of rows to display when multiline option is set to true."
    multiline            :  "If true, a textarea element is rendered instead of an input." 
    name                 :  "Name attribute of the input element." 
    onChange             :  "Callback fired when the value is changed.Signature:function(event: object) => voidevent: The event source of the callback. You can pull out the new value by accessing event.target.value (string)." 
    placeholder          :  "The short hint displayed in the input before the user enters a value." 
    required             :  "If true, the label is displayed as required and the input element is required." 
    rows                 :  "Number of rows to display when multiline option is set to true."
    select               :  "Render a Select element while passing the Input element to Select as input parameter. If this option is set you must pass the options of the select as children." 
    SelectProps          :  "Props applied to the Select element." 
    size                 :  "The size of the component."
    type                 :  "Type of the input element. It should be a valid HTML5 input type." 
    value                :  "The value of the input element, required for a controlled component." 
    variant              :  "The variant to use."
    focused              :  "If true, the component is displayed in focused state." 
    hiddenLabel          :  "If true, the label is hidden. This is used to increase density for a FilledInput. Be sure to add aria-label to the input element." 
    componentName        :  "Constant internal value for mapping classes to components in front-end"
    """
    autoComplete         = StringProp        ( default = None, allow_None = True,
                                              doc = "This prop helps users to fill forms faster, especially on mobile devices. The name can be confusing, as it's more like an autofill. You can learn more about it following the specification." )
    autoFocus            = BooleanProp       ( default = False, 
                                              doc = "If true, the input element is focused during the first mount." )
    defaultValue         = Parameter         ( default = None, allow_None = True,
                                              doc = "The default value. Use when the component is not controlled." )
    FormHelperTextProps  = ObjectProp        ( default = None, 
                                              doc = "Props applied to the FormHelperText element." )
    helperText           = NodeProp          ( class_ = (ReactBaseComponent, str), default = None, allow_None = True,
                                              doc = "The helper text content." )
    InputLabelProps      = ObjectProp        ( default = None, allow_None = True,
                                              doc = "Props applied to the InputLabel element. Pointer events like onClick are enabled if and only if shrink is true." )
    inputProps           = ObjectProp        ( default = {}, doc = "Attributes applied to the input element." )
    InputProps           = ObjectProp        ( default = None, allow_None = True,
                                              doc = "Props applied to the Input element. It will be a FilledInput, OutlinedInput or Input component depending on the variant prop value." ) 
    label                = NodeProp          ( class_ = (ReactBaseComponent, str), default = None, allow_None = True,
                                              doc = "The label content." )
    maxRows              = IntegerProp	     ( default = None, allow_None = True,
                                             doc = "Maximum number of rows to display when multiline option is set to true." )
    minRows              = IntegerProp	     ( default = None, allow_None = True,
                                             doc = "Minimum number of rows to display when multiline option is set to true." )
    multiline            = BooleanProp       ( default = False,
                                              doc = "If true, a textarea element is rendered instead of an input." )
    name                 = StringProp        ( default = None, allow_None = True,
                                              doc = "Name attribute of the input element." )
    onChange             = ComponentOutputProp() 
    placeholder          = StringProp        ( default = None, allow_None = True,
                                              doc = "The short hint displayed in the input before the user enters a value." )
    required             = BooleanProp       ( default = False,
                                              doc = "If true, the label is displayed as required and the input element is required." )
    rows                 = IntegerProp   	 ( default = None, allow_None = True,
                                            doc = "Number of rows to display when multiline option is set to true." )
    select               = BooleanProp       ( default = False,
                                              doc = "Render a Select element while passing the Input element to Select as input parameter. If this option is set you must pass the options of the select as children." )
    SelectProps          = ObjectProp        ( default = None, 
                                              doc = "Props applied to the Select element." )
    componentName        = ComponentName     ( default = "ContextfulMUITextField" )
    value                = StubProp          (doc = """The value of the own element (symbolic JSON specification based pointer - the actual value is in the browser). 
                                              For textfield, this is the content of the textfield.""")
   
    def __init__(self, **params):
        self.inputProps = {} # above initialisation is a shared dict
        self.value = StringStub()
        super().__init__(**params)
        
    