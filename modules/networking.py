import multiprocessing as mp
import socket
import threading
import json
import os
import sys
import random

import modules.servercmds

class Server:
    def __init__(self, port_):
        class serverdata:
            host = ''
            port = port_
            connections = []
            map = None
            mapdata = None
            conn_data = [] #individual spaces for connections to store data to be publically accessible
        self.serverdata = serverdata
        
        self.output_pipe, pipe = mp.Pipe()
        
        self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connection.bind((self.serverdata.host, self.serverdata.port))
        self.connection.listen(5)
        
        self.cmdline = modules.servercmds.ServerCommandLineUI(self.handle_command, pipe)
        
        with open(os.path.join(sys.path[0], 'server', 'config.json'), 'r') as file:
            self.settingsdata = json.load(file)
        for script in self.settingsdata['scripts']['autoexec']:
            with open(os.path.join(sys.path[0], 'server', 'scripts', '{}.txt'.format(script)), 'r') as file:
                text = file.read()
            self.output_pipe.send(self.run_script(text))
        
        threading.Thread(target = self.acceptance_thread, name = 'Acceptance thread', daemon = True).start()
        
    def acceptance_thread(self):
        conn_id = 0
        while True:
            self.output_pipe.send('Ready for incoming connections')
            
            conn, addr = self.connection.accept()
            threading.Thread(target = self.connection_handler, args = [addr, conn, conn_id], daemon = True).start()
            self.serverdata.connections.append([addr, conn])
            
            for script in self.settingsdata['scripts']['userconnect']:
                with open(os.path.join(sys.path[0], 'server', 'scripts', '{}.txt'.format(script)), 'r') as file:
                    text = file.read()
                self.output_pipe.send(self.run_script(text))
            
            conn_id += 1
    
    def connection_handler(self, address, connection, conn_id):
        self.output_pipe.send('New connection from {}'.format(address[0]))
        
        self.serverdata.conn_data.append({'model': random.choice(self.serverdata.mapdata['entity models']['player']),
                                              'connection': connection,
                                              'active': True,
                                              'address': address,
                                              'id': conn_id})
        
        cont = True
        while cont:
            try:
                data = connection.recv(2048)
                req = Request(json.loads(data.decode()))
            except ConnectionResetError or ConnectionAbortedError:
                req = Request(command = 'disconnect', arguments = {'clean': False}) #argument 'clean' shows whether or not a message was sent to close the connection or the conenction was forcibly closed
                cont = False
                
            if req.command == 'disconnect':
                self.output_pipe.send('User {} disconnected'.format(address[0]))
            elif req.command == 'var update r':
                if req.subcommand == 'map':
                    self.send(connection, Request(command = 'var update w', subcommand = 'map', arguments = {'map name': self.serverdata.map}))
                elif req.subcommand == 'player model':
                    if self.serverdata.map != None:
                        self.send(connection, Request(command = 'var update w', subcommand = 'player model', arguments = {'value': self.serverdata.conn_data[conn_id]['model']}))
        self.serverdata.conn_data[conn_id]['active'] = False
    
    def handle_command(self, command, source = 'internal'):
        if command == '' or command.startswith(' '):
            command = 'help'
        splitcommand = command.split(' ')
        name = splitcommand[0]
        argstring = ''
        for arg in splitcommand[1:]:
            argstring += '{} '.format(arg)
        argstring = argstring[:len(argstring) - 1]
        
        output = 'ERROR'
        if name == 'help':
            output = '''Commands:
map: load a map by name
say: send a message to all players
exec: exexute a script by name stored in the server/scripts directory
echo: output the text given to the console
clear: clear the console

sv_:
sv_conns: list of connections to the server
sv_kick_addr: kick a player by address
sv_quit: destroy the server'''
        elif name == 'map':
            if source == 'internal':
                try:
                    self.load_map(argstring)
                    output = 'Loading map \'{}\'...'.format(argstring)
                except ValueError:
                    output = 'Map \'{}\' not found'.format(argstring)
            else:
                output = 'No permissions'
        elif name == 'say':
            self.send_all(Request(command = 'say', arguments = {'text': argstring}))
            output = 'Said \'{}\''.format(argstring)
        elif name.startswith('sv_'):
            if name == 'sv_kick_addr':
                if source == 'internal':
                    try:
                        self.kick_address(argstring)
                        output = 'Kicked all connections through \'{}\''.format(argstring)
                    except ValueError:
                        output = 'Error while kicking \'{}\''.format(argstring)
                else:
                    output = 'No permissions'
            elif name == 'sv_quit':
                if source == 'internal':
                    self.quit()
                    output = 'Server is now offline'
                else:
                    output = 'No permissions'
            else:
                output = 'Command not found, try \'help\''
        elif name == 'exec':
            with open(os.path.join(sys.path[0], 'server', 'scripts', '{}.txt'.format(argstring)), 'r') as file:
                text = file.read()
            output = self.run_script(text)
        elif name == 'echo':
            output = argstring
        elif name == 'clear':
            output = '$$clear$$'
        else:
            output = 'Command not found, try \'help\''
        return output
    
    def run_script(self, text):
        output = ''
        for line in text.split('\n'):
            if not line == '':
                cmdout = self.handle_command(line)
                if not cmdout == '':
                    output += '{}\n'.format(cmdout)
        return output
    
    def load_map(self, mapname):
        self.serverdata.map = mapname
        
        with open(os.path.join(sys.path[0], 'server', 'maps', self.serverdata.map, 'list.json'), 'r') as file:
            self.serverdata.mapdata = json.load(file)
        
        for data in self.serverdata.conn_data:
            data['model'] = random.choice(self.serverdata.mapdata['entity models']['player'])
        
        req = Request(command = 'var update w', subcommand = 'map', arguments = {'map name': self.serverdata.map})
        self.send_all(req)
    
    def kick_address(self, target_address):
        i = 0
        to_delete = []
        for address, connection in self.serverdata.connections:
            if address[0] == target_address:
                connection.close()
                to_delete.append(i)
            i += 1
        for i in to_delete:
            self.serverdata.connections.pop(i)
    
    def send(self, connection, data):
        connection.send(data.as_json().encode())
        
    def send_all(self, data):
        for address, connection in self.serverdata.connections:
            self.send(connection, data)
    
    def quit(self):
        self.connection.close()

