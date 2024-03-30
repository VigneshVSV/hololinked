from .constants import USE_OBJECT_NAME, HTTP_METHODS
from .decorators import remote_method


def get(URL_path : str = USE_OBJECT_NAME):
    """
    use it on RemoteObject subclass methods to be available with GET HTTP request. 
    method is also by default accessible to proxy clients. 
    """
    return remote_method(URL_path=URL_path, http_method=HTTP_METHODS.GET)
    
def post(URL_path : str = USE_OBJECT_NAME):
    """
    use it on RemoteObject subclass methods to be available with POST HTTP request. 
    method is also by default accessible to proxy clients. 
    """
    return remote_method(URL_path=URL_path, http_method=HTTP_METHODS.POST)

def put(URL_path : str = USE_OBJECT_NAME):
    """
    use it on RemoteObject subclass methods to be available with PUT HTTP request. 
    method is also by default accessible to proxy clients. 
    """
    return remote_method(URL_path=URL_path, http_method=HTTP_METHODS.PUT)
    
def delete(URL_path : str = USE_OBJECT_NAME):
    """
    use it on RemoteObject subclass methods to be available with DELETE HTTP request. 
    method is also by default accessible to proxy clients. 
    """
    return remote_method(URL_path=URL_path, http_method=HTTP_METHODS.DELETE)

def patch(URL_path : str = USE_OBJECT_NAME):
    """
    use it on RemoteObject subclass methods to be available with PATCH HTTP request. 
    method is also by default accessible to proxy clients. 
    """
    return remote_method(URL_path=URL_path, http_method=HTTP_METHODS.PATCH)


__all__ = ['get', 'put', 'post', 'delete', 'patch', 'HTTP_METHODS']