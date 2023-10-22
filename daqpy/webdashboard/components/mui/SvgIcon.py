from ..basecomponents import MuiBaseComponent, ReactBaseComponent
from ..baseprops import ComponentNameProp, AnyValueProp, MultiTypeProp, SelectorProp, StringProp, BooleanProp



class SvgIcon(MuiBaseComponent):
	"""
	color           : 'inherit' | 'action' | 'disabled' | 'primary' | 'secondary' | 'error' | 'info' | 'success' | 'warning'
	fontSize        : 'inherit' | 'large' | 'medium' | 'small'
	htmlColor       : str
	inheritViewBox  : bool
	shapeRendering  : str
	titleAccess     : str
	viewBox         : str
	componentName   : read-only

	color           :  "The color of the component. It supports both default and custom theme colors, which can be added as shown in the palette customization guide. You can use the htmlColor prop to apply a color attribute to the SVG element." 
	fontSize        :  "The fontSize applied to the icon. Defaults to 24px, but can be configure to inherit font size."
	htmlColor       :  "Applies a color attribute to the SVG element."
	inheritViewBox  :  "If true, the root node will inherit the custom component's viewBox and the viewBox prop will be ignored. Useful when you want to reference a custom component and have SvgIcon pass that component's viewBox to the root node." 
	shapeRendering  :  "The shape-rendering attribute. The behavior of the different options is described on the MDN Web Docs. If you are having issues with blurry icons you should investigate this prop." 
	titleAccess     :  "Provides a human-readable title for the element that contains it. https://www.w3.org/TR/SVG-access/#Equivalent" 
	viewBox         :  "Allows you to redefine what the coordinates without units mean inside an SVG element. For example, if the SVG element is 500 (width) by 200 (height), and you pass viewBox='0 0 50 20', this means that the coordinates inside the SVG will go from the top left corner (0,0) to bottom right (50,20) and each unit will be worth 10px."
	componentName   :  "Constant internal value for mapping classes to components in front-end"
	"""
	color           = SelectorProp      ( objects = [ 'inherit', 'action', 'disabled', 'primary', 'secondary', 'error', 'info', 'success', 'warning'], default = 'inherit', allow_None = False,
		                                  doc = "The color of the component. It supports both default and custom theme colors, which can be added as shown in the palette customization guide. You can use the htmlColor prop to apply a color attribute to the SVG element." ) 
	fontSize        = SelectorProp      ( objects = [ 'inherit', 'large', 'medium', 'small'], default = 'medium', allow_None = False,
		                                  doc = "The fontSize applied to the icon. Defaults to 24px, but can be configure to inherit font size." )
	htmlColor       = StringProp        ( default = None, allow_None = True,
		                                  doc = "Applies a color attribute to the SVG element." )
	inheritViewBox  = BooleanProp       ( default = False, allow_None = False,
		                                  doc = "If true, the root node will inherit the custom component's viewBox and the viewBox prop will be ignored. Useful when you want to reference a custom component and have SvgIcon pass that component's viewBox to the root node." ) 
	shapeRendering  = StringProp        ( default = None, allow_None = True,
		                                  doc = "The shape-rendering attribute. The behavior of the different options is described on the MDN Web Docs. If you are having issues with blurry icons you should investigate this prop." ) 
	titleAccess     = StringProp        ( default = None, allow_None = True,
		                                  doc = "Provides a human-readable title for the element that contains it. https://www.w3.org/TR/SVG-access/#Equivalent" ) 
	viewBox         = StringProp        ( default = '0 0 24 24', allow_None = False,
		                                  doc = "Allows you to redefine what the coordinates without units mean inside an SVG element. For example, if the SVG element is 500 (width) by 200 (height), and you pass viewBox='0 0 50 20', this means that the coordinates inside the SVG will go from the top left corner (0,0) to bottom right (50,20) and each unit will be worth 10px." )
	componentName   = ComponentNameProp ( default = "MuiSvgIcon",
		                                  doc = "Constant internal value for mapping classes to components in front-end" )


