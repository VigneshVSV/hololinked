from ..server.remote_object import RemoteObject

"""
Copyright © 2017-2023 World Wide Web Consortium. W3C® liability, trademark and permissive document 
license rules apply.    
"""


class Thing(RemoteObject):
    """
    An abstraction of a physical or a virtual entity whose metadata and interfaces are described by a 
    WoT Thing Description. To access the thing description, go to

    http(s)://{server name}/{instance name}/wot-td
    """


__all__ = [
    Thing.__name__
]