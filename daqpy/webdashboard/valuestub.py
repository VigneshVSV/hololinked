from dataclasses import dataclass, asdict, field
from typing import Any, Union, Dict, List
from collections.abc import MutableMapping


addop = "+" 
subop = "-"
mulop = "*"
divop = "/"
floordivop = "//"
modop = "%"
powop = "^"
gtop  = ">"
geop  = ">="
ltop  = "<"
leop  = "<="
eqop  = "=="
neop  = "!="

orop  = "or"
andop = "and"
xorop = "xor"
notop = "not"


RAW = "raw"
NESTED_ID = "nested_id"
ACTION = "action"
ACTION_RESULT = "result_of_action"
# The above are the interpretations of an operand
# RAW means op1 or op2 is JSON compatible value
# NESTED means op1 or op2 itself is yet another stub
# ACTION means the stub should be evaluated to become a method in the frontend
# ACTION RESULT means the op1 or op2 is retrived as a JSON compatible value after an action is performed


@dataclass
class abstract_stub:

    def json(self):
        return asdict(self)

@dataclass
class single_op_stub(abstract_stub):
    op1 : Any 
    op1interpretation : str 
    op1dtype : str = field(default = "unknown")

@dataclass
class two_ops_stub(abstract_stub):
    op1 : Any
    op1interpretation : str 
    op2 : Any 
    op2interpretation : Any
    op : str 
    op1dtype : str = field(default = "unknown")
    op2dtype : str = field(default = "unknown")

@dataclass
class dotprop_stub(abstract_stub):
    op1 : Any
    op1interpretation : str  
    op1prop  : str 
    op1dtype : str = field(default = "unknown")

@dataclass
class funcop_stub(abstract_stub): 
    op1 : Any 
    op1func : str 
    op1args : Any 
    op1interpretation : str 
    op1dtype : str = field(default = "unknown")

@dataclass
class json_stub(abstract_stub):
    op1 : str
    op1interpretation : str  
    fields : Union[str, None] 
    op1dtype : str = field(default = "unknown")


@dataclass 
class action_stub(abstract_stub):
    op1 : str 
    op1interpretation : str 
    op1dtype : str = field(default = "unknown")


stub_type = Union[two_ops_stub, single_op_stub, funcop_stub, dotprop_stub, json_stub]


