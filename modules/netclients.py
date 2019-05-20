from tkinter import messagebox
import socket
import threading
import json
import random
import time

from modules.networking import Request

class Client:
    def __init__(self, server_data, ui):
        class serverdata:
            raw = server_data
            host = raw['address']
            port = raw['port']
        self.serverdata = serverdata
        
        self.ui = ui
        
        self._log = None
        
        self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        try:
            self.connection.connect((self.serverdata.host, self.serverdata.port))
        except ConnectionRefusedError:
            messagebox.showerror('Connection refused', 'The connection was refused by the target machine. Make sure that the IP you are trying to connect to has a server running')
            raise ConnectionRefusedError()
        except socket.gaierror:
            messagebox.showerror('Address not found', 'The server address could not be found. Check it for misspellings and make sure that it is accessible on your network')
            raise socket.gaierror(0, 'Address not found')
        
        self.listener = SocketListen(self)
        self.listener.listen()
    
    def send_raw(self, text):
        self.connection.send(text.encode())
    
    def send(self, data):
        try:
            self.send_raw(data.as_json())
        except OSError:
            if self._log is not None:
                self._log.add('sending', 'Couldn\'t send request: {}'.format(data.pretty_print()))
    
    def read_var(self, category):
        self.var_update('read', category, None)
    
    def write_var(self, category, to_write):
        self.var_update('write', category, to_write)
    
    def var_update(self, mode, category, to_write):
        if type(to_write) is not dict:
            to_write = {'value': to_write}
        
        if mode.lower().startswith('r'):
            self.send(Request(command = 'var update r',
                              subcommand = category))
                              
        elif mode.lower().startswith('w'):
            self.send(Request(command = 'var update w',
                              subcommand = category,
                              arguments = to_write))
    
    def say(self, text):
        self.send(Request(command = 'say', arguments = {'text': text}))
    
    def use_item(self, item, rotation, position, slot):
        self.send(Request(command = 'use',
                          subcommand = 'client item',
                          arguments = {'item': item,
                                       'rotation': rotation,
                                       'position': position,
                                       'slot': slot}))
    
    def notify_map_load_finished(self):
        self.send(Request(command = 'map loaded'))
    
    def read_db(self, read_from, arguments = {}):
        self.send(Request(command = 'db read', subcommand = read_from, arguments = arguments))
    
    def write_db(self, write_to, data):
        if type(data) is not dict:
            data = {'data': data}

        self.send(Request(command = 'db write', subcommand = write_to, arguments = data))
    
    def list_lobbies(self):
        self.send(Request(command = 'lobby', subcommand = 'list'))
    
    def join_lobby(self, index):
        self.send(Request(command = 'lobby', subcommand = 'join', arguments = {'index': index}))
    
    def disconnect(self):
        self.connection.close()

class NetClient:
    def __init__(self, address, connection):
        self.address = address
        self.connection = connection
        
        self.listener = SocketListen(self)
        self._log = None
        
        self.running = False
    
    def start(self):
        self.running = True
        
        self.listener.listen()
    
    def send(self, req):
        self.send_to(self.connection, req)
    
    def send_to(self, connection, req):
        try:
            connection.send(req.as_json().encode())
        except OSError:
            if self._log is not None:
                self._log.add('sending', 'Couldn\'t send request: {}'.format(req.pretty_print()))
    
    def close(self):
        self.connection.close()
        self.running = False
        
