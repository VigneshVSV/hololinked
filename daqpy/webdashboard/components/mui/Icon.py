from ..basecomponents import MuiBaseComponent
from ..baseprops import StringProp, SelectorProp, ComponentName



class Icon(MuiBaseComponent):
	"""
	baseClassName  : str
	color          : 'inherit' | 'action' | 'disabled' | 'primary' | 'secondary' | 'error' | 'info' | 'success' | 'warning'
	fontSize       : 'inherit' | 'large' | 'medium' | 'small'
	componentName  : read-only

	componentName  :  "Constant internal value for mapping classes to components in front-end"
	baseClassName  :  "The base class applied to the icon. Defaults to 'material-icons', but can be changed to any other base class that suits the icon font you're using (e.g. material-icons-rounded, fas, etc)."
	color          :  "The color of the component. It supports both default and custom theme colors, which can be added as shown in the palette customization guide." 
	fontSize       :  "The fontSize applied to the icon. Defaults to 24px, but can be configure to inherit font size."
	"""
	componentName  = ComponentName ( default = "MuiIcon",
                                    doc = "Constant internal value for mapping classes to components in front-end" )
	baseClassName  = StringProp        ( default = 'material-icons', allow_None = False,
		                                 doc = "The base class applied to the icon. Defaults to 'material-icons', but can be changed to any other base class that suits the icon font you're using (e.g. material-icons-rounded, fas, etc)." )
	color          = SelectorProp      ( objects = [ 'inherit', 'action', 'disabled', 'primary', 'secondary', 'error', 'info', 'success', 'warning'], default = 'inherit', allow_None = False,
		                                 doc = "The color of the component. It supports both default and custom theme colors, which can be added as shown in the palette customization guide." ) 
	fontSize       = SelectorProp      ( objects = [ 'inherit', 'large', 'medium', 'small'], default = 'medium', allow_None = False,
		                                 doc = "The fontSize applied to the icon. Defaults to 24px, but can be configure to inherit font size." )


