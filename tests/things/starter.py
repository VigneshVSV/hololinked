import typing, multiprocessing, threading, logging
from hololinked.server import ThingMeta


def run_thing(
    thing_cls : ThingMeta, 
    instance_name : str, 
    protocols : typing.List[str] = ['IPC'], 
    tcp_socket_address : str = None,
    done_queue : typing.Optional[multiprocessing.Queue] = None,
    log_level : int = logging.WARN,
    prerun_callback : typing.Optional[typing.Callable] = None
) -> None:
    if prerun_callback:
        prerun_callback(thing_cls)
    thing = thing_cls(instance_name=instance_name, log_level=log_level)
    thing.run(zmq_protocols=protocols, tcp_socket_address=tcp_socket_address)
    if done_queue is not None:
        done_queue.put(instance_name)


def start_thing_forked(
    thing_cls : ThingMeta, 
    instance_name : str, 
    protocols : typing.List[str] = ['IPC'], 
    tcp_socket_address : str = None,
    done_queue : typing.Optional[multiprocessing.Queue] = None,
    log_level : int = logging.WARN,
    prerun_callback : typing.Optional[typing.Callable] = None,
    as_process : bool = True
):
    if as_process:
        multiprocessing.Process(
                        target=run_thing,
                        kwargs=dict(
                            thing_cls=thing_cls,
                            instance_name=instance_name,
                            protocols=protocols,
                            tcp_socket_address=tcp_socket_address,
                            done_queue=done_queue,
                            log_level=log_level,
                            prerun_callback=prerun_callback
                        ), daemon=True
                    ).start()
    else:
        threading.Thread(
            target=run_thing,
            kwargs=dict(
                thing_cls=thing_cls,
                instance_name=instance_name,
                protocols=protocols,
                tcp_socket_address=tcp_socket_address,
                done_queue=done_queue,
                log_level=log_level,
                prerun_callback=prerun_callback
            ), daemon=True
        ).start()
    


    