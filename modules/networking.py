import socket
import threading

import modules.servercmds

class Server:
    def __init__(self, port_):
        class serverdata:
            host = ''
            port = port_
        self.serverdata = serverdata
        
        self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connection.bind((self.serverdata.host, self.serverdata.port))
        self.connection.listen(5)
        threading.Thread(target = self.acceptance_thread, name = 'Acceptance thread', daemon = True).start()
        
        self.cmdline = modules.servercmds.ServerCommandLineUI(self.handle_command)
        
    def acceptance_thread(self):
        while True:
            print('ready')
            conn, addr = self.connection.accept()
            print(addr)
            threading.Thread(target = self.connection_handler, args = [addr, conn], daemon = True).start()
    
    def connection_handler(self, address, connection):
        print(address)
        while True:
            data = connection.recv(2048)
            print(data.decode('UTF-8'))
    
    def handle_command(self, command, source = 'internal'):
        if command == '' or command.startswith(' '):
            command = 'help'
        splitcommand = command.split(' ')
        name = splitcommand[0]
        argstring = ''
        for arg in splitcommand[1:]:
            argstring += '{} '.format(arg)
        argstring = argstring[:len(argstring) - 1]
        
        output = ''
        if name == 'help':
            output = '''Commands:
map: load a map by name
sv_conns: list of connections to the server'''
        elif name == 'map':
            if source == 'internal':
                try:
                    self.load_map(argstring)
                    output = 'Loading map \'{}\'...'.format(argstring)
                except ValueError:
                    output = 'Map \'{}\' not found'.format(argstring)
            else:
                output = 'No permissions'
        else:
            output = 'Command not found, try \'help\''
        return output
    
    def load_map(self, mapname):
        pass

class Client:
    def __init__(self, host_, port_):
        class serverdata:
            host = host_
            port = port_
        self.serverdata = serverdata
        
        self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print('xd')
        self.connection.connect((self.serverdata.host, self.serverdata.port))
        print('2')
    
    def send_raw(self, text):
        self.connection.send(text.encode())


class Request:
    def __init__(self):
        self._clear_all_values()
    
    def as_json(self):
        return json.dumps(self.as_dict())
    
    def as_dict(self):
        pass
        
    def json_in(self, data):
        self.dict_in(json.loads(data))
   
    def dict_in(self, data):
        self._clear_all_values()
        
        self.request_id = data['request id']
        if 'response id' in data:
            self.response_id = data['response id']
        self.data = data['data']
        
    def _clear_all_values(self):
        self.request_id = None
        self.response_id = None
        self.data = None