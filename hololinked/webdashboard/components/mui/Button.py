from ...basecomponents import MUIBaseComponent, ReactBaseComponent
from ...baseprops import ComponentName, SelectorProp, BooleanProp, NodeProp, StringProp, ObjectProp, UnsupportedProp
from ...actions import ActionProp



class ButtonBase(MUIBaseComponent):
    """
    centerRipple           : bool
    disabled               : bool
    disableRipple          : bool
    disableTouchRipple     : bool
    focusRipple            : bool
    focusVisibleClassName  : str
    LinkComponent          : component
    onFocusVisible         : AxiosRequestConfig | makeRequest()
    TouchRippleProps       : dict

    centerRipple           :  "If true, the ripples are centered. They won't start at the cursor interaction position." 
    disabled               :  "If true, the component is disabled." 
    disableRipple          :  "If true, the ripple effect is disabled.⚠️ Without a ripple there is no styling for :focus-visible by default. Be sure to highlight the element by applying separate styles with the .Mui-focusVisible class." 
    disableTouchRipple     :  "If true, the touch ripple effect is disabled." 
    focusRipple            :  "If true, the base button will have a keyboard focus ripple." 
    focusVisibleClassName  :  "This prop can help identify which element has keyboard focus. The class name will be applied when the element gains the focus through keyboard interaction. It's a polyfill for the CSS :focus-visible selector. The rationale for using this feature is explained here. A polyfill can be used to apply a focus-visible class to other components if needed." 
    LinkComponent          :  "The component used to render a link when the href prop is provided." 
    onFocusVisible         :  "Callback fired when the component is focused with a keyboard. We trigger a onFocus callback too." 
    TouchRippleProps       :  "Props applied to the TouchRipple element." 
    touchRippleRef         :  "A ref that points to the TouchRipple element." 
    """
    
    componentName = ComponentName(default="ContextfulMUIButtonBase")
    centerRipple = BooleanProp(default=False,
        doc="If true, the ripples are centered. They won't start at the cursor interaction position.") 
    disabled = BooleanProp(default=False,
        doc="If true, the component is disabled.") 
    disableRipple = BooleanProp (default=False,
        doc="If true, the ripple effect is disabled.⚠️ Without a ripple there is no styling for :focus-visible by default. \
            Be sure to highlight the element by applying separate styles with the .Mui-focusVisible class." ) 
    disableTouchRipple = BooleanProp(default = False,
        doc="If true, the touch ripple effect is disabled.") 
    focusRipple = BooleanProp(default = False,
        doc="If true, the base button will have a keyboard focus ripple.") 
    focusVisibleClassName = StringProp(default=None, allow_None=True,
        doc="This prop can help identify which element has keyboard focus. \
            The class name will be applied when the element gains the focus through keyboard interaction. \
            It's a polyfill for the CSS :focus-visible selector. The rationale for using this feature is explained here. \
            A polyfill can be used to apply a focus-visible class to other components if needed." ) 
    LinkComponent = NodeProp(class_ = (ReactBaseComponent, str), default = 'a', 
        doc="The component used to render a link when the href prop is provided.") 
    TouchRippleProps = ObjectProp(doc="Props applied to the TouchRipple element.") 
    touchRippleRef = UnsupportedProp()
    onFocusVisible = UnsupportedProp() 
    action = UnsupportedProp()

 


