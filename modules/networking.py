from tkinter import messagebox
import multiprocessing as mp
import sqlite3 as sql
import socket
import threading
import json
import os
import sys
import random
import time
import math

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
            item_data = [] #store ongoing items
            item_ticket = 0 #allow clients to know which items are which from tick to tick
            tickrate = 10 #times to process items per second
            looptime = 1 / tickrate
        self.serverdata = serverdata
        
        self.log = modules.logging.Log(os.path.join(sys.path[0], 'server', 'logs', 'svlog.txt'))
        
        self.database = ServerDatabase(os.path.join(sys.path[0], 'server', 'database.db'), modules.logging.Log(os.path.join(sys.path[0], 'server', 'logs', 'dblog.txt')))
        
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
        
        self.serverdata.tickrate = self.settingsdata['network']['tickrate']
        self.serverdata.looptime = 1 / self.serverdata.tickrate

        threading.Thread(target = self.acceptance_thread, name = 'Acceptance thread', daemon = True).start()
        threading.Thread(target = self.handle_items, name = 'Item handler', daemon = True).start()
        
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
                                          'health': 100,
                                          'username': 'guest'})
        
        self.send(connection, Request(command = 'var update r', subcommand = 'username'))
        
        cont = True
        while cont:
            reqs = []
            try:
                data = connection.recv(4096).decode('UTF-8')
                
                #unpack the data - often will get multiple dictionaries
                escape_level = 0
                output = []
                current_string = ''
                for char in data:
                    if char == '{':
                        escape_level += 1
                    elif char == '}':
                        escape_level -= 1
                    current_string += char
                    if escape_level == 0 and not len(current_string) == 0:
                        output.append(current_string)
                        current_string = ''
                
                for json_data in output:
                    reqs.append(Request(json_data))
            except ConnectionResetError or ConnectionAbortedError:
                req = Request(command = 'disconnect', arguments = {'clean': False}) #argument 'clean' shows whether or not a message was sent to close the connection or the conenction was forcibly closed
                cont = False
            except json.decoder.JSONDecodeError:
                pass
            for req in reqs:
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
                    
                    elif req.subcommand == 'health':
                        self.send(connection, Request(command = 'var update w', subcommand = 'health', arguments = {'value': self.serverdata.conn_data[conn_id]['health']}))
                            
                    elif req.subcommand == 'all player positions': #client wants to see all player positions (players marked as "active")
                        output = []
                        for data in self.serverdata.conn_data:
                            if data['active'] and 'position' in data and not data == self.serverdata.conn_data[conn_id] and not data['health'] == 0:
                                output.append(data['position'])
                        self.send(connection, Request(command = 'var update w', subcommand = 'player positions', arguments = {'positions': output}))
                        
                elif req.command == 'var update w': #client wants to update a variable on the server
                    if req.subcommand == 'position': #client wants to update it's own position
                        self.serverdata.conn_data[conn_id]['position'] = {'x': req.arguments['x'],
                                                                          'y': req.arguments['y'],
                                                                          'rotation': req.arguments['rotation']}
                    elif req.subcommand == 'health': #client wants to update it's own health
                        self.update_health(self.serverdata.conn_data[conn_id], req.arguments['value'])
                    
                    elif req.subcommand == 'username':
                        self.serverdata.conn_data[conn_id]['username'] = req.arguments['value']
                        self.database.user_connected(self.serverdata.conn_data[conn_id]['username'])
                        
                elif req.command == 'map loaded': #client has loaded the map and wants to be given the starting items and other information
                    self.send(connection, Request(command = 'give', arguments = {'items': self.serverdata.mapdata['player']['starting items'][self.serverdata.conn_data[conn_id]['team']]}))
                    self.send(connection, Request(command = 'var update w', subcommand = 'team', arguments = {'value': self.serverdata.conn_data[conn_id]['team']}))
                    self.send(connection, Request(command = 'var update r', subcommand = 'username', arguments = {}))
                    
                    spawnpoint = random.choice(self.serverdata.mapdata['player']['spawnpoints'][self.serverdata.conn_data[conn_id]['team']])
                    self.send(connection, Request(command = 'var update w', subcommand = 'client position', arguments = {'x': spawnpoint[0], 'y': spawnpoint[1], 'rotation': 0}))
                    
                    self.send(connection, Request(command = 'popmsg', subcommand = 'welcome', arguments = {'text': self.settingsdata['welcome text']}))
                elif req.command == 'use':
                    with open(os.path.join(sys.path[0], 'server', 'maps', self.serverdata.map, 'items', req.arguments['item']), 'r') as file:
                        item_data = json.load(file)
                    
                    self.serverdata.item_data.append({'ticket': self.serverdata.item_ticket,
                                                      'data': item_data,
                                                      'file name': req.arguments['item'],
                                                      'distance travelled': 0,
                                                      'rotation': req.arguments['rotation'],
                                                      'position': req.arguments['position'],
                                                      'new': True})
                    
                    self.serverdata.item_ticket += 1
                
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
say_pop: send a fullscreen message to all players
exec: execute a script by name stored in the server/scripts directory
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
                    output = 'Error while loading map \'{}\''.format(argstring)
            else:
                output = 'No permissions'
        elif name.startswith('say'):
            if name == 'say':
                self.send_all(Request(command = 'say', arguments = {'text': argstring}))
                output = 'Said \'{}\' to all users'.format(argstring)
            elif name == 'say_pop':
                self.send_all(Request(command = 'popmsg', subcommand = 'general', arguments = {'text': argstring}))
                output = 'Said \'{}\' to all users with a fullscreen message'.format(argstring)
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
    
    def handle_items(self):
        while True:
            start = time.time()
            
            to_remove = []
            data_to_send = []
            
            i = 0
            for item in self.serverdata.item_data:
                to_send_loop = {}
                
                out_of_bounds = False
                if item['data']['hitbox']['type'] == 'circular':
                    if item['position'][0] > self.serverdata.mapdata['geometry'][0] + item['data']['hitbox']['radius']:
                        out_of_bounds = True
                    elif item['position'][0] < 0 - item['data']['hitbox']['radius']:
                        out_of_bounds = True
                    if item['position'][1] > self.serverdata.mapdata['geometry'][1] + item['data']['hitbox'][
                        'radius']:
                        out_of_bounds = True
                    elif item['position'][1] < 0 - item['data']['hitbox']['radius']:
                        out_of_bounds = True
            
                if ((not item['data']['range'] == None) and item['distance travelled'] >= item['data']['range']) or out_of_bounds:
                    to_send_loop['type'] = 'remove'
                    to_send_loop['ticket'] = item['ticket']
                    to_remove.append(i)
                   
                elif item['new']:
                    to_send_loop['type'] = 'add'
                    
                    to_send_loop['position'] = item['position']
                    to_send_loop['rotation'] = item['rotation']
                    to_send_loop['new'] = True
                    item['new'] = False
                    to_send_loop['data'] = item['data']
                
                elif not item['data']['speed'] == 0:
                    to_send_loop['type'] = 'update position'
                    
                    to_move = item['data']['speed'] / self.serverdata.tickrate

                    item['position'][0] +=  to_move * math.cos(math.radians(item['rotation']))
                    item['position'][1] +=  to_move * math.sin(math.radians(item['rotation']))
                    
                    to_send_loop['position'] = item['position']
                    
                #clipping
                for playerdata in self.serverdata.conn_data:
                    damage_dealt = False
                    if playerdata['active']:
                        if self.item_touches_player(playerdata['position']['x'], playerdata['position']['y'], item):
                            if item['data']['destroyed after damage']:
                                to_send_loop['type'] = 'remove'
                                to_send_loop['ticket'] = item['ticket']
                                to_remove.append(i)
                                
                            if 'last damage' in item and not item['last damage'] == None:
                                if (time.time() - item['last damage']) > item['data']['damage cooldown']:
                                    damage_dealt = True
                            else:
                                damage_dealt = True
                    
                    if damage_dealt:
                        self.increment_health(playerdata, 0 - item['data']['damage']['player'])
                        item['last damage'] = time.time()
                        
                        self.send(playerdata['connection'], Request(command = 'var update w', subcommand = 'health', arguments = {'value': playerdata['health']}))
                
                if not to_send_loop == {}:
                    to_send_loop['ticket'] = item['ticket']
                    data_to_send.append(to_send_loop)
                    
                i += 1
			
            to_remove.sort()
            to_remove.reverse()
            for i in to_remove:
                self.serverdata.item_data.pop(i)
            
            for conn_data in self.serverdata.conn_data:
                self.send(conn_data['connection'], Request(command = 'update items', subcommand = 'server tick', arguments = {'pushed': data_to_send}))
            
            time.sleep(max(0, self.serverdata.looptime - (time.time() - start))) #prevent server from running too quickly
    
    def item_touches_player(self, x, y, item):
        if item['data']['hitbox']['type'] == 'circular':
            if self.distance_to_point(x, y, *item['position']) <= item['data']['hitbox']['radius']:
                return True
        return False
    
    def distance_to_point(self, x0, y0, x1, y1):
        return math.hypot(x1 - x0, y1 - y0)
    
    def update_health(self, client_data, health):
        old_health = client_data['health']
        client_data['health'] = health
        
        if not old_health == client_data['health']: #health has changed
            if (old_health == 0 and client_data['health'] < 0): #death has already occured
                client_data['health'] = 0
            elif client_data['health'] <= 0 and old_health > 0: #this is the first death
                client_data['health'] = 0
                self.send_all(Request(command = 'event', subcommand = 'death', arguments = {'username': client_data['username']}))
                self.send_all(Request(command = 'say', arguments = {'text': '{} died'.format(client_data['username']), 'category': 'death'}))
    
    def increment_health(self, client_data, health):
        self.update_health(client_data, client_data['health'] + health)

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
            reqs = []
            try:
                data = self.connection.recv(4096).decode('UTF-8')
                
                #unpack the data - often will get multiple dictionaries
                escape_level = 0
                output = []
                current_string = ''
                for char in data:
                    if char == '{':
                        escape_level += 1
                    elif char == '}':
                        escape_level -= 1
                    current_string += char
                    if escape_level == 0 and not len(current_string) == 0:
                        output.append(current_string)
                        current_string = ''
                
                for json_data in output:
                    reqs.append(Request(json_data))
            except ConnectionAbortedError:
                reqs = [Request(command = 'disconnect')]
                cont = False
            except json.decoder.JSONDecodeError:
                pass
            for bind in self.recv_binds:
                for req in reqs:
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
        
        pipe, self.pipe = mp.Pipe()
        
        threading.Thread(target = self.databasecontrollerd, name = 'Server database controller daemon', args = [pipe]).start()
    
    def databasecontrollerd(self, input_pipe):
        database_is_new = False
        if not os.path.isfile(self.path):
            database_is_new = True
            
        self.connection = sql.connect(self.path)
        
        if database_is_new:
            self._make()
        
        self._log_wrapper('Connected to SQLite database at {}'.format(self.path))
        
        cont = True
        while cont:
            data = input_pipe.recv()
            
            if len(data) == 2:
                task, arguments = data
                
                self._log_wrapper('Received command #{} with arguments {}'.format(task, arguments))
                
                if task == self.lookup.make:
                    self._make()
                elif task == self.lookup.disconnect:
                    cont = False
                elif task == self.lookup.user_connected:
                    self._user_connected(arguments[0])
                elif task == self.lookup.match_concluded:
                    self._match_concluded(arguments[0], arguments[1])
                elif task == self.lookup.get_user_data:
                    self.output.dictionary[arguments[1]] = self._get_user_data(arguments[0])
                else:
                    self._log_wrapper('Uncaught command #{}'.format(task))
            else:
                self._log_wrapper('Command must be of length 2, not {}'.format(len(data)))
            self.connection.commit()
        self.connection.close()
                
    def _make(self):
        'Make the \'users\' table in the database. Overwrites if it already exists'
        self.connection.execute("""CREATE TABLE `users` (
	`username`	TEXT,
	`lastconn`	REAL,
	`elo`	REAL,
	`wins`	INTEGER,
	`losses`	INTEGER,
	`metadata`	TEXT
)""")
        self._log_wrapper('Made user table')
    
    def _add_user(self, username):
        'Add a user to the database if the username doesn\'t already exist'
        if self._get_user_data(username) == None:
            self.connection.execute("INSERT INTO `users` VALUES ((?), (?), 1500.0, 0, 0, '{}')", (username, time.time()))
            self._log_wrapper('Added user {}'.format(username))
        else:
            self._log_wrapper('Couldn\'t add user {}'.format(username))
            raise ValueError('Username "{}" is already in use'.format(username))
    
    def _user_connected(self, username):
        'Add a user if they don\'t already exist. Update their last connection time if they do'
        if self._get_user_data(username) == None:
            self._add_user(username)
        self.connection.execute("UPDATE users SET lastconn = (?) WHERE username = (?)", (time.time(), username))
        self._log_wrapper('User {} connected'.format(username))
    
    def _match_concluded(self, winner_name, loser_name):
        'Update win/loss records for two users'
        if (not self._get_user_data(winner_name) == None) and (not self._get_user_data(winner_name) == None):
            self.connection.execute('UPDATE users SET wins = wins + 1 WHERE username = (?)', (winner_name,))
            self.connection.execute('UPDATE users SET losses = losses + 1 WHERE username = (?)', (loser_name,))
            self._log_wrapper('{} beat {}, stored in database'.format(winner_name, loser_name))
        else:
            self._log_wrapper('Couldn\'t find either {} or {}'.format(winner_name, loser_name))
            raise ValueError('Either {} or {} do not exist'.format(winner_name, loser_name))
    
    def _get_user_data(self, username):
        'Return all information on a user'
        'Finds the data for a user if they exist. If not, returns None'
        data = self.connection.execute("SELECT * FROM users WHERE username = (?)", (username,)).fetchall()
        
        if len(data) == 0:
            self._log_wrapper('Couldn\'t find data for {}'.format(username))
            return None
        else:
            self._log_wrapper('Found data for {}, {} entry/entries'.format(username, len(data)))
            return data[0]
    
    def _log_wrapper(self, text):
        'A wrapper for the database log (if it has been specified)'
        if not self.log == None:
            self.log.add('database', text)
    
    class lookup:
        make = 0
        disconnect = 1
        user_connected = 2
        match_concluded = 3
        get_user_data = 4
    
    class output:
        ticket = 0
        dictionary = {}
    
    def make(self):
        'Make the \'users\' table in the database. Overwrites if it already exists'
        self.pipe.send([self.lookup.make, []])
    
    def disconnect(self):
        'Disconnect from the database'
        self.pipe.send([self.lookup.disconnect, []])
    
    def user_connected(self, username):
        'Updates the last connection time on a user'
        self.pipe.send([self.lookup.user_connected, [username]])
        print('{} connected'.format(username))
    
    def match_concluded(self, winner_name, loser_name):
        self.pipe.send([self.lookup.match_concluded, [winner_name, loser_name]])
    
    def get_user_data(self, username):
        ticket = str(self.output.ticket)
        self.output.ticket += 1
        
        self.pipe.send([self.lookup.get_user_data, [username, ticket]])
        
        while not ticket in self.output.dictionary:
            time.sleep(0.05)
        return self.output.dictionary.pop(ticket)