class SocketListen:
    def __init__(self, parent):
        self.parent = parent
        
        self.binds = []
        self.running = False
    
    def listen(self):
        self.running = True
        threading.Thread(target = self._listen, name = 'Socket listener', daemon = True).start()
    
    def _listen(self):
        current_string = ''
        escape_level = 0
        is_escaped = False
        is_string = False
        
        while self.running:
            reqs = []
            output = []
            try:
                data = self.parent.connection.recv(4096).decode('UTF-8')
                
                if type(data) is not str:
                    print(data)
                
                #unpack the data - often will get multiple dictionaries
                for char in data:
                    if char == '{' and not is_escaped and not is_string:
                        escape_level += 1
                        
                    elif char == '}' and not is_escaped and not is_string:
                        escape_level -= 1
                        
                    elif char == '"' and not is_escaped:
                        is_string = not is_string
                        
                    elif char == '\\':
                        is_escaped = not is_escaped
                    
                    if not char == '\\':
                        is_escaped = False
                    
                    current_string += char
                    if escape_level == 0 and not len(current_string) == 0:
                        output.append(current_string)
                        current_string = ''
                
                for json_data in output:
                    reqs.append(Request(json_data))
                    
            except (ConnectionResetError, ConnectionAbortedError):
                reqs.append(Request(command = 'disconnect', arguments = {'clean': False})) #argument 'clean' shows whether or not a message was sent to close the connection or the conenction was forcibly closed
                self.running = False
            
            except json.JSONDecodeError:
                pass
            
            for bind in self.binds:
                for req in reqs:
                    bind(req)
                    
        self.parent.connection.close()

