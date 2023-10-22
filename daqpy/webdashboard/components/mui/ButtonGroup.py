from ...basecomponents import MUIBaseComponent
from ...baseprops import ComponentName, SelectorProp, BooleanProp



class ButtonGroup(MUIBaseComponent):
	"""
	color               : 'inherit' | 'primary' | 'secondary' | 'error' | 'info' | 'success' | 'warning'
	disabled            : bool
	disableElevation    : bool
	disableFocusRipple  : bool
	disableRipple       : bool
	fullWidth           : bool
	orientation         : 'horizontal' | 'vertical'
	size                : 'small' | 'medium' | 'large'
	variant             : 'contained' | 'outlined' | 'text'
	componentName       : read-only

	color               :  "The color of the component. It supports both default and custom theme colors, which can be added as shown in the palette customization guide." 
	disabled            :  "If true, the component is disabled." 
	disableElevation    :  "If true, no elevation is used." 
	disableFocusRipple  :  "If true, the button keyboard focus ripple is disabled." 
	disableRipple       :  "If true, the button ripple effect is disabled." 
	fullWidth           :  "If true, the buttons will take up the full width of its container." 
	orientation         :  "The component orientation (layout flow direction)."
	size                :  "The size of the component. small is equivalent to the dense button styling." 
	variant             :  "The variant to use."
	componentName       :  "Constant internal value for mapping classes to components in front-end"
	"""
	color               = SelectorProp ( objects = [ 'inherit', 'primary', 'secondary', 'error', 'info', 'success', 'warning'], default = 'primary', allow_None = False,
									doc = "The color of the component. It supports both default and custom theme colors, which can be added as shown in the palette customization guide." ) 
	disabled            = BooleanProp ( default = False, allow_None = False,
									doc = "If true, the component is disabled." ) 
	disableElevation    = BooleanProp ( default = False, allow_None = False,
									doc = "If true, no elevation is used." ) 
	disableFocusRipple  = BooleanProp ( default = False, allow_None = False,
									doc = "If true, the button keyboard focus ripple is disabled." ) 
	disableRipple       = BooleanProp ( default = False, allow_None = False,
									doc = "If true, the button ripple effect is disabled." ) 
	fullWidth           = BooleanProp ( default = False, allow_None = False,
									doc = "If true, the buttons will take up the full width of its container." ) 
	orientation         = SelectorProp ( objects = [ 'horizontal', 'vertical'], default = 'horizontal', allow_None = False,
									doc = "The component orientation (layout flow direction)." )
	size                = SelectorProp ( objects = [ 'small', 'medium', 'large'], default = 'medium', allow_None = False,
									doc = "The size of the component. small is equivalent to the dense button styling." ) 
	variant             = SelectorProp ( objects = [ 'contained', 'outlined', 'text'], default = 'outlined', allow_None = False,
									doc = "The variant to use." )
	componentName       = ComponentName(default = "ContextfulMUIButtonGroup")


