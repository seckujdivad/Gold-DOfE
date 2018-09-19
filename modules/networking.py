from tkinter import messagebox
import multiprocessing as mp
import sqlite3 as sql
import socket
import threading
import json
import os
import sys
import random

import modules.servercmds
import modules.logging

class Server:
    def __init__(self, port_):
        class serverdata:
            host = ''
            port = port_
            connections = []
            map = None
            mapdata = None
            conn_data = [] #individual spaces for connections to store data to be publicly accessible
        self.serverdata = serverdata
        
        self.log = modules.logging.Log(os.path.join(sys.path[0], 'server', 'logs', 'svlog.txt'))
        
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
                                          'id': conn_id,
                                          'team': self.get_team_id(self.get_team_distributions()),
                                          'health': 100})
        
        
        print(self.serverdata.mapdata['player']['starting items'][self.serverdata.conn_data[conn_id]['team']])
        
        cont = True
        while cont:
            try:
                data = connection.recv(2048)
                req = Request(json.loads(data.decode()))
            except ConnectionResetError or ConnectionAbortedError:
                req = Request(command = 'disconnect', arguments = {'clean': False}) #argument 'clean' shows whether or not a message was sent to close the connection or the conenction was forcibly closed
                cont = False
            except json.decoder.JSONDecodeError:
                req = Request()
                self.log.add('error', 'Couldn\'t read JSON {}'.format(data))
                
            if req.command == 'disconnect': #client wants to cleanly end it's connection with the server
                self.output_pipe.send('User {} disconnected'.format(address[0]))
                if 'clean' in req.arguments and not req.arguments['clean']:
                    self.output_pipe.send('Disconnect was not clean'.format(address[0]))
                    
            elif req.command == 'var update r': #client wants the server to send it a value
            
                if req.subcommand == 'map': #client wants the server to send the name of the current map
                    self.send(connection, Request(command = 'var update w', subcommand = 'map', arguments = {'map name': self.serverdata.map}))
                    
                elif req.subcommand == 'player model': #client wants to know it's own player model
                    if self.serverdata.map != None:
                        self.send(connection, Request(command = 'var update w', subcommand = 'player model', arguments = {'value': self.serverdata.conn_data[conn_id]['model']}))
                        
                elif req.subcommand == 'all player positions': #client wants to see all player positions (players marked as "active")
                    output = []
                    for data in self.serverdata.conn_data:
                        if data['active'] and 'position' in data and not data == self.serverdata.conn_data[conn_id]:
                            output.append(data['position'])
                    self.send(connection, Request(command = 'var update w', subcommand = 'player positions', arguments = {'positions': output}))
                    
            elif req.command == 'var update w': #client wants to update a variable on the server
                if req.subcommand == 'position': #client wants to update it's own position
                    self.serverdata.conn_data[conn_id]['position'] = {'x': req.arguments['x'],
                                                                      'y': req.arguments['y'],
                                                                      'rotation': req.arguments['rotation']}
                elif req.subcommand == 'health': #client wants to update it's own health
                    self.serverdata.conn_data[conn_id]['health'] = req.arguments['value']
                    
            elif req.command == 'map loaded': #client has loaded the map and wants to be given the starting items and other information
                self.send(connection, Request(command = 'give', arguments = {'items': self.serverdata.mapdata['player']['starting items'][self.serverdata.conn_data[conn_id]['team']]}))
                self.send(connection, Request(command = 'var update w', subcommand = 'team', arguments = {'value': self.serverdata.conn_data[conn_id]['team']}))
                
                spawnpoint = random.choice(self.serverdata.mapdata['player']['spawnpoints'][self.serverdata.conn_data[conn_id]['team']])
                self.send(connection, Request(command = 'var update w', subcommand = 'client position', arguments = {'x': spawnpoint[0], 'y': spawnpoint[1], 'rotation': 0}))
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
        
        self.log.add('command input', command)
        
        output = 'ERROR'
        if name == 'help':
            output = '''Commands:
map: load a map by name
say: send a message to all players
exec: exexute a script by name stored in the server/scripts directory
echo: output the text given to the console
clear: clear the console
close_window: close the console

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
            output = 'Said \'{}\' to all users'.format(argstring)
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
        elif name == 'close_window':
            output = '$$close_window$$'
        else:
            output = 'Command not found, try \'help\''
            
        self.log.add('command output', output)
        
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
        
        for conn_data in self.serverdata.conn_data:
            if conn_data['active']:
                req = Request(command = 'give', arguments = {'items': self.serverdata.mapdata['player']['starting items'][conn_data['team']]})
                self.send(conn_data['connection'], req)
                req = Request(command = 'var update w', subcommand = 'team', arguments = {'value': conn_data['team']})
                self.send(conn_data['connection'], req)
                
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
        self.log.add('sent', 'Data sent to {} - {}'.format(connection.getpeername(), data.pretty_print()))
        connection.send(data.as_json().encode())
        
    def send_all(self, data):
        for address, connection in self.serverdata.connections:
            self.send(connection, data)
    
    def quit(self):
        self.connection.close()
    
    def get_team_id(self, team_quantities):
        return team_quantities.index(min(team_quantities))
    
    def get_team_distributions(self):
        team_quantities = [0, 0]
        for conn_data in self.serverdata.conn_data:
            if conn_data['active'] and conn_data['team'] != None:
                team_quantities[conn_data['team']] += 1
        return team_quantities

class Client:
    def __init__(self, host_, port_):
        class serverdata:
            host = host_
            port = port_
        self.serverdata = serverdata
        
        self.recv_binds = [] #functions to be called when data is received
        
        self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        try:
            self.connection.connect((self.serverdata.host, self.serverdata.port))
        except ConnectionRefusedError:
            messagebox.showerror('Connection refused', 'The connection was refused by the target machine. Make sure that the IP you are trying to connect to has a server running')
            raise ConnectionRefusedError()
        except socket.gaierror:
            messagebox.showerror('Address not found', 'The server address could not be found. Check it for misspellings and make sure that it is accessible on your network')
            raise socket.gaierror()
        
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
            except json.decoder.JSONDecodeError:
                req = Request(command = None)
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
    
    def pretty_print(self):
        return '<{}> - {} {}'.format(self.command, self.subcommand, self.arguments)

class ServerDatabase:
    def __init__(self, path, log = None):
        self.path = path
        self.log = log
        
        self.connection = sql.connect(self.path)
        
    def make(self):
        self.connection.execute("""CREATE TABLE `users` (
	`username`	TEXT,
	`lastconn`	REAL,
	`elo`	REAL,
	`wins`	INTEGER,
	`losses`	INTEGER,
	`metadata`	TEXT
)""")
        self.wrap_log('Made user table')
    
    def add_user(self, username):
        if self.get_user_data(username) == None:
            self.connection.execute("INSERT INTO `users` VALUES ((?), (?), 1500.0, 0, 0, '{}')", (username, time.time()))
            self.wrap_log('Added user {}'.format(username))
        else:
            self.wrap_log('Couldn\'t add user {}'.format(username))
            raise ValueError('Username "{}" is already in use'.format(username))
    
    def user_connected(self, username):
        self.connection.execute("UPDATE users SET lastconn = (?) WHERE username = (?)", (time.time(), username))
        self.wrap_log('User {} connected'.format(username))
    
    def match_concluded(self, winner_name, loser_name):
        if (not self.get_user_data(winner_name) == None) and (not self.get_user_data(winner_name) == None):
            self.connection.execute('UPDATE users SET wins = wins + 1 WHERE username = (?)', (winner_name))
            self.connection.execute('UPDATE users SET losses = losses + 1 WHERE username = (?)', (loser_name))
            self.wrap_log('{} beat {}, stored in database'.format(winner_name, loser_name))
        else:
            self.wrap_log('Couldn\'t find either {} or {}'.format(winner_name, loser_name))
            raise ValueError('Either {} or {} do not exist'.format(winner_name, loser_name))
    
    def get_user_data(self, username):
        'Finds the data for a user if they exist. If not, returns None'
        data = self.connection.execute("SELECT * FROM users WHERE username = (?)", (username)).fetchall()
        
        if len(data) == 0:
            self.wrap_log('Couldn\'t find data for {}'.format(username))
            return None
        else:
            self.wrap_log('Found data for {}, {} entry/entries'.format(username, len(data)))
            return data[0]
    
    def wrap_log(self, text):
        if not self.log == None:
            self.log.add('database', text)