class Button(ButtonBase):
    """
    color               : 'inherit' | 'primary' | 'secondary' | 'success' | 'error' | 'info' | 'warning'
    disableElevation    : bool
    disableFocusRipple  : bool
    endIcon             : component
    fullWidth           : bool
    size                : 'small' | 'medium' | 'large'
    startIcon           : component
    variant             : 'contained' | 'outlined' | 'text'

    color               :  "The color of the component. It supports both default and custom theme colors, which can be added as shown in the palette customization guide." 
    disableElevation    :  "If true, no elevation is used." 
    disableFocusRipple  :  "If true, the  keyboard focus ripple is disabled." 
    endIcon             :  "Element placed after the children."
    fullWidth           :  "If true, the button will take up the full width of its container." 
    size                :  "The size of the component. small is equivalent to the dense button styling." 
    startIcon           :  "Element placed before the children."
    variant             :  "The variant to use."
    """
    componentName       = ComponentName ( default = "ContextfulMUIButton" )
    color               = SelectorProp ( objects = [ 'inherit', 'primary', 'secondary', 'success', 'error', 'info', 'warning'], default = 'primary', 
                                    doc = "The color of the component. It supports both default and custom theme colors, which can be added as shown in the palette customization guide." ) 
    disableElevation    = BooleanProp  ( default = False, 
                                    doc = "If true, no elevation is used." ) 
    disableRipple       = BooleanProp  ( default = False, 
                                    doc = "If true, the ripple effect is disabled.⚠️ Without a ripple there is no styling for :focus-visible by default. Be sure to highlight the element by applying separate styles with the .Mui-focusVisible class." ) 
    endIcon             = NodeProp    ( class_ = ReactBaseComponent, default = None, allow_None = True,
                                    doc = "Element placed after the children." )
    fullWidth           = BooleanProp  ( default = False, 
                                    doc = "If true, the button will take up the full width of its container." ) 
    size                = SelectorProp ( objects = [ 'small', 'medium', 'large'], default = 'medium', 
                                    doc = "The size of the component. small is equivalent to the dense button styling." ) 
    startIcon           = NodeProp    ( class_ = ReactBaseComponent, default = None, allow_None = True,
                                    doc = "Element placed before the children." )
    variant             = SelectorProp ( objects = [ 'contained', 'outlined', 'text'], default = 'text',
                                    doc = "The variant to use." )
    onClick             = ActionProp   ( default = None, 
                                    doc = "server resource to reach when button is clicked." )


class hrefButton(Button):
    """
    href                   : str 
    centerRipple           : bool
    disabled               : bool
    disableRipple          : bool
    disableTouchRipple     : bool
    focusRipple            : bool
    focusVisibleClassName  : str
    LinkComponent          : component
    onFocusVisible         : AxiosRequestConfig | makeRequest()
    TouchRippleProps       : dict
    color                  : 'inherit' | 'primary' | 'secondary' | 'success' | 'error' | 'info' | 'warning'
    disableElevation       : bool
    disableFocusRipple     : bool
    endIcon                : component
    fullWidth              : bool
    size                   : 'small' | 'medium' | 'large'
    startIcon              : component
    variant                : 'contained' | 'outlined' | 'text'

    href                   : "The URL to link to when the button is clicked. If defined, an a element will be used as the root node."
    centerRipple           : "If true, the ripples are centered. They won't start at the cursor interaction position." 
    disabled               : "If true, the component is disabled." 
    disableRipple          : "If true, the ripple effect is disabled.⚠️ Without a ripple there is no styling for :focus-visible by default. Be sure to highlight the element by applying separate styles with the .Mui-focusVisible class." 
    disableTouchRipple     : "If true, the touch ripple effect is disabled." 
    focusRipple            : "If true, the base button will have a keyboard focus ripple." 
    focusVisibleClassName  : "This prop can help identify which element has keyboard focus. The class name will be applied when the element gains the focus through keyboard interaction. It's a polyfill for the CSS :focus-visible selector. The rationale for using this feature is explained here. A polyfill can be used to apply a focus-visible class to other components if needed." 
    LinkComponent          : "The component used to render a link when the href prop is provided." 
    onFocusVisible         : "Callback fired when the component is focused with a keyboard. We trigger a onFocus callback too." 
    TouchRippleProps       : "Props applied to the TouchRipple element." 
    touchRippleRef         : "A ref that points to the TouchRipple element." 
    color                  : "The color of the component. It supports both default and custom theme colors, which can be added as shown in the palette customization guide." 
    disableElevation       : "If true, no elevation is used." 
    disableFocusRipple     : "If true, the  keyboard focus ripple is disabled." 
    endIcon                : "Element placed after the children."
    fullWidth              : "If true, the button will take up the full width of its container." 
    size                   : "The size of the component. small is equivalent to the dense button styling." 
    startIcon              : "Element placed before the children."
    variant                : "The variant to use."
    """
    componentName       = ComponentName ( "ContextfulMUIhRefButton" )
    href                = StringProp   ( default = None, allow_None = True, 
                                doc = "The URL to link to when the button is clicked. If defined, an a element will be used as the root node." ) 
