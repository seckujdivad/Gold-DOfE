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

class NetClient:
    def __init__(self, address, connection):
        self.address = address
        self.connection = connection
        
        self.passthroughs = []
        self.running = False
    
    def start(self):
        self.running = True
        
        threading.Thread(target = self.listen, name = 'Client listen daemon').start()
    
    def listen(self):
        while self.running:
            reqs = []
            try:
                data = self.connection.recv(4096).decode('UTF-8')
                
                if type(data) is not str:
                    print(data)
                
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
                reqs.append(Request(command = 'disconnect', arguments = {'clean': False})) #argument 'clean' shows whether or not a message was sent to close the connection or the conenction was forcibly closed
                self.running = False
            
            for passthrough in self.passthroughs:
                for req in reqs:
                    passthrough.handle(req)
        self.connection.close()
    
    def send(self, req):
        self.send_to(self.connection, req)
    
    def send_to(self, connection, req):
        connection.send(req.as_json().encode())
    
    def close(self):
        self.connection.close()
        self.running = False

class ServerClient:
    def __init__(self, server, interface):
        self.server = server
        self.interface = interface
        
        self.interface.passthroughs.append(self)
        
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
        
        self.serverdata = self.server.serverdata
        
        self.send_all = self.server.send_all
        self.send = self.interface.send
        self.send_to = self.interface.send_to
        self.client_display_text = self.server.send_text
    
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
            
            for client in self.serverdata.conn_data:
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
        
        if self.serverdata.gamemode == 0:
            alive = self.server.num_alive()
            
            if alive[0] == 0:
                self.server.round_ended(winner = 1)
            elif alive[1] == 0:
                self.server.round_ended(winner = 0)
                
        elif self.serverdata.gamemode == 1:
            self.respawn_after(self.server.settingsdata['player']['gamemodes']['deathmatch']['respawn time'])
            
        elif self.serverdata.gamemode == 2:
            if self.metadata.team_id == 0:
                self.server.increment_scoreline(score0 = 1)
            elif self.metadata.team_id == 1:
                self.server.increment_scoreline(score1 = 1)
                
            self.respawn_after(self.server.settingsdata['player']['gamemodes']['team deathmatch']['respawn time'])
            
        elif self.serverdata.gamemode == 3:
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
        self.give(self.serverdata.mapdata['player']['starting items'][self.metadata.team_id])
    
    def respawn_after(self, delay):
        threading.Thread(target = self._respawn_after, args = [delay], name = 'Scheduled respawn', daemon = True).start()
    
    def _respawn_after(self, delay):
        time.sleep(delay)
        self.respawn()
    
    def generate_spawn(self):
        if self.serverdata.gamemode == 0:
            return random.choice(self.serverdata.mapdata['player']['spawnpoints'][0][self.metadata.team_id])
        elif self.serverdata.gamemode == 1:
            cmin, cmax = self.serverdata.mapdata['player']['spawnpoints'][1]
            return [random.randrange(cmin[0], cmax[0]), random.randrange(cmin[1], cmax[1])]
        elif self.serverdata.gamemode == 2:
            cmin, cmax = self.serverdata.mapdata['player']['spawnpoints'][2][self.metadata.team_id]
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
        self.send(Request(command = 'var update w', subcommand = 'player positions', arguments = {'positions': self.server.get_all_positions([self])}))
    
    def push_health(self):
        self.write_var('health', self.metadata.health)
    
    def handle(self, req):
        if req.command == 'disconnect': #client wants to cleanly end it's connection with the server
            self.output_console('User {} disconnected'.format(self.interface.address[0]))
            if 'clean' in req.arguments and not req.arguments['clean']:
                self.output_console('Disconnect was not clean'.format(self.interface.address[0]))
                
        elif req.command == 'var update r': #client wants the server to send it a value
            if req.subcommand == 'map': #client wants the server to send the name of the current map
                self.write_var('map', {'map name': self.serverdata.map})
                
            elif req.subcommand == 'player model': #client wants to know it's own player model
                if self.serverdata.map is not None:
                    self.write_var('player model', self.metadata.model)
            
            elif req.subcommand == 'health':
                self.write_var('health', self.metadata.health)
                
            elif req.subcommand == 'all player positions': #client wants to see all player positions (players marked as "active")
                self.push_positions()
            
            elif req.subcommand == 'round time':
                self.write_var('round time', self.server.get_timeleft())
                
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
            self.give(self.serverdata.mapdata['player']['starting items'][self.metadata.team_id])
            print(self.serverdata.mapdata['player']['starting items'][self.metadata.team_id])
            self.write_var('team', self.metadata.team_id)
            self.read_var('username')
            self.set_mode('player')
            
            spawnpoint = self.generate_spawn()
            self.setpos(spawnpoint[0], spawnpoint[1], 0)
            
            self.tell_use_accurate_hitscan(self.server.settingsdata['network']['accurate hit detection'])
            
            self.client_display_text(['fullscreen', 'welcome'], None, category = 'welcome')
            
        elif req.command == 'use' and req.arguments['item'] in self.serverdata.item_dicts:
            if self.metadata.item_use_timestamp is None or (time.time() - self.metadata.item_use_timestamp) > self.serverdata.item_dicts[req.arguments['item']]['use cooldown']:
                self.serverdata.item_data.append({'ticket': self.serverdata.item_ticket,
                                                  'data': self.serverdata.item_dicts[req.arguments['item']],
                                                  'file name': req.arguments['item'],
                                                  'distance travelled': 0,
                                                  'rotation': req.arguments['rotation'],
                                                  'position': req.arguments['position'],
                                                  'new': True,
                                                  'creator': self})
                
                self.serverdata.item_ticket += 1
                self.metadata.item_use_timestamp = time.time()
                
                self.send(Request(command = 'increment inventory slot',
                                  arguments = {'index': req.arguments['slot'],
                                               'increment': -1}))
        
        elif req.command == 'say':
            self.send_all(Request(command = 'say', arguments = {'text': '{}: {}'.format(self.metadata.username, req.arguments['text'])}))
    
    def close(self):
        self.metadata.active = False
        self.interface.close()