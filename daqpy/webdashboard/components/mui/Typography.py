from ...basecomponents import MUIBaseComponent, ReactBaseComponent
from ...baseprops import ComponentName, AnyValueProp, MultiTypeProp, SelectorProp, BooleanProp, DictProp



class Typography(MUIBaseComponent):
	"""
	align           : 'center' | 'inherit' | 'justify' | 'left' | 'right'
	gutterBottom    : bool
	noWrap          : bool
	paragraph       : bool
	variant         : 'body1' | 'body2' | 'button' | 'caption' | 'h1' | 'h2' | 'h3' | 'h4' | 'h5' | 'h6' | 'inherit' | 'overline' | 'subtitle1' | 'subtitle2'
	variantMapping  : dict
	componentName   : read-only

	align           :  "Set the text-align on the component."
	gutterBottom    :  "If true, the text will have a bottom margin." 
	noWrap          :  "If true, the text will not wrap, but instead will truncate with a text overflow ellipsis.Note that text overflow can only happen with block or inline-block level elements (the element needs to have a width in order to overflow)." 
	paragraph       :  "If true, the element will be a paragraph element." 
	variant         :  "Applies the theme typography styles."
	variantMapping  :  "The component maps the variant prop to a range of different HTML element types. For instance, subtitle1 to <h6>. If you wish to change that mapping, you can provide your own. Alternatively, you can use the component prop." 
	componentName   :  "Constant internal value for mapping classes to components in front-end"
	"""
	align           = SelectorProp      ( objects = [ 'center', 'inherit', 'justify', 'left', 'right'], default = 'inherit', allow_None = False,
		                                  doc = "Set the text-align on the component." )
	gutterBottom    = BooleanProp       ( default = False, allow_None = False,
		                                  doc = "If true, the text will have a bottom margin." ) 
	noWrap          = BooleanProp       ( default = False, allow_None = False,
		                                  doc = "If true, the text will not wrap, but instead will truncate with a text overflow ellipsis.Note that text overflow can only happen with block or inline-block level elements (the element needs to have a width in order to overflow)." ) 
	paragraph       = BooleanProp       ( default = False, allow_None = False,
		                                  doc = "If true, the element will be a paragraph element." ) 
	variant         = SelectorProp      ( objects = [ 'body1', 'body2', 'button', 'caption', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'inherit', 'overline', 'subtitle1', 'subtitle2'], default = 'body1', allow_None = False,
		                                  doc = "Applies the theme typography styles." )
	variantMapping  = DictProp          ( default = None, key_type = str, allow_None = True,
		                                  doc = "The component maps the variant prop to a range of different HTML element types. For instance, subtitle1 to <h6>. If you wish to change that mapping, you can provide your own. Alternatively, you can use the component prop." ) 
	componentName   = ComponentName ( default = "MuiTypography" )


