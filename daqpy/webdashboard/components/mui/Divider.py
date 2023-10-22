from ...basecomponents import MUIBaseComponent
from ...baseprops import BooleanProp, SelectorProp, ComponentName


class Divider(MUIBaseComponent):
    absolute = BooleanProp(default=False, doc="Absolutely position the element" )
    flexItem = BooleanProp(default=False, 
                doc="""If true, a vertical divider will have the correct height when used in flex container. 
                By default, a vertical divider will have a calculated height of 0px if it is the child of a flex container.""")
    light    = BooleanProp(default=False, doc="If true, the divider will have a lighter color")
    orientation = SelectorProp(default='horizontal', objects=['horizontal', 'vertical'],
                    doc="The component orientation.")
    textAlign   = SelectorProp(default='center', objects=['center', 'left', 'right'],
                    doc="The text alignment.")
    variant     = SelectorProp(default='fullWidth', objects=['fullWidth', 'inset', 'middle'],
                    doc="The variant to use. other strings not supported unlike stateed in MUI docs.")
    componentName = ComponentName(default='ContextfulMUIDivider')
