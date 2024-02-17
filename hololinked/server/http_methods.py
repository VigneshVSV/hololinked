




from .constants import USE_OBJECT_NAME, GET, POST, PUT, DELETE, PATCH
from .decorators import remote_method


def get(URL_path = USE_OBJECT_NAME):
    """
    use it on RemoteObject subclass methods to be available with GET HTTP request. 
    method is also by default accessible to proxy clients. 
    """
    return remote_method(URL_path=URL_path, http_method=GET)
    
def post(URL_path = USE_OBJECT_NAME):
    """
    use it on RemoteObject subclass methods to be available with POST HTTP request. 
    method is also by default accessible to proxy clients. 
    """
    return remote_method(URL_path=URL_path, http_method=POST)

def put(URL_path = USE_OBJECT_NAME):
    """
    use it on RemoteObject subclass methods to be available with PUT HTTP request. 
    method is also by default accessible to proxy clients. 
    """
    return remote_method(URL_path=URL_path, http_method=PUT)
    
def delete(URL_path = USE_OBJECT_NAME):
    """
    use it on RemoteObject subclass methods to be available with DELETE HTTP request. 
    method is also by default accessible to proxy clients. 
    """
    return remote_method(URL_path=URL_path, http_method=DELETE)

def patch(URL_path = USE_OBJECT_NAME):
    """
    use it on RemoteObject subclass methods to be available with PATCH HTTP request. 
    method is also by default accessible to proxy clients. 
    """
    return remote_method(URL_path=URL_path, http_method=PATCH)


__all__ = ['get', 'put', 'post', 'delete', 'patch']