from ..basecomponents import RGLBaseComponent
from ..baseprops import (StringProp, SelectorProp, IntegerProp, BooleanProp, 
                        StubProp, NumberProp, ObjectProp, TypedList, ComponentName,
                        UnsupportedProp)
from ..axios import RequestProp
from ..actions import ComponentOutputProp
from ..valuestub import StringStub


class AceEditor(RGLBaseComponent):
    """
    For docs on each prop refer - https://github.com/securingsincity/react-ace/blob/master/docs/Ace.md
    """
    placeholder         = StringProp(default="", doc="Placeholder text to be displayed when editor is empty")
    mode                = SelectorProp(objects=["javascript", "java", "python", "xml", "ruby", "sass", 
                                        "markdown", "mysql", "json", "html", "handlebars", "golang", 
                                        "csharp", "coffee", "css"], 
                                    default='json', doc="Language for parsing and code highlighting")
    theme               = SelectorProp(objects=["monokai", "github", "tomorrow", "kuroir", "twilight", "crimson_editor",
                                        "xcode", "textmate", "solarized dark", "solarized light", "terminal"], 
                                    default="crimson_editor", doc="Language for parsing and code highlighting")
    value               = StubProp(default=None)
    defaultValue        = StringProp(default="", doc="Default value of the editor")
    height              = StringProp(default="", doc="CSS value for height") 
    width               = StringProp(default="", doc="CSS value for width")
    # className           = StringProp(default="", doc="custom className")
    fontSize            = IntegerProp(default=12, doc="pixel value for font-size", bounds=(1, None))
    showGutter          = BooleanProp(default=True, doc="show gutter")
    showPrintMargin     = BooleanProp(default=True, doc="show print margin")
    highlightActiveLine = BooleanProp(default=True, doc="highlight active line")
    focus               = BooleanProp(default=False, doc="whether to focus")
    cursorStart         = IntegerProp(default=1, doc="the location of the cursor", bounds=(1, None))
    wrapEnabled         = BooleanProp(default=False, doc="Wrapping lines")
    readOnly            = BooleanProp(default=False, doc="make the editor read only")
    minLines            = IntegerProp(default=12, doc="Minimum number of lines to be displayed", bounds=(1, None))
    maxLines            = IntegerProp(default=12, doc="Maximum number of lines to be displayed", bounds=(1, None))
    enableBasicAutocompletion = BooleanProp(default=False, doc="Enable basic autocompletion")
    enableLiveAutocompletion  = BooleanProp(default=False, doc="Enable live autocompletion")
    enableSnippets      = BooleanProp(default=False, doc="Enable snippets")
    tabSize             = IntegerProp(default=4, doc="tabSize", bounds=(1, None))
    debounceChangePeriod= NumberProp(default=None, allow_None=True, doc="A debounce delay period for the onChange event", 
                                        bounds=(0, None))
    onLoad              = RequestProp(doc="called on editor load. The first argument is the instance of the editor")
    onBeforeLoad        = RequestProp(doc="called before editor load. the first argument is an instance of ace")
    onChange            = ComponentOutputProp()
    # These props are generally client side
    onCopy              = UnsupportedProp()
    onPaste             = UnsupportedProp()
    onSelectionChange   = UnsupportedProp()
    onCursorChange      = UnsupportedProp()
    onFocus	            = UnsupportedProp()
    onBlur              = UnsupportedProp()
    onInput             = UnsupportedProp()
    onScroll            = UnsupportedProp()
    onValidate          = UnsupportedProp()
    editorProps         = ObjectProp(doc="properties to apply directly to the Ace editor instance")
    setOptions          = ObjectProp(doc="options to apply directly to the Ace editor instance")
    keyboardHandler     = StringProp(doc="corresponding to the keybinding mode to set (such as vim or emacs)", default="")
    commands            = TypedList(doc="""
                                    new commands to add to the editor
                                    """)
    annotations         = TypedList(doc="""
                                    annotations to show in the editor i.e. [{ row: 0, column: 2, type: 'error', text: 'Some error.'}], displayed in the gutter
                                    """)
    markers             = TypedList(doc="""
                                    markers to show in the editor, 
                                    i.e. [{ startRow: 0, startCol: 2, endRow: 1, endCol: 20, className: 'error-marker', type: 'background' }]. 
                                    Make sure to define the class (eg. ".error-marker") and set position: absolute for it.
                                    """)
    style               = ObjectProp(doc="camelCased properties")
    componentName       = ComponentName(default="ContextfulAceEditor")

    def __init__(self, **params):
        self.editorProps = {}
        self.setOptions = {}
        self.style = {}
        self.value = StringStub()
        super().__init__(**params)

 

__all__ = ["AceEditor"]