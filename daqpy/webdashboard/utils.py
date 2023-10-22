from ..param.parameters import String
import uuid


def unique_id(prefix : str = 'htmlid_') -> str:
    return "{}{}".format(prefix if isinstance(prefix, str) else '', str(uuid.uuid4()))


class __UniqueValueContainer__:
    FooBar = String( default="ReadOnly", readonly = True, constant = True,
            doc = "This container might be useful in internal validations, please dont modify it outside the package.")
                    
U = __UniqueValueContainer__()