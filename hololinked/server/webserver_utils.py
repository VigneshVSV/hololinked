import traceback
import typing
import ifaddr


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
        "message" : str(exc),
        "type"    : repr(exc).split('(', 1)[0],
        "traceback" : traceback.format_exc().splitlines(),
        "notes"   : E.__notes__ if hasattr(exc, "__notes__") else None # type: ignore
    }


__all__ = ['get_IP_from_interface', 'format_exception_as_json']