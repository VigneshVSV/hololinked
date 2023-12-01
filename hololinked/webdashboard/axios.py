from typing import Union
from collections import namedtuple

from ..param.parameters import TypedList, ClassSelector, TypedDict
from .baseprops import StringProp, SelectorProp, IntegerProp, BooleanProp, ObjectProp, StubProp, ComponentName
from .valuestub import ObjectStub
from .actions import BaseAction, Cancel
from .utils import unique_id



interceptor = namedtuple('interceptor', 'request response')

class InterceptorContainer:

    def use(self, callable : BaseAction) -> None:
        self.callable = callable 



class AxiosRequestConfig(BaseAction):
    """
    url              : str
    method           : ['GET', 'POST', 'PUT']
    baseurl          : str 
    headers          : dict
    params           : dict 
    data             : dict 
    timeout          : int > 0
    withCredentials  : bool
    auth             : dict
    responseType     : ['arraybuffer', 'document', 'json', 'text', 'stream', 'blob']
    xsrfCookieName   : str
    xsrfHeaderName   : str
    maxContentLength : int
    maxBodyLength    : int
    maxRedirects     : int
    """   
    actionType           = ComponentName ( default = "SingleHTTPRequest") 
    url                  = StringProp   ( default = None,  allow_None = True, 
                                        doc = """URL to make request. Enter full URL or just the path without the server. 
                                        Server can also be specified in baseURL. Please dont specify server in both URL and baseURL""" )
    method               = SelectorProp ( objects = ['get', 'post', 'put', 'delete', 'options'], default = 'post',
                                        doc = "HTTP method of the request" )
    baseurl              = StringProp   ( default = None,  allow_None = True, 
                                        doc = "Server or path to prepend to url" )
    # headers              = DictProp     ( default = {'X-Requested-With': 'XMLAxiosRequestConfigRequest'}, key_type = str, allow_None = True )
    # params               = DictProp     ( default = None,    allow_None = True )
    data                 = ObjectProp  ( default = None, allow_None = True )
    timeout              = IntegerProp  ( default = 0,  bounds = (0,None), allow_None = False )
    # withCredentials      = BooleanProp  ( default = False, allow_None = False  )
    # # auth                 = DictProp     ( default = None,    allow_None = True )
    # responseType         = SelectorProp ( objects = ['arraybuffer', 'document', 'json', 'text', 'stream', 'blob'], 
    #                                       default = 'json', allow_None = True )
    # xsrfCookieName       = StringProp   ( default = 'XSRF-TOKEN'  , allow_None = True )
    # xsrfHeaderName       = StringProp   ( default = 'X-XSRF-TOKEN', allow_None = True )
    # maxContentLength     = IntegerProp  ( default = 2000, bounds     = (0,None), allow_None = False )
    # maxBodyLength        = IntegerProp  ( default = 2000, bounds     = (0,None), allow_None = False )
    # maxRedirects         = IntegerProp  ( default = 21,   bounds     = (0,None), allow_None = False )
    # repr                 = StringProp   ( default = "Axios Request Configuration", readonly = True, allow_None = False )
    # intervalAfterTimeout = BooleanProp  ( default = False, allow_None = False )
    response            = StubProp        ( doc = """response value of the request (symbolic JSON specification based pointer - the actual value is in the browser).
                                           Index it to access specific fields within the response.""" )
    onStatus            = TypedDict       ( default = None, allow_None = True, key_type = int, item_type = BaseAction ) 
    interceptor         = ClassSelector   (class_=namedtuple, allow_None=True, constant=True, default=None )


    def request_json(self):
        return {
            'url' : self.url, 
            'method' : self.method, 
            'baseurl' : self.baseurl,
            'data' : self.data 
        }

    def json(self):
        return dict(**super().json(), config=self.request_json())
     
    def __init__(self, **kwargs) -> None:
        super().__init__()
        self.response = ObjectStub(self.id)
        # self.interceptor = interceptor(
        #     request =  InterceptorContainer(), 
        #     response = InterceptorContainer()
        # )
        for key, value in kwargs.items():
            setattr(self, key, value)

    def cancel(self):
        return Cancel(self.id)


