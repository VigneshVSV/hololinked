import logging
import textwrap
import typing
import ifaddr
from typing import Dict, Any, List
# from tabulate import tabulate
from tornado.httputil import HTTPServerRequest

from .constants import CALLABLE, ATTRIBUTE, EVENT, FILE, IMAGE_STREAM
from .data_classes import FileServerData
from .zmq_message_brokers import AsyncZMQClient, SyncZMQClient


def update_resources(resources : Dict[str, Dict[str, Dict[str, Any]]], add : Dict[str, Dict[str, Any]]) -> None:
    file_server_routes = dict(
        STATIC_ROUTES = dict(),
        DYNAMIC_ROUTES = dict()
    )
    for http_method, existing_map in resources.items():
        if http_method == 'FILE_SERVER':
            continue
        for URL_path, info in add[http_method].items():
            if isinstance(info, HTTPServerEventData):
                existing_map["STATIC_ROUTES"][URL_path] = info
            elif isinstance(info, HTTPServerResourceData):
                info.compile_path()
                if info.path_regex is None:
                    existing_map["STATIC_ROUTES"][info.path_format] = info
                else:
                    existing_map["DYNAMIC_ROUTES"][info.path_format] = info
            elif info["what"] == ATTRIBUTE or info["what"] == CALLABLE:
                data = HTTPServerResourceData(**info)
                data.compile_path()
                if data.path_regex is None:
                    existing_map["STATIC_ROUTES"][data.path_format] = data
                else:
                    existing_map["DYNAMIC_ROUTES"][data.path_format] = data
            elif info["what"] == EVENT:
                existing_map["STATIC_ROUTES"][URL_path] = HTTPServerEventData(**info)
            elif info["what"] == IMAGE_STREAM:
                existing_map["STATIC_ROUTES"][URL_path] = HTTPServerEventData(**info)
            elif info["what"] == FILE:
                data = FileServerData(**info)
                data.compile_path()
                if data.path_regex is None:
                    file_server_routes["STATIC_ROUTES"][data.path_format] = data
                else:
                    file_server_routes["DYNAMIC_ROUTES"][data.path_format] = data
    resources["FILE_SERVER"]["STATIC_ROUTES"].update(file_server_routes["STATIC_ROUTES"])
    resources["FILE_SERVER"]["STATIC_ROUTES"].update(file_server_routes["DYNAMIC_ROUTES"])



async def update_resources_using_client(resources : Dict[str, Dict[str, Any]], remote_object_info : List, 
                                client : typing.Union[AsyncZMQClient, SyncZMQClient]) -> None:
    from .remote_object import RemoteObjectDB
    _, _, _, _, _, reply = await client.async_execute('/resources/http', raise_client_side_exception = True)
    update_resources(resources, reply["returnValue"]) # type: ignore
    _, _, _, _, _, reply = await client.read_attribute('/object-info', raise_client_side_exception = True)
    remote_object_info.append(RemoteObjectDB.RemoteObjectInfo(**reply["returnValue"]))


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
    

resources_table_headers = ["URL", "method"]
def log_resources(logger : logging.Logger, resources : Dict[str, Dict[str, Any]] ) -> None:
    if logger.level == logging.DEBUG:
        # check log level manually before cooking this long string        
        text = """
            GET resources : 
            {}            
            POST resources :
            {}                 
            PUT resources :
            {}
            """.format(
                    tabulate([[key] + [values[1]] for key, values in resources["GET"].items()] , headers=resources_table_headers, tablefmt="presto"),
                    tabulate([[key] + [values[1]] for key, values in resources["POST"].items()], headers=resources_table_headers, tablefmt="presto"),
                    tabulate([[key] + [values[1]] for key, values in resources["PUT"].items()] , headers=resources_table_headers, tablefmt="presto")
                )
        logger.debug(textwrap.dedent(text).lstrip())


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
            

__all__ = ['log_request', 'log_resources']