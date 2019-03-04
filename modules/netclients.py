from tkinter import messagebox
import socket
import threading
import json
import random

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
    def __init__(self, address, connection, passthroughs):
        self.address = address
        self.connection = connection
        self.passthroughs = passthroughs
        
        self.running = True
        
        threading.Thread(target = self.listen, name = 'Client listen daemon').start()
    
    def listen(self):
        while self.running:
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
                    
            except ConnectionResetError or ConnectionAbortedError:
                reqs.append(Request(command = 'disconnect', arguments = {'clean': False})) #argument 'clean' shows whether or not a message was sent to close the connection or the conenction was forcibly closed
                self.running = False
            
            for passthrough in self.passthroughs:
                for req in reqs:
                    passthrough.handle(req)
        self.connection.close()
    
    def send(self, req):
        self.connection.send(req.as_json().encode())

class ServerClient:
    def __init__(self, server, interface):
        self.server = server
        self.interface = interface
        
        class metadata:
            model = None
            mode = None
            
            class pos:
                x = 0
                y = 0
                rotation = 0
            health = 0
            item_use_timestamp = None
            username = None
            team_id = None
        self.metadata = metadata
        
        self.serverdata = self.server.serverdata
        
        self.send_all = self.server.send_all
        self.send = self.interface.send
        self.client_display_text = self.server.send_text
    
    def output_console(self, string):
        'Send a string to the server console'
        self.server.output_pipe.send(string)
    
    def update_health(self, value, weapon, killer):
        old_health = self.metadata.health
        self.metadata.health = value
        
        if not old_health == self.metadata.health: #health has changed
            if old_health == 0 and self.metadata.health < 0: #death has already occured
                self.metadata.health = 0
            elif self.metadata.health <= 0 and old_health > 0: #this is the 'first death' (first time health reached 0)
                self.on_death(weapon, killer)
    
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
                if client['active']:
                    self.send(client['connection'], Request(command = 'var update w', subcommand = 'player positions', arguments = {'positions': self.get_all_positions([client['id']])}))
    
    def on_death(self, weapon, killer):
        self.metadata.health = 0
        
        #send death message to all connected clients
        s = random.choice(self.server.settingsdata['messages']['killfeed'])
        self.send_all(Request(command = 'event', subcommand = 'death', arguments = {'text': s.format(weapon = weapon.lower(), killer = killer, victim = self.metadata.username),
                                                                                    'weapon': weapon.lower()}))
        self.output_console('Player {} died'.format(self.metadata.username))
        
        self.set_mode(client, 'spectator')
        
        if self.serverdata.gamemode == 0:
            alive = self.num_alive()
            
            if alive[0] == 0:
                self.round_ended(winner = 1)
            elif alive[1] == 0:
                self.round_ended(winner = 0)
                
        elif self.serverdata.gamemode == 1:
            self.respawn_after(conn_id, self.settingsdata['player']['gamemodes']['deathmatch']['respawn time'])
            
        elif self.serverdata.gamemode == 2:
            if client['team'] == 0:
                self.increment_scoreline(score0 = 1)
            elif client['team'] == 1:
                self.increment_scoreline(score1 = 1)
                
            self.respawn_after(conn_id, self.settingsdata['player']['gamemodes']['team deathmatch']['respawn time'])
            
        elif self.serverdata.gamemode == 3:
            self.respawn_after(conn_id, self.settingsdata['player']['gamemodes']['pve surival']['respawn time'])
    
    def handle(self, req):
        if req.command == 'disconnect': #client wants to cleanly end it's connection with the server
            self.output_console('User {} disconnected'.format(self.interface.address[0]))
            if 'clean' in req.arguments and not req.arguments['clean']:
                self.output_console('Disconnect was not clean'.format(self.interface.address[0]))
                
        elif req.command == 'var update r': #client wants the server to send it a value
            if req.subcommand == 'map': #client wants the server to send the name of the current map
                self.send(Request(command = 'var update w', subcommand = 'map', arguments = {'map name': self.serverdata.map}))
                
            elif req.subcommand == 'player model': #client wants to know it's own player model
                if self.serverdata.map is not None:
                    self.send(Request(command = 'var update w', subcommand = 'player model', arguments = {'value': self.metadata.model}))
            
            elif req.subcommand == 'health':
                self.send(Request(command = 'var update w', subcommand = 'health', arguments = {'value': conn_data['health']}))
                
            elif req.subcommand == 'all player positions': #client wants to see all player positions (players marked as "active")
                self.send(Request(command = 'var update w', subcommand = 'player positions', arguments = {'positions': self.get_all_positions([conn_id])}))
            
            elif req.subcommand == 'round time':
                self.send(Request(command = 'var update w', subcommand = 'round time', arguments = {'value': self.get_timeleft()}))
                
        elif req.command == 'var update w': #client wants to update a variable on the server
            if req.subcommand == 'position': #client wants to update it's own position
                self.metadata.pos.x = req.arguments['x']
                self.metadata.pos.y = req.arguments['y']
                self.metadata.pos.rotation = req.arguments['rotation']
                
            elif req.subcommand == 'health': #client wants to update it's own health
                self.update_health(req.arguments['value'], weapon = 'environment', killer = 'world')
            
            elif req.subcommand == 'username':
                self.output_console('{} changed name to {}'.format(conn_data['username'], req.arguments['value']))
                self.serverdata.conn_data[conn_id]['username'] = req.arguments['value']
                self.database.user_connected(conn_data['username'])
                self.send_text(['chat', 'client changed name'], [conn_data['username']], connection)
                
        elif req.command == 'map loaded': #client has loaded the map and wants to be given the starting items and other information
            self.send(connection, Request(command = 'give', arguments = {'items': self.serverdata.mapdata['player']['starting items'][self.serverdata.conn_data[conn_id]['team']]}))
            self.send(connection, Request(command = 'var update w', subcommand = 'team', arguments = {'value': self.serverdata.conn_data[conn_id]['team']}))
            self.send(connection, Request(command = 'var update r', subcommand = 'username', arguments = {}))
            
            self.set_mode(conn_data, 'player')
            
            spawnpoint = self.generate_spawn(conn_id)
            self.send(connection, Request(command = 'var update w', subcommand = 'client position', arguments = {'x': spawnpoint[0], 'y': spawnpoint[1], 'rotation': 0}))
            
            self.send(connection, Request(command = 'set hit model', subcommand = {True: 'accurate', False: 'loose'}[self.settingsdata['network']['accurate hit detection']]))
            
            self.send_text(['fullscreen', 'welcome'], None, connection, category = 'welcome')
            
        elif req.command == 'use' and req.arguments['item'] in self.serverdata.item_dicts:
            if conn_data['last use'] is None or (time.time() - conn_data['last use']) > self.serverdata.item_dicts[req.arguments['item']]['use cooldown']:
                self.serverdata.item_data.append({'ticket': self.serverdata.item_ticket,
                                                  'data': self.serverdata.item_dicts[req.arguments['item']],
                                                  'file name': req.arguments['item'],
                                                  'distance travelled': 0,
                                                  'rotation': req.arguments['rotation'],
                                                  'position': req.arguments['position'],
                                                  'new': True,
                                                  'creator': conn_data})
                
                self.serverdata.item_ticket += 1
                conn_data['last use'] = time.time()
                
                self.send(connection, Request(command = 'increment inventory slot',
                                              arguments = {'index': req.arguments['slot'],
                                                           'increment': -1}))
        
        elif req.command == 'say':
            self.send_all(Request(command = 'say', arguments = {'text': '{}: {}'.format(self.conn_data['username'], req.arguments['text'])}))