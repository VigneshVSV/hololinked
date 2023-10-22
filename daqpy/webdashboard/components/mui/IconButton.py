from ..basecomponents import MuiBaseComponent, ReactBaseComponent
from ..baseprops import ComponentName, SelectorProp, BooleanProp, StringProp, ChildProp
from ..axios import AxiosHttp
from .Button import ButtonBase


class IconButton(ButtonBase):
	"""
	color               : 'inherit' | 'default' | 'primary' | 'secondary' | 'error' | 'info' | 'success' | 'warning'
	disabled            : bool
	disableFocusRipple  : bool
	disableRipple       : bool
	edge                : 'end' | 'start' | False
	size                : 'small' | 'medium' | 'large'
	centerRipple        : bool
	disableTouchRipple  : bool
	focusRipple         : bool
	focusVisibleClassName : str
	LinkComponent       : component
	onFocusVisible      : AxiosHTTP | makeRequest()
	TouchRippleProps    : dict
	
	color               :  "The color of the component. It supports both default and custom theme colors, which can be added as shown in the palette customization guide." 
	disabled            :  "If true, the component is disabled." 
	disableFocusRipple  :  "If true, the  keyboard focus ripple is disabled." 
	disableRipple       :  "If true, the ripple effect is disabled.⚠️ Without a ripple there is no styling for :focus-visible by default. Be sure to highlight the element by applying separate styles with the .Mui-focusVisible class." 
	edge                :  "If given, uses a negative margin to counteract the padding on one side (this is often helpful for aligning the left or right side of the icon with content above or below, without ruining the border size and shape)."
	size                :  "The size of the component. small is equivalent to the dense button styling." 
	centerRipple        :  "If true, the ripples are centered. They won't start at the cursor interaction position." 
	disableTouchRipple  :  "If true, the touch ripple effect is disabled." 
	focusRipple         :  "If true, the base button will have a keyboard focus ripple." 
	focusVisibleClassName :  "This prop can help identify which element has keyboard focus. The class name will be applied when the element gains the focus through keyboard interaction. It's a polyfill for the CSS :focus-visible selector. The rationale for using this feature is explained here. A polyfill can be used to apply a focus-visible class to other components if needed." 
	LinkComponent       :  "The component used to render a link when the href prop is provided." 
	onFocusVisible      :  "Callback fired when the component is focused with a keyboard. We trigger a onFocus callback too." 
	TouchRippleProps    :  "Props applied to the TouchRipple element." 
	"""
	componentName       = ComponentName ( default = "MuiIconButton" )
	color               = SelectorProp ( objects = [ 'inherit', 'default', 'primary', 'secondary', 'error', 'info', 'success', 'warning'], default = 'default', allow_None = False,
	                                     doc = "The color of the component. It supports both default and custom theme colors, which can be added as shown in the palette customization guide." ) 
	disabled            = BooleanProp  ( default = False, allow_None = False,
	                                     doc = "If true, the component is disabled." ) 
	disableFocusRipple  = BooleanProp  ( default = False, allow_None = False,
	                                     doc = "If true, the  keyboard focus ripple is disabled." ) 
	edge                = SelectorProp ( objects = [ 'end', 'start', False], default = False, allow_None = False,
	                                     doc = "If given, uses a negative margin to counteract the padding on one side (this is often helpful for aligning the left or right side of the icon with content above or below, without ruining the border size and shape)." )
	size                = SelectorProp ( objects = [ 'small', 'medium', 'large'], default = 'medium', allow_None = False,
	                                     doc = "The size of the component. small is equivalent to the dense button styling." ) 
	centerRipple        = BooleanProp  ( default = False, allow_None = False,
	                                     doc = "If true, the ripples are centered. They won't start at the cursor interaction position." ) 
	

class HttpIconButton(IconButton):
	"""
	onClick             : AxiosHttp | makeRequest() 
	color               : 'inherit' | 'default' | 'primary' | 'secondary' | 'error' | 'info' | 'success' | 'warning'
	disabled            : bool
	disableFocusRipple  : bool
	disableRipple       : bool
	edge                : 'end' | 'start' | False
	size                : 'small' | 'medium' | 'large'
	centerRipple        : bool
	disableTouchRipple  : bool
	focusRipple         : bool
	focusVisibleClassName : str
	LinkComponent       : component
	onFocusVisible      : AxiosHTTP | makeRequest()
	TouchRippleProps    : dict

	onClick             : "server resource to reach when button is clicked." 
	color               :  "The color of the component. It supports both default and custom theme colors, which can be added as shown in the palette customization guide." 
	disabled            :  "If true, the component is disabled." 
	disableFocusRipple  :  "If true, the  keyboard focus ripple is disabled." 
	disableRipple       :  "If true, the ripple effect is disabled.⚠️ Without a ripple there is no styling for :focus-visible by default. Be sure to highlight the element by applying separate styles with the .Mui-focusVisible class." 
	edge                :  "If given, uses a negative margin to counteract the padding on one side (this is often helpful for aligning the left or right side of the icon with content above or below, without ruining the border size and shape)."
	size                :  "The size of the component. small is equivalent to the dense button styling." 
	centerRipple        :  "If true, the ripples are centered. They won't start at the cursor interaction position." 
	disableTouchRipple  :  "If true, the touch ripple effect is disabled." 
	focusRipple         :  "If true, the base button will have a keyboard focus ripple." 
	focusVisibleClassName :  "This prop can help identify which element has keyboard focus. The class name will be applied when the element gains the focus through keyboard interaction. It's a polyfill for the CSS :focus-visible selector. The rationale for using this feature is explained here. A polyfill can be used to apply a focus-visible class to other components if needed." 
	LinkComponent       :  "The component used to render a link when the href prop is provided." 
	onFocusVisible      :  "Callback fired when the component is focused with a keyboard. We trigger a onFocus callback too." 
	TouchRippleProps    :  "Props applied to the TouchRipple element." 
	"""
	componentName       = ComponentName ( default = "MuiHttpIconButton" )
	onClick             = ChildProp    ( class_ = AxiosHttp, default = None, allow_None = True,
                                         doc = "server resource to reach when button is clicked." )
	
