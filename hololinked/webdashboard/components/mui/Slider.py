from ...basecomponents import MUIBaseComponent, ReactBaseComponent
from ...baseprops import ComponentName, StringProp, SelectorProp, BooleanProp, NodeProp, NumberProp, ObjectProp, TypedDict
from ...axios import RequestProp



class Slider(MUIBaseComponent):
    """
    aria-label         : str
    aria-labelledby    : str
    aria-valuetext     : str
    componentsProps    : { input?: object, mark?: object, markLabel?: object, rail?: object, root?: object, thumb?: object, track?: object, valueLabel?: { className?: string, components?: { Root?: elementType }, style?: object, value?: Array<number> | number, valueLabelDisplay?: 'auto' | 'off' | 'on' } }
    defaultValue       : TypeConstrainedList | float
    disabled           : bool
    disableSwap        : bool
    getAriaLabel       : AxiosHttp | makeRequest()
    getAriaValueText   : AxiosHttp | makeRequest()
    isRtl              : bool
    marks              : TypeConstrainedList | bool
    max                : float
    min                : float
    name               : str
    onChange           : AxiosHttp | makeRequest()
    onChangeCommitted  : AxiosHttp | makeRequest()
    orientation        : 'horizontal' | 'vertical'
    scale              : AxiosHttp | makeRequest()
    step               : float
    tabIndex           : float
    track              : 'inverted' | 'normal' | false
    value              : TypeConstrainedList | float
    valueLabelDisplay  : 'auto' | 'off' | 'on'
    valueLabelFormat   : MethodsType | str
    componentName      : read-only

    aria-label         :  "The label of the slider."
    aria-labelledby    :  "The id of the element containing a label for the slider."
    aria-valuetext     :  "A string value that provides a user-friendly name for the current value of the slider."
    componentsProps    :  "The props used for each slot inside the Slider."
    defaultValue       :  "The default value. Use when the component is not controlled."
    disabled           :  "If true, the component is disabled." 
    disableSwap        :  "If true, the active thumb doesn't swap when moving pointer over a thumb while dragging another thumb." 
    getAriaLabel       :  "Accepts a function which returns a string value that provides a user-friendly name for the thumb labels of the slider. This is important for screen reader users.Signature:function(index: number) => stringindex: The thumb label's index to format." 
    getAriaValueText   :  "Accepts a function which returns a string value that provides a user-friendly name for the current value of the slider. This is important for screen reader users.Signature:function(value: number, index: number) => stringvalue: The thumb label's value to format.index: The thumb label's index to format." 
    isRtl              :  "Indicates whether the theme context has rtl direction. It is set automatically."
    marks              :  "Marks indicate predetermined values to which the user can move the slider. If true the marks are spaced according the value of the step prop. If an array, it should contain objects with value and an optional label keys." 
    max                :  "The maximum allowed value of the slider. Should not be equal to min."
    min                :  "The minimum allowed value of the slider. Should not be equal to max."
    name               :  "Name attribute of the hidden input element." 
    onChange           :  "Callback function that is fired when the slider's value changed.Signature:function(event: Event, value: number | Array<number>, activeThumb: number) => voidevent: The event source of the callback. You can pull out the new value by accessing event.target.value (any). Warning: This is a generic event not a change event.value: The new value.activeThumb: Index of the currently moved thumb." 
    onChangeCommitted  :  "Callback function that is fired when the mouseup is triggered.Signature:function(event: React.SyntheticEvent | Event, value: number | Array<number>) => voidevent: The event source of the callback. Warning: This is a generic event not a change event.value: The new value." 
    orientation        :  "The component orientation."
    scale              :  "A transformation function, to change the scale of the slider."
    step               :  "The granularity with which the slider can step through values. (A "discrete" slider.) The min prop serves as the origin for the valid values. We recommend (max - min) to be evenly divisible by the step.When step is null, the thumb can only be slid onto marks provided with the marks prop." 
    tabIndex           :  "Tab index attribute of the hidden input element." 
    track              :  "The track presentation:- normal the track will render a bar representing the slider value. - inverted the track will render a bar representing the remaining slider value. - false the track will render without a bar." 
    value              :  "The value of the slider. For ranged sliders, provide an array with two values."
    valueLabelDisplay  :  "Controls when the value label is displayed:- auto the value label will display when the thumb is hovered or focused. - on will display persistently. - off will never display." 
    valueLabelFormat   :  "The format function the value label's value.When a function is provided, it should have the following signature:- {number} value The value label's value to format - {number} index The value label's index to format" 
    componentName      :  "Constant internal value for mapping classes to components in front-end"
    """
    ariaLabel          = StringProp    ( default = None, allow_None = True,
                                        doc = "The label of the slider." )
    ariaLabelledBy     = StringProp    ( default = None, allow_None = True,
                                        doc = "The id of the element containing a label for the slider." )
    ariaValueText      = StringProp    ( default = None, allow_None = True,
                                        doc = "A string value that provides a user-friendly name for the current value of the slider." )
    color              = SelectorProp  ( objects = [ 'primary', 'secondary'], default = 'primary', allow_None = False,
                                        doc = "The color of the component. It supports both default and custom theme colors, which can be added as shown in the palette customization guide." ) 
    componentsProps    = ObjectProp    ( default = {}, 
                                        doc = "The props used for each slot inside the Slider." )
    defaultValue       = SelectorProp  ( class_ = (list, float), default = None, allow_None = True,
                                        doc = "The default value. Use when the component is not controlled." )
    disabled           = BooleanProp   ( default = False, 
                                        doc = "If true, the component is disabled." ) 
    disableSwap        = BooleanProp   ( default = False,
                                        doc = "If true, the active thumb doesn't swap when moving pointer over a thumb while dragging another thumb." ) 
    getAriaLabel       = NodeProp      ( class_ = ReactBaseComponent, default = None, allow_None = True,
                                        doc = "Accepts a function which returns a string value that provides a user-friendly name for the thumb labels of the slider. This is important for screen reader users.Signature:function(index: number) => stringindex: The thumb label's index to format." ) 
    getAriaValueText   = NodeProp      ( class_ = ReactBaseComponent, default = None, allow_None = True,
                                        doc = "Accepts a function which returns a string value that provides a user-friendly name for the current value of the slider. This is important for screen reader users.Signature:function(value: number, index: number) => stringvalue: The thumb label's value to format.index: The thumb label's index to format." ) 
    isRtl              = BooleanProp   ( default = False, 
                                        doc = "Indicates whether the theme context has rtl direction. It is set automatically." )
    marks              = SelectorProp  ( class_ = (list, bool), default = False,
                                        doc = "Marks indicate predetermined values to which the user can move the slider. If true the marks are spaced according the value of the step prop. If an array, it should contain objects with value and an optional label keys." ) 
    max                = NumberProp    ( default = 100,
                                        doc = "The maximum allowed value of the slider. Should not be equal to min." )
    min                = NumberProp    ( default = 0,
                                        doc = "The minimum allowed value of the slider. Should not be equal to max." )
    name               = StringProp    ( default = None, allow_None = True,
                                        doc = "Name attribute of the hidden input element." ) 
    onChange           = RequestProp   ( default = None, 
                                        doc = "Callback function that is fired when the slider's value changed.Signature:function(event: Event, value: number | Array<number>, activeThumb: number) => voidevent: The event source of the callback. You can pull out the new value by accessing event.target.value (any). Warning: This is a generic event not a change event.value: The new value.activeThumb: Index of the currently moved thumb." ) 
    onChangeCommitted  = RequestProp   ( default = None, 
                                        doc = "Callback function that is fired when the mouseup is triggered.Signature:function(event: React.SyntheticEvent | Event, value: number | Array<number>) => voidevent: The event source of the callback. Warning: This is a generic event not a change event.value: The new value." ) 
    orientation        = SelectorProp  ( objects = ['horizontal', 'vertical'], default = 'horizontal', 
                                        doc = "The component orientation." )
    scale              = RequestProp   ( default = None, 
                                        doc = "A transformation function, to change the scale of the slider." )
    size               = SelectorProp  ( objects = ['small', 'medium'], default = 'medium',
                                        doc = "The size of the slider." )
    slots              = TypedDict     ( default = {}, allow_None = False, key_type = str, item_type = (str, ReactBaseComponent), 
                                        doc = "The components used for each slot inside the Slider. Either a string to use a HTML element or a component" )
    slotProps          = ObjectProp    ( default = {}, allow_None = False, 
                                        doc = "The props used for each slot inside the Slider.")
    step               = NumberProp    ( default = 1, allow_None = False,
                                        doc = "The granularity with which the slider can step through values. (A discrete slider.) The min prop serves as the origin for the valid values. We recommend (max - min) to be evenly divisible by the step.When step is null, the thumb can only be slid onto marks provided with the marks prop." ) 
    tabIndex           = NumberProp    ( default = None, allow_None = True,
                                        doc = "Tab index attribute of the hidden input element." ) 
    track              = SelectorProp  ( objects = ['inverted', 'normal', False], default = 'normal',
                                        doc = "The track presentation:- normal the track will render a bar representing the slider value. - inverted the track will render a bar representing the remaining slider value. - false the track will render without a bar." ) 
    value              = SelectorProp  ( class_ = (list, float), default = None, allow_None = True,
                                        doc = "The value of the slider. For ranged sliders, provide an array with two values." )
    valueLabelDisplay  = SelectorProp  ( objects = [ 'auto', 'off', 'on'], default = 'off', 
                                        doc = "Controls when the value label is displayed:- auto the value label will display when the thumb is hovered or focused. - on will display persistently. - off will never display." ) 
    valueLabelFormat   = RequestProp   ( default = None, 
                                        doc = "The format function the value label's value.When a function is provided, it should have the following signature:- {number} value The value label's value to format - {number} index The value label's index to format" ) 
    componentName      = ComponentName ( default = "MuiSlider",
                                        doc = "Constant internal value for mapping classes to components in front-end" )