def makeRequest(**params) -> AxiosRequestConfig:
    """
    url              : str
    method           : ['GET', 'POST', 'PUT']
    baseurl          : str 
    headers          : dict
    params           : dict 
    data             : dict 
    timeout          : int > 0
    withCredentials  : bool
    auth             : dict
    responseType     : ['arraybuffer', 'document', 'json', 'text', 'stream', 'blob']
    xsrfCookieName   : str
    xsrfHeaderName   : str
    maxContentLength : int
    maxBodyLength    : int
    maxRedirects     : int
    """
    return AxiosRequestConfig(**params)


class QueuedHTTPRequests(BaseAction):

    actionType = ComponentName(default="QueuedHTTPRequests") 
    requests = TypedList(default=None, allow_None=True, item_type=AxiosRequestConfig, 
                        doc="Request objects that will be fired one after the other, order within the list is respected.")
    ignoreFailedRequests = BooleanProp(default=True, 
                        doc="If False, if one request fails, remain requests are dropped. If true, failed requests are ignored.") 

    def json(self):
        return dict(**super().json(), requests=self.requests, ignoreFailedRequests=True)
    
    def __init__(self, *args : AxiosRequestConfig, ignore_failed_requests : bool = True) -> None:
        super().__init__()
        self.requests = list(args)
        self.ignoreFailedRequests = ignore_failed_requests

    def cancel(self) -> Cancel:
        return Cancel(self.id)


class ParallelHTTPRequests(BaseAction): 

    actionType = ComponentName(default="ParallelHTTPRequests") 
    requests = TypedList(default=None, allow_None=True, item_type=AxiosRequestConfig, 
                        doc="Request objects that will be fired one after the other. Order within the list is not important.")

    def json(self):
        return dict(**super().json(), requests=self.requests, ignoreFailedRequests=True)
    
    def __init__(self, *args : AxiosRequestConfig) -> None:
        super().__init__()
        self.requests = list(args)


def makeRequests(*args : AxiosRequestConfig, mode : str = 'serial', ignore_failed_requests : bool = True):
    if mode == 'serial':
        return QueuedHTTPRequests(*args, ignore_failed_requests=ignore_failed_requests)
    elif mode == 'parallel':
        return ParallelHTTPRequests(*args)
    else:
        raise ValueError("Only two modes are supported - serial or parallel. Given value : {}".format(mode))



class RepeatedRequests(BaseAction):

    actionType = ComponentName(default="RepeatedRequests")
    requests   = ClassSelector(class_=(AxiosRequestConfig, QueuedHTTPRequests, ParallelHTTPRequests), default = None, 
                                allow_None=True)
    interval   = IntegerProp(default=None, allow_None=True)

    def __init__(self, requests : Union[AxiosRequestConfig, QueuedHTTPRequests, ParallelHTTPRequests], interval : int = 60000) -> None:
        super().__init__()
        self.requests = requests
        # self.id = requests.id
        self.interval = interval

    def json(self):
        return dict(super().json(), requests=self.requests, interval=self.interval)
        

def repeatRequest(requests, interval = 60000):
    return (
        RepeatedRequests(
            requests, 
            interval = interval
        )
    )



class RequestProp(ClassSelector):

    def __init__(self, default = None, **params):
        super().__init__(class_=(AxiosRequestConfig, QueuedHTTPRequests, ParallelHTTPRequests, RepeatedRequests), default=default, 
                        deepcopy_default=False, allow_None=True, **params)


__all__ = ['makeRequest', 'AxiosRequestConfig', 'QueuedHTTPRequests', 'ParallelHTTPRequests', 'RepeatedRequests',
           'makeRequests', 'repeatRequest' ]