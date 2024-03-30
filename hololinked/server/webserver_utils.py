import traceback
import typing
import ifaddr


def get_IP_from_interface(interface_name : str = 'Ethernet', adapter_name = None) -> str:
    """
    Get IP address of specified interface. Generally necessary when connected to the network
    through multiple adapters and a server binds to only one adapter at a time. 

    Parameters
    ----------
    interface_name: str
        Ethernet, Wifi etc. 
    adapter_name: optional, str
        name of the adapter if available

    Returns
    -------
    str: 
        IP address of the interface
    """
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
    raise ValueError(f"interface name {interface_name} not found in system interfaces.")
            

def format_exception_as_json(exc : Exception) -> typing.Dict[str, typing.Any]: 
    """
    return exception as a JSON serializable dictionary
    """
    return {
        "message" : str(exc),
        "type" : repr(exc).split('(', 1)[0],
        "traceback" : traceback.format_exc().splitlines(),
        "notes" : exc.__notes__ if hasattr(exc, "__notes__") else None 
    }


__all__ = ['get_IP_from_interface', 'format_exception_as_json']