class ValueStub:
    """
    A container class to store information about operations to be performed directly at the frontend without making 
    a request to the backend. The goal is to generate a JSON of the following form to be used at the frontend -
    {
        'op1' - first operand, 
        'op1type' - the javasript type of the value stored by the first operand. For ex - a textfield component stores string 
        'op1interpretaion' - interpretation of first operand, four are possible now - RAW, NESTED, ACTION & ACTION_RESULT
        'op2' - second operand, 
        'op2type' - the type of the value stored by the second operand.
        'op2interpretation' - interpretation of second operand
        'op'  - the operation required to be performed 
    }.

    This JSON is also composed inside this class as an instance of ValueStub 

    Attributes:
        op1 - the id of the ReactBaseComponent which composes the ValueContainer, consequently it is the first operand 'op1'
        dtype - the javascript data type that the container is storing after instantiation 
        value - object which stores the final information on how to compute the value 
    
    A few varieties are possible :
    1) if stored as 
        {
            'op1' : some valid HTML ID
            'op1type' : some valid data type
        }
    it means there is no operation, and the value stored by the HTML component is the value of the component.

    2) if stored as 
        {
            'op1' : some valid HTML ID
            'op1type' : some valid data type
            'op2' : another valid HTML ID
            'op2type' : some valid data type
            'op' : some valid operation
        }
    this means there is some operation, and the final value is arrived by operating on the operands 

    3) Similar to above, it is possible to store function instructions 

    More importantly, some HTML components are input components (for ex - textfield) and yet others are output 
    components (for ex - typography). For input components, the first JSON is stored and for output component the second
    JSON or third type is stored so that some value can be computed and shown as display.  

    One can also assign these JSON to individual props when suitable,
    """
 
    dtype = 'unknown'
    acceptable_pydtypes = None 
    
    def __init__(self, action_result_id_or_stub : Union[str, stub_type, None] = None) -> None:
        self._uninitialized = True
        if action_result_id_or_stub is not None:
            self.create_base_info(action_result_id_or_stub)
    
    def json(self, return_as_dict : bool = False):
        return self._info
  
    def create_base_info(self, value: Any) -> None:
        if isinstance(value, str):
            self._info = single_op_stub(op1 = value, op1dtype = self.dtype, op1interpretation = ACTION_RESULT)
        elif isinstance(value, two_ops_stub):
            self._info = value
            self._info.op1dtype = self.dtype
            self._info.op2dtype = self.dtype 
        elif isinstance(value, abstract_stub):
            self._info = value
            self._info.op1dtype = self.dtype # type: ignore 
            # we assume abstract stub is never used, all other stubs have op1
        else:
            raise ValueError("ValueStub assignment failed. Given type : {}, expected any of stub types.".format(type(value)))
        self._uninitialized = False

    def compute_dependents(self, sub_info : Union[single_op_stub, two_ops_stub, None] = None):
        raise NotImplementedError("compute_dependents() not supported for {}".format(self.__class__))
    
    dependents = property(compute_dependents)

    def create_op_info(self, op2 : "ValueStub", op : str):
        raise NotImplementedError("create_func_info() not supported for {}".format(self.__class__))

    def create_func_info(self, func_name : str, args: Any):
        raise NotImplementedError("create_func_info() not supported for {}".format(self.__class__))

    def create_dot_property_info(self, prop_name : str):
        raise NotImplementedError("create_dot_property_info() not supported for {}".format(self.__class__))


class SupportsNumericalOperations(ValueStub):

    acceptable_pydtypes = ()
    # refer NumberStub for meaning of acceptable_pydtypes 

    def create_op_info(self, op2 : Union["ValueStub", float, int], op : str) -> two_ops_stub:
        """
        we already have op1, op2 requires to be set correctly for completing the op info.
        Generally we need to set op2 & op2intepretation, dtype will set at init while creating a new stub
        """
        if self._uninitialized:
            raise AttributeError("HTML id requires to be set before stub information (props that allow to access to directly manipulate at the frontend).")
        if isinstance(op2, self.acceptable_pydtypes):
            op2interpration = RAW
            # note : op2 = op2
        elif isinstance(op2, self.__class__):
            if op2._uninitialized:
                raise AttributeError("HTML id requires to be set before stub information (props that allow to access to directly manipulate at the frontend).")
            if isinstance(op2._info, single_op_stub):
                # Order of assignment is important for below
                op2interpration = op2._info.op1interpretation
                op2 = op2._info.op1
            else:
                op2interpration = NESTED_ID
                op2 = op2._info # type: ignore
        else:
            raise TypeError("cannot perform {} operation on {} and {} in ValueStub".format(op, self._info.op1, op2)) 

        if isinstance(self._info, single_op_stub):
            return two_ops_stub(
                op1 = self._info.op1,
                op1interpretation = self._info.op1interpretation,
                op2 = op2, 
                op2interpretation = op2interpration,
                op = op
            )     
        else:
            return two_ops_stub(
                op1 = self._info, 
                op1interpretation = NESTED_ID,
                op2 = op2, 
                op2interpretation = op2interpration,
                op = op
            )
        

class HasDotProperty(ValueStub):

    def create_dot_property_info(self, prop_name : str) -> dotprop_stub:
        if isinstance(self._info, single_op_stub):
            return dotprop_stub(
                op1 = self._info.op1,
                op1interpretation = self._info.op1interpretation,
                op1prop = prop_name
            ) 
        elif isinstance(self._info, abstract_stub): 
            return dotprop_stub(
                op1 = self._info, 
                op1interpretation = NESTED_ID,
                op1prop = prop_name, 
            ) 
        raise NotImplementedError("Internal error regarding stub information calculation. {} has {} stub which is unexpected.".format(
                    self.__class__, type(self._info)))