class ServerClient:
    def __init__(self, server, interface, lobby):
        self.server = server
        self.interface = interface
        self.lobby = lobby
        
        self.interface.listener.binds.append(self.handle)
        
        class metadata:
            model = None
            mode = None
            active = True
            
            class pos:
                x = 0
                y = 0
                rotation = 0

            health = 0
            item_use_timestamp = None
            username = None
            team_id = None
            id = None
        self.metadata = metadata
        
        self.send = self.interface.send
        self.send_to = self.interface.send_to
    
    def output_console(self, string):
        'Send a string to the server console'
        self.server.output_pipe.send(string)
    
    def update_health(self, value, weapon = None, killer = None):
        old_health = self.metadata.health
        self.metadata.health = value
        
        if not old_health == self.metadata.health: #health has changed
            if old_health == 0 and self.metadata.health < 0: #death has already occured
                self.metadata.health = 0
            elif self.metadata.health <= 0 and old_health > 0: #this is the 'first death' (first time health reached 0)
                self.on_death(weapon, killer)
    
    def increment_health(self, value, weapon = None, killer = None):
        self.update_health(self.metadata.health + value, weapon, killer)
    
    def set_mode(self, mode):
        self.send(Request(command = 'set mode', subcommand = mode))
        
        self.metadata.mode = mode
        
        if self.metadata.mode == 'spectator':
            self.client_display_text(['chat', 'new mode', 'spectator'], [self.metadata.username])
            self.output_console('{} is now spectating'.format(self.metadata.username))
        elif self.metadata.mode == 'player':
            self.client_display_text(['chat', 'new mode', 'player'], [self.metadata.username])
            self.output_console('{} is now playing'.format(self.metadata.username))
            
            for client in self.server.clients:
                if client.metadata.active:
                    self.push_positions()
    
    def on_death(self, weapon, killer):
        self.metadata.health = 0
        
        #send death message to all connected clients
        s = random.choice(self.server.settingsdata['messages']['killfeed'])
        self.send_all(Request(command = 'event', subcommand = 'death', arguments = {'text': s.format(weapon = weapon.lower(), killer = killer, victim = self.metadata.username),
                                                                                    'weapon': weapon.lower()}))
        self.output_console('Player {} died'.format(self.metadata.username))
        
        self.set_mode('spectator')
        
        if self.lobby.gamemode == 0:
            alive = self.lobby.num_alive()
            
            if alive[0] == 0:
                self.lobby.round_ended(winner = 1)
            elif alive[1] == 0:
                self.lobby.round_ended(winner = 0)
                
        elif self.lobby.gamemode == 1:
            self.respawn_after(self.server.settingsdata['player']['gamemodes']['deathmatch']['respawn time'])
            
        elif self.lobby.gamemode == 2:
            if self.metadata.team_id == 0:
                self.lobby.increment_scoreline(score0 = 1)
            elif self.metadata.team_id == 1:
                self.lobby.increment_scoreline(score1 = 1)
                
            self.respawn_after(self.server.settingsdata['player']['gamemodes']['team deathmatch']['respawn time'])
            
        elif self.lobby.gamemode == 3:
            self.respawn_after(self.server.settingsdata['player']['gamemodes']['pve surival']['respawn time'])
            
    def setpos(self, x = None, y = None, rotation = None):
        to_send = {}
        
        if x is not None:
            to_send['x'] = x
        if y is not None:
            to_send['y'] = y
        if rotation is not None:
            to_send['rotation'] = rotation
        
        self.write_var('client position', to_send)
    
    def respawn(self):
        spawnpoint = self.generate_spawn()
        self.set_mode('player')
        self.setpos(spawnpoint[0], spawnpoint[1], 0)
        self.update_health(100)
        self.clear_inventory()
        self.give(self.lobby.map.data['player']['starting items'][self.metadata.team_id])
    
    def respawn_after(self, delay):
        threading.Thread(target = self._respawn_after, args = [delay], name = 'Scheduled respawn', daemon = True).start()
    
    def _respawn_after(self, delay):
        time.sleep(delay)
        self.respawn()
    
    def generate_spawn(self):
        if self.lobby.gamemode == 0:
            return random.choice(self.lobby.map.data['player']['spawnpoints'][0][self.metadata.team_id])

        elif self.lobby.gamemode == 1:
            cmin, cmax = self.lobby.map.data['player']['spawnpoints'][1]
            return [random.randrange(cmin[0], cmax[0]), random.randrange(cmin[1], cmax[1])]

        elif self.lobby.gamemode == 2:
            cmin, cmax = self.lobby.map.data['player']['spawnpoints'][2][self.metadata.team_id]
            return [random.randrange(cmin[0], cmax[0]), random.randrange(cmin[1], cmax[1])]
    
    def read_var(self, category):
        self.var_update('read', category, None)
    
    def write_var(self, category, to_write):
        self.var_update('write', category, to_write)
    
    def var_update(self, mode, category, to_write):
        if type(to_write) is not dict:
            to_write = {'value': to_write}
        
        if mode.lower().startswith('r'):
            self.send(Request(command = 'var update r',
                              subcommand = category))
                              
        elif mode.lower().startswith('w'):
            self.send(Request(command = 'var update w',
                              subcommand = category,
                              arguments = to_write))
    
    def give(self, items):
        self.send(Request(command = 'give',
                          arguments = {'items': items}))
    
    def tell_use_accurate_hitscan(self, use_accurate_hitscan):
        self.send(Request(command = 'set hit model', subcommand = {True: 'accurate', False: 'loose'}[use_accurate_hitscan]))
    
    def clear_inventory(self):
        self.send(Request(command = 'clear inventory'))
    
    def push_item_states(self, states):
        self.send(Request(command = 'update items', subcommand = 'server tick', arguments = {'pushed': states}))
    
    def push_positions(self):
        self.send(Request(command = 'var update w', subcommand = 'player positions', arguments = {'positions': self.lobby.get_all_positions([self])}))
    
    def push_health(self):
        self.write_var('health', self.metadata.health)
    
    def send_all(self, req, only_lobby = True):
        if only_lobby:
            self.lobby.send_all(req)
        
        else:
            self.server.send_all(req)
    
    def client_display_text(self, path, formats = None, target = None, category = 'general'):
        if self.lobby is None:
            raise Exception('Client is not in a lobby; can\'t send formatted text')
        
        else:
            self.lobby.send_text(path, formats, target, category)
    
    def handle(self, req):
        if req.command == 'disconnect': #client wants to cleanly end it's connection with the server
            self.output_console('User {} disconnected'.format(self.interface.address[0]))
            if 'clean' in req.arguments and not req.arguments['clean']:
                self.output_console('Disconnect was not clean')
        
        elif req.command == 'lobby':
            if req.subcommand == 'join':
                self.server.join_lobby(self, req.arguments['index'])
            
            elif req.subcommand == 'list':
                self.send(Request(command = 'lobby response', subcommand = 'list', arguments = {'lobbies': self.server.list_lobbies(show_inactive = False)}))
        
        if self.lobby is None: #player is in the menu, not a lobby
            if req.command == 'say':
                self.send_all(Request(command = 'say', arguments = {'text': '{}: {}'.format(self.metadata.username, req.arguments['text'])}), only_lobby = False)
        
            elif req.command == 'db read':
                if req.subcommand == 'leaderboard':
                    self.send(Request(command = 'db read response', subcommand = 'leaderboard', arguments = {'data': self.server.database.get_leaderboard(req.arguments['num'])}))
            
            elif req.command == 'db write':
                pass
        
        else: #player is in a lobby
            if req.command == 'var update r': #client wants the server to send it a value
                if req.subcommand == 'map': #client wants the server to send the name of the current map
                    self.write_var('map', {'map name': self.lobby.map.name})
                    
                elif req.subcommand == 'player model': #client wants to know it's own player model
                    if self.lobby.map.name is not None:
                        self.write_var('player model', self.metadata.model)
                
                elif req.subcommand == 'health':
                    self.write_var('health', self.metadata.health)
                    
                elif req.subcommand == 'all player positions': #client wants to see all player positions (players marked as "active")
                    self.push_positions()
                
                elif req.subcommand == 'round time':
                    self.write_var('round time', self.lobby.get_timeleft())
                    
            elif req.command == 'var update w': #client wants to update a variable on the server
                if req.subcommand == 'position': #client wants to update it's own position
                    self.metadata.pos.x = req.arguments['x']
                    self.metadata.pos.y = req.arguments['y']
                    self.metadata.pos.rotation = req.arguments['rotation']
                    
                elif req.subcommand == 'health': #client wants to update it's own health
                    self.update_health(req.arguments['value'], weapon = 'environment', killer = 'world')
                
                elif req.subcommand == 'username':
                    self.output_console('{} changed name to {}'.format(self.metadata.username, req.arguments['value']))
                    self.metadata.username = req.arguments['value']
                    self.server.database.user_connected(self.metadata.username)
                    self.client_display_text(['chat', 'client changed name'], [self.metadata.username])
                    
            elif req.command == 'map loaded': #client has loaded the map and wants to be given the starting items and other information
                self.give(self.lobby.map.data['player']['starting items'][self.metadata.team_id])
                print(self.lobby.map.data['player']['starting items'][self.metadata.team_id])
                self.write_var('team', self.metadata.team_id)
                self.read_var('username')
                self.set_mode('player')
                
                spawnpoint = self.generate_spawn()
                self.setpos(spawnpoint[0], spawnpoint[1], 0)
                
                self.tell_use_accurate_hitscan(self.server.settingsdata['network']['accurate hit detection'])
                
                self.client_display_text(['fullscreen', 'welcome'], None, category = 'welcome')
                
            elif req.command == 'use' and req.arguments['item'] in self.lobby.item_dicts:
                if self.metadata.item_use_timestamp is None or (time.time() - self.metadata.item_use_timestamp) > self.lobby.item_dicts[req.arguments['item']]['use cooldown']:
                    obj = self.lobby.item_scripts[self.lobby.item_dicts[req.arguments['item']]['control script']](req.arguments['item'], self.server)
                    
                    obj.attributes.creator = self
                    obj.attributes.pos.x = req.arguments['position'][0]
                    obj.attributes.pos.y = req.arguments['position'][1]
                    obj.attributes.rotation = req.arguments['rotation']
                    obj.attributes.ticket = self.lobby.item_ticket
                    obj.set_velocity(self.lobby.item_dicts[req.arguments['item']]['speed'])
                    
                    self.lobby.item_objects.append(obj)
                    
                    self.lobby.item_ticket += 1
                    self.metadata.item_use_timestamp = time.time()
                    
                    self.send(Request(command = 'increment inventory slot',
                                    arguments = {'index': req.arguments['slot'],
                                                'increment': -1}))
            
            elif req.command == 'say':
                self.send_all(Request(command = 'say', arguments = {'text': '{}: {}'.format(self.metadata.username, req.arguments['text'])}))
    
    def close(self):
        self.metadata.active = False
        self.interface.close()