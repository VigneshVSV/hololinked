from ...param.parameters import String
from ..basecomponents import RGLBaseComponent
from ..baseprops import ObjectProp, ComponentName
from ..axios import AxiosRequestConfig
from ..valuestub import ValueStub

class PlotlyFigure(RGLBaseComponent):
    plot = String ( doc = """Enter here the plot configuration as entered in plotly python. Tip : create a python
                plotly figure, extract JSON and assign it to this prop for verification. This prop is not verified 
                except that it is valid JSON specification. All errors appear at frontend.""")
    
    sources = ObjectProp ( item_type = (AxiosRequestConfig, ValueStub) )
    componentName = ComponentName ( "ContextfulPlotlyGraph" )
