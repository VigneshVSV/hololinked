from ...basecomponents import MUIBaseComponent, ReactBaseComponent
from ...baseprops import TupleSelectorProp, NodeProp, NumberProp, BooleanProp, ComponentName



class Stack(MUIBaseComponent):
    direction = TupleSelectorProp(objects=['column-reverse', 'column', 'row-reverse', 'row'], default="column",
                            doc="Defines the flex-direction style property. It is applied for all screen sizes.",
                            accept_list=True)
    divider = NodeProp(class_=ReactBaseComponent, default=None, allow_None=True, 
                    doc="Add an element between each child.")
    spacing = NumberProp(bounds=(0, None),
                    doc="Defines the space between immediate children, accepts only number unlike stated in MUI docs")
    useFlexGap = BooleanProp(default=False,
                    doc="If true, the CSS flexbox gap is used instead of applying margin to children. not supported on all browsers.")
    componentName = ComponentName(default="ContextfulMUIStack")


class Box(MUIBaseComponent):
    componentName = ComponentName(default="ContextfulMUIBox")
  

    