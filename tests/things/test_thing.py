from hololinked.server import Thing, action


class TestThing(Thing):

    @action()
    def get_protocols(self):
        protocols = []
        if self.rpc_server.inproc_server is not None and self.rpc_server.inproc_server.socket_address.startswith('inproc://'):
            protocols.append('INPROC')
        if self.rpc_server.ipc_server is not None and self.rpc_server.ipc_server.socket_address.startswith('ipc://'): 
            protocols.append('IPC')
        if self.rpc_server.tcp_server is not None and self.rpc_server.tcp_server.socket_address.startswith('tcp://'): 
            protocols.append('TCP')
        return protocols

    @action()
    def test_echo(self, value):
        return value