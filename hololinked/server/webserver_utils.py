import logging
import textwrap
import traceback
import typing
import ifaddr
from tornado.httputil import HTTPServerRequest



def log_request(request : HTTPServerRequest, logger : typing.Optional[logging.Logger] = None) -> None:
    if logger and logger.level == logging.DEBUG: # 
        # check log level manually before cooking this long string        
        text = """
            REQUEST:
            path            : {},
            host            : {},
            host-name       : {},
            remote ip       : {},
            method          : {},  
            body type       : {}, 
            body            : {}, 
            arguments       : {},
            query arguments : {},
            body arguments  : {},    
            header          : {}"
            """.format(request.path, request.host, request.host_name, 
                request.remote_ip, request.method, type(request.body), request.body, 
                request.arguments, request.query_arguments, request.body_arguments,
                request.headers
        )
        logger.debug(textwrap.dedent(text).lstrip())
    else: 
        text = """
            REQUEST:
            path            : {},
            host            : {},
            host-name       : {},
            remote ip       : {},
            method          : {},  
            body type       : {}, 
            body            : {}, 
            arguments       : {},
            query arguments : {},
            body arguments  : {},    
            header          : {}"
            """.format(request.path, request.host, request.host_name, 
                request.remote_ip, request.method, type(request.body), request.body, 
                request.arguments, request.query_arguments, request.body_arguments,
                request.headers
        )
        print(textwrap.dedent(text).lstrip())
    

def get_IP_from_interface(interface_name : str = 'Ethernet', adapter_name = None):
    adapters = ifaddr.get_adapters(include_unconfigured=True)
    for adapter in adapters:
        if not adapter_name:
            for ip in adapter.ips:
                if interface_name == ip.nice_name:
                    if ip.is_IPv4:
                        return ip.ip
        elif adapter_name == adapter.nice_name:
            for ip in adapter.ips:
                if interface_name == ip.nice_name:
                    if ip.is_IPv4:
                        return ip.ip
            raise ValueError("interface name {} not found in system interfaces.".format(interface_name))
    raise ValueError("interface name {} not found in system interfaces.".format(interface_name))
            

def format_exception_as_json(exc : Exception) -> typing.Dict[str, typing.Any]: 
    return {
        "exception" : {
            "message" : str(exc),
            "type"    : repr(exc).split('(', 1)[0],
            "traceback" : traceback.format_exc().splitlines(),
            "notes"   : E.__notes__ if hasattr(exc, "__notes__") else None # type: ignore
        }
    }


__all__ = ['log_request', 'format_exception_as_json']