class SupportsMethods(ValueStub):

    def create_func_info(self, func_name : str, args : Any):
        if isinstance(self._info, single_op_stub):
            return funcop_stub(
                op1 = self._info.op1,
                op1interpretation = self._info.op1interpretation,
                op1args = args, 
                op1func = func_name     
            )
        elif isinstance(self._info, abstract_stub): 
            return funcop_stub(
                op1 = self._info,
                op1interpretation = NESTED_ID,
                op1args = args, 
                op1func = func_name  
            )
        raise NotImplementedError("Internal error regarding stub information calculation. {} has {} stub which is unexpected".format(
                        self.__class__, type(self._info)))

        


class NumberStub(SupportsNumericalOperations):
    
    dtype = "number"
    acceptable_pydtypes = (float, int)
   
    def __add__(self, value : ValueStub) -> "NumberStub":
        return NumberStub(self.create_op_info(value, addop))
    
    def __sub__(self, value : ValueStub) -> "NumberStub":
        return NumberStub(self.create_op_info(value, subop))

    def __mul__(self, value : ValueStub) -> "NumberStub":
        return NumberStub(self.create_op_info(value, mulop))

    def __floordiv__(self, value : ValueStub) -> "NumberStub":
        return NumberStub(self.create_op_info(value, floordivop))

    def __truediv__(self, value : ValueStub) -> "NumberStub":
        return NumberStub(self.create_op_info(value, divop))

    def __mod__(self, value : ValueStub) -> "NumberStub":
        return NumberStub(self.create_op_info(value, modop))

    def __pow__(self, value : ValueStub) -> "NumberStub":
        return NumberStub(self.create_op_info(value, powop))

    def __gt__(self, value : ValueStub) -> "BooleanStub":
        return BooleanStub(self.create_op_info(value, gtop))
  
    def __ge__(self, value : ValueStub) -> "BooleanStub":
        return BooleanStub(self.create_op_info(value, geop))
  
    def __lt__(self, value : ValueStub) -> "BooleanStub":
        return BooleanStub(self.create_op_info(value, ltop))
   
    def __le__(self, value : ValueStub) -> "BooleanStub":
        return BooleanStub(self.create_op_info(value, leop))

    def __eq__(self, value : ValueStub) -> "BooleanStub":
       return BooleanStub(self.create_op_info(value, eqop))
  
    def __ne__(self, value : ValueStub) -> "BooleanStub":
        return BooleanStub(self.create_op_info(value, neop))
  


class BooleanStub(SupportsNumericalOperations):

    dtype = "boolean"
    acceptable_pydtypes = bool   

    def __or__(self, value : ValueStub) -> "BooleanStub":
        return BooleanStub(self.create_op_info(value, orop))

    def __and__(self, value : ValueStub) -> "BooleanStub":
        return BooleanStub(self.create_op_info(value, andop))

    def __xor__(self, value : ValueStub) -> "BooleanStub":
        return BooleanStub(self.create_op_info(value, xorop))

    def __not__(self, value : ValueStub) -> "BooleanStub":
        return BooleanStub(self.create_op_info(value, notop))



