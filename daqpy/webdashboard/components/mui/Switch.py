from ...basecomponents import MUIBaseComponent, ReactBaseComponent
from ...baseprops import ComponentName, StubProp, BooleanProp, NodeProp, SelectorProp, StringProp, ObjectProp, UnsupportedProp
from ...axios import RequestProp
from ...valuestub import BooleanStub


class Switch(MUIBaseComponent):
	"""
	checked         : bool
	checkedIcon     : component
	color           : 'default' | 'primary' | 'secondary' | 'error' | 'info' | 'success' | 'warning'
	defaultChecked  : bool
	disabled        : bool
	disableRipple   : bool
	edge            : 'end' | 'start' | false
	icon            : component
	id              : str
	inputProps      : dict
	onChange        : AxiosHttp | makeRequest()
	required        : bool
	size            : 'medium' | 'small'
	value           : any
	componentName   : read-only

	checked         :  "If true, the component is checked." 
	checkedIcon     :  "The icon to display when the component is checked."
	color           :  "The color of the component. It supports both default and custom theme colors, which can be added as shown in the palette customization guide." 
	defaultChecked  :  "The default checked state. Use when the component is not controlled."
	disabled        :  "If true, the component is disabled." 
	disableRipple   :  "If true, the ripple effect is disabled." 
	edge            :  "If given, uses a negative margin to counteract the padding on one side (this is often helpful for aligning the left or right side of the icon with content above or below, without ruining the border size and shape)."
	icon            :  "The icon to display when the component is unchecked."
	id              :  "The id of the input element." 
	inputProps      :  "Attributes applied to the input element." 
	onChange        :  "Callback fired when the state is changed.Signature:function(event: React.ChangeEvent<HTMLInputElement>) => voidevent: The event source of the callback. You can pull out the new value by accessing event.target.value (string). You can pull out the new checked state by accessing event.target.checked (boolean)." 
	required        :  "If true, the input element is required." 
	size            :  "The size of the component. small is equivalent to the dense switch styling." 
	value           :  "The value of the component. The DOM API casts this to a string. The browser uses 'on' as the default value."
	componentName   :  "Constant internal value for mapping classes to components in front-end"
	"""
	checked         = BooleanProp       ( default = False,
		                                  doc = "If true, the component is checked. Note - this is an input value and different from defaultChecked." ) 
	checkedIcon     = NodeProp          ( class_ = ReactBaseComponent, default = None, allow_None = True,
		                                  doc = "The icon to display when the component is checked." )
	color           = SelectorProp      ( objects = [ 'default', 'primary', 'secondary', 'error', 'info', 'success', 'warning'], default = 'primary',
		                                  doc = "The color of the component. It supports both default and custom theme colors, which can be added as shown in the palette customization guide." ) 
	defaultChecked  = BooleanProp       ( default = False,
		                                  doc = "The default checked state. Use when the component is not controlled." )
	disabled        = BooleanProp       ( default = False,
		                                  doc = "If true, the component is disabled." ) 
	disableRipple   = BooleanProp       ( default = False,
		                                  doc = "If true, the ripple effect is disabled." ) 
	edge            = SelectorProp      ( objects = [ 'end', 'start', False], default = False,
		                                  doc = "If given, uses a negative margin to counteract the padding on one side (this is often helpful for aligning the left or right side of the icon with content above or below, without ruining the border size and shape)." )
	icon            = NodeProp          ( class_ = ReactBaseComponent, default = None, allow_None = True,
		                                  doc = "The icon to display when the component is unchecked." )
	inputElementID  = StringProp        ( default = None, allow_None = True,
		                                  doc = "The id of the input element." ) 
	inputProps      = ObjectProp        ( doc = "Attributes applied to the input element." )
	inputRef        = UnsupportedProp   ( doc = "This prop is not supported as it generally executes a client side function")
	onChange        = RequestProp       ( doc = "Request fired when the state is changed. To use the boolean value within the UI, use the `value` prop" ) 
	required        = BooleanProp       ( default = False, 
		                                  doc = "If true, the input element is required." ) 
	size            = SelectorProp      ( objects = [ 'medium', 'small'], default = 'medium',
		                                  doc = "The size of the component. small is equivalent to the dense switch styling." ) 
	value           = StubProp          ( default = BooleanStub(), 
		                                  doc = "The value of the component. The DOM API casts this to a string. The browser uses 'on' as the default value." )
	componentName   = ComponentName     ( default = "MuiSwitch" )


