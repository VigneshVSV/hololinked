from typing import Any


def getStringRepr(object : Any, NumOfChars : int = 200):
        if isinstance(object, str):
            if (len(object) > NumOfChars):
                return object[0:int(NumOfChars/2)]+ "..." + object[-int(NumOfChars/2):-1]
            return object 
        elif isinstance(object, (float, int, bool)):
            return object
        elif hasattr(object, '__iter__'):
            items = []
            limiter = ']'
            length = 0
            for item in object:
                string = str(item)
                length += len(string)
                if length < 200:
                    items.append(string)
                else:
                    limiter = ', ...]'
                    break
            items = '[' + ', '.join(items) + limiter
            return items
        else: 
            return object


def raise_PropError(Exc : Exception, pobj, prop : str) -> None:
    # We need to reduce the stack
    if hasattr(pobj, 'id') and pobj.id is not None:
        if hasattr(pobj, 'componentName'):
            message = "{}.{} with id '{}' - {}".format(pobj.componentName, prop,  pobj.id, str(Exc))
        elif hasattr(pobj, 'actionType'):
            message = "{}.{} with id '{}' - {}".format(pobj.actionType, prop,  pobj.id, str(Exc))
        else:
            message = "{} of object with id '{}' - {}".format(prop,  pobj.id, str(Exc))
    else:
        message = "{} - {}.".format(prop, str(Exc))
    # does not work for axios
    raise type(Exc)(message)


__all__ = ['raise_PropError', 'getStringRepr']