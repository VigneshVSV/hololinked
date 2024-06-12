import typing
from .constants import JSON

class JSONSchemaError(Exception):
    """
    common error to be raised for JSON schema
    validation irrespective of internal validation used
    """
    pass 

class JSONValidationError(Exception):
    """
    common error to be raised for JSON validation
    irrespective of internal validation used
    """
    pass



try: 
    import fastjsonschema 
    
    class FastJsonSchemaValidator:
        """
        JSON schema validator according to fast JSON schema.
        Useful for performance with dictionary based schema specification
        which msgspec has no built in support. Normally, for speed, 
        one should try to use msgspec's struct concept.
        """

        def __init__(self, schema : JSON):
            self.schema = schema
            self.validator = fastjsonschema.compile(schema)

        def validate(self, data):
            """validates and raises exception when failed directly to the caller"""
            try: 
                self.validator(data)
            except fastjsonschema.JsonSchemaException as ex: 
                raise JSONSchemaError(str(ex)) from None

        def json(self):
            """allows JSON (de-)serializable of the instance itself"""
            return self.schema

        def __get_state__(self):
            return self.schema
        
        def __set_state__(self, schema):
            return FastJsonSchemaValidator(schema)

except ImportError as ex:
    pass



import jsonschema

class JsonSchemaValidator:
    """
    JSON schema validator according to standard python JSON schema.
    Somewhat slow, consider msgspec if possible. 
    """
    
    def __init__(self, schema):
        self.schema = schema
        self.validator = jsonschema.Draft7Validator(schema)
        self.validator.check_schema(schema)

    def validate(self, data):
        self.validator.validate(data)

    def json(self):
        """allows JSON (de-)serializable of the instance itself"""
        return self.schema

    def __get_state__(self):
        return self.schema
    
    def __set_state__(self, schema):
        return JsonSchemaValidator(schema)
    


def _get_validator_from_user_options(option : typing.Optional[str] = None) -> typing.Union[JsonSchemaValidator, FastJsonSchemaValidator]:
    """
    returns a JSON schema validator based on user options
    """
    if option == "fastjsonschema":
        return FastJsonSchemaValidator
    elif option == "jsonschema" or not option:
        return JsonSchemaValidator
    else:
        raise ValueError(f"Unknown JSON schema validator option: {option}")