class StringStub(SupportsNumericalOperations, HasDotProperty, SupportsMethods):

    dtype = "string"
    acceptable_pydtypes = str
         
    def length(self) -> NumberStub:
        return NumberStub(self.create_dot_property_info("length")) 

    def charAt(self):
        raise NotImplementedError("charAt is not yet implemented")

    def capitalize(self):
        raise NotImplementedError("capitalize is not yet implemented")

    def slice(self, start : int, end : Union[int, None] = None) -> "StringStub":
        if isinstance(start, int) and (isinstance(end, int) or end is None):
            return StringStub(self.create_func_info("slice", [start, end]))
        else:
            raise TypeError("start/end index not specified as integer : start - {}, end - {}".format(type(start), type(end)))

    def substring(self, start : int, end : int) -> "StringStub":
        if isinstance(start, int) and isinstance(end, int):
            return StringStub(self.create_func_info("substring", [start, end]))
        else:
            raise TypeError("start/end index not specified as integer : start - {}, end - {}".format(type(start), type(end)))

    def substr(self, start : int, length : Union[int, None] = None) -> "StringStub":
        if isinstance(start, int) and (isinstance(length, int) or length is None):
            return StringStub(self.create_func_info("substr", [start, length]))
        else:
            raise TypeError("start/length value not specified as integer : start - {}, end - {}".format(type(start), type(length)))

    def __add__(self, value : ValueStub): 
        return StringStub(self.create_op_info(value, addop))


class JSON(SupportsMethods):

    dtype = 'object'
    acceptable_pydtypes = (dict, MutableMapping)

    def create_base_info(self, value: Any) -> None:
        if isinstance(value , str):
            self._info = json_stub(op1 = value, fields = None, op1interpretation = ACTION_RESULT, op1dtype = self.dtype) # type: ignore
        elif isinstance(value, (json_stub, funcop_stub)):
            self._info = value 
            self._info.op1dtype = self.dtype
        else:
            raise ValueError("ValueStub assignment failed. Given type : {}, expected ".format(type(value)))

    @classmethod
    def stringify(cls, value : Any, space = None):
        if isinstance(value, (ObjectStub, JSON)):    
            _info = funcop_stub(
                op1 = value._info,
                op1func = 'stringify', 
                op1args = [None, space], 
                op1interpretation = value._info.op1interpretation # type: ignore
            )
        elif isinstance(value, cls.acceptable_pydtypes):
            _info = funcop_stub(
                op1 = value,
                op1func = 'stringify',
                op1args = [None, space],
                op1interpretation = RAW
            )   
        else:
            raise ValueError(f"Given value cannot be stringified. Only JSON or Dict is accepted, given type {type(value)}")
        return StringStub(_info)


class ObjectStub(ValueStub):

    # Differs from JSON stub in the sense that JSON stub supports the javascript methods
    # like stringify

    dtype = "object"

    def json(self):
        return self._info if hasattr(self, '_info') else None

    def create_base_info(self, value : Any):
        if isinstance(value, str):
            self._info = json_stub(op1 = value, fields = None, op1interpretation = ACTION_RESULT, op1dtype = self.dtype)
        elif isinstance(value, json_stub):
            self._info = value
            self._info.op1dtype = self.dtype
        else:
            raise ValueError("ValueStub assignment failed. Given type : {}, expected ".format(type(value)))
        
    def __getitem__(self, field : str):
        assert isinstance(field , str), "indexing a response object should be JSON compliant, give string field names. Given type {}".format(type(field))
        if not hasattr(self, '_info'):
            raise AttributeError("information container not yet created for ObjectStub object")
        if self._info.fields is None:
            fields = field
        else:
            fields = self._info.fields + "." + field
        return ObjectStub(json_stub(op1 = self._info.op1, fields = fields, op1interpretation = ACTION_RESULT))


class ActionStub(ValueStub):
    
    dtype = 'action'

    def create_base_info(self, value: Any) -> None:
        if isinstance(value, str):
            self._info = action_stub(op1 = value, op1interpretation = ACTION, op1dtype = self.dtype)
        else:
            raise ValueError("ValueStub assignment failed. Given type : {}, expected HTML-like id string.".format(type(value)))



def string_cast(value):
    return StringStub(
        single_op_stub(
            op1 = value, 
            op1interpretation = RAW
    ))