class Client:
    def __init__(self, host_, port_):
        class serverdata:
            host = host_
            port = port_
        self.serverdata = serverdata
        
        self.recv_binds = [] #functions to be called when data is received
        
        self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connection.connect((self.serverdata.host, self.serverdata.port))
        
        threading.Thread(target = self.recv_loop, name = 'Client receiver loop').start()
    
    def send_raw(self, text):
        self.connection.send(text.encode())
    
    def send(self, data):
        self.send_raw(data.as_json())
    
    def recv_loop(self):
        cont = True
        while cont:
            try:
                data = self.connection.recv(1024).decode('UTF-8')
                req = Request(data)
            except ConnectionAbortedError:
                req = Request(command = 'disconnect')
                cont = False
            for bind in self.recv_binds:
                bind(req)
    
    def disconnect(self):
        self.connection.close()

class Request:
    def __init__(self, data = {}, **args):
        #priorities data from the data variable over the flags
        if not data == {}:
            if type(data) == str:
                self.json_in(data)
            else:
                self.dict_in(data)
        elif not args == {}:
            self.dict_in(args)
        else:
            self.dict_in(data)
    
    def as_json(self):
        return json.dumps(self.as_dict())
    
    def as_dict(self):
        return {'command': self.command,
                'subcommand': self.subcommand,
                'arguments': self.arguments}
        
    def json_in(self, data):
        self.dict_in(json.loads(data))
   
    def dict_in(self, data):
        self._clear_all_values()
        
        if 'command' in data:
            self.command = data['command']
        else:
            self.command = ''
        if 'subcommand' in data:
            self.subcommand = data['subcommand']
        else:
            self.subcommand = None
        if 'arguments' in data:
            self.arguments = data['arguments']
        else:
            self.arguments = []
        
    def _clear_all_values(self):
        self.request_id = None
        self.response_id = None