import multiprocessing as mp
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
import modules.netclients
import modules.modloader
import modules.dbaccess

class Server:
    def __init__(self, port_, frame = None):
        class serverdata:
            host = '' #hostname of server
            port = port_ #port server is operating on
            connections = [] #open or closed connections with clients
            
            running = True #whether or not server is running
            
            tickrate = 10 #times to process items per second
            looptime = 1 / tickrate #time per loop
            
            map = None #map name
            mapdata = None #map attributes
            
            item_dicts = {} #store attributes of the map's possible items
            item_objects = [] #store ongoing items
            item_scripts = {}
            item_ticket = 0 #allow clients to know which items are which from tick to tick
            
            gamemode = None #current gamemode int
            scoreline = [0, 0] #current game scoreline
            round_start_time = None #timestamp for start of round
            round_in_progress = False #whether or not a round is in progress
        self.serverdata = serverdata
        
        self.clients = []
        self.modloader = None
        
        self.frame = frame
        
        self.log = modules.logging.Log(os.path.join(sys.path[0], 'server', 'logs', 'svlog.txt'))
        
        self.database = modules.dbaccess.ServerDatabase(os.path.join(sys.path[0], 'server', 'database.db'), modules.logging.Log(os.path.join(sys.path[0], 'server', 'logs', 'dblog.txt')))
        
        self.output_pipe, pipe = mp.Pipe()
        
        self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connection.bind((self.serverdata.host, self.serverdata.port))
        self.connection.listen(5)
        
        self.cmdline = modules.servercmds.ServerCommandLineUI(self.handle_command, pipe, self.frame)
        
        with open(os.path.join(sys.path[0], 'server', 'config.json'), 'r') as file:
            self.settingsdata = json.load(file)
        for script in self.settingsdata['scripts']['autoexec']:
            with open(os.path.join(sys.path[0], 'server', 'scripts', '{}.txt'.format(script)), 'r') as file:
                text = file.read()
            self.output_pipe.send(self.run_script(text))
        
        self.serverdata.tickrate = self.settingsdata['network']['tickrate']
        self.serverdata.looptime = 1 / self.serverdata.tickrate
        
        while self.serverdata.mapdata is None:
            time.sleep(0.01) #refuse to come online until a map is loaded
        
        self.serverdata.round_start_time = time.time()
        self.serverdata.round_in_progress = True

        threading.Thread(target = self.acceptance_thread, name = 'Acceptance thread', daemon = True).start()
        threading.Thread(target = self.handle_items, name = 'Item handler', daemon = True).start()
        threading.Thread(target = self.push_timeleftd, name = 'Round timer daemon', daemon = True).start()
        
    def acceptance_thread(self):
        current_id = 0
        while self.serverdata.running:
            self.output_pipe.send('Ready for incoming connections')
            
            try:
                conn, addr = self.connection.accept()
            except OSError:
                addr, conn = (None, None)
                self.serverdata.running = False
            
            if self.serverdata.running:
                self.serverdata.connections.append([addr, conn])
                
                netcl = modules.netclients.NetClient(addr, conn)
                client = modules.netclients.ServerClient(self, netcl)
                
                client.metadata.health = 100
                client.metadata.username = 'guest'
                client.metadata.team_id = self.get_team_id(self.get_team_distributions())
                
                client.metadata.id = current_id
                current_id += 1
                
                netcl.start()
                
                self.clients.append(client)
                
                for script in self.settingsdata['scripts']['userconnect']:
                    with open(os.path.join(sys.path[0], 'server', 'scripts', '{}.txt'.format(script)), 'r') as file:
                        text = file.read()
                    self.output_pipe.send(self.run_script(text))
    
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
exec: execute a script by name stored in the server/scripts directory
echo: output the text given to the console
clear: clear the console
close_window: close the console

say: send a message to all players
say_pop: send a fullscreen message to all players

mp_:
mp_gamemode: set the gamemode
mp_respawn_all: respawn all players
mp_scoreline_team1: set the scoreline of team 1
mp_scoreline_team2: set the scoreline of team 2

sv_:
sv_conns: list of connections to the server
sv_kick_addr: kick a player by address
sv_quit: destroy the server
sv_hitbox: choose whether or not to use accurate hitboxes

db_:
db_commit: push all database changes to the disk
db_reset: resets the database'''
        elif name == 'map':
            if source == 'internal':
                try:
                    self.load_map(argstring)
                    output = 'Loading map \'{}\'...'.format(argstring)
                except ValueError:
                    type, value, traceback = sys.exc_info()
                    output = 'Error while loading map \'{}\'\nERROR: {}\n{}'.format(argstring, type, value)
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
                    
            elif name == 'sv_hitbox':
                if source == 'internal':
                    try:
                        for client in self.clients:
                            client.set_hitboxes(argstring)
                    except ValueError:
                        output = 'Error while setting hitboxes to \'{}\''.format(argstring)
                else:
                    output = 'No permissions'
            else:
                output = 'Command not found, try \'help\''
                
        elif name.startswith('mp_'):
            if name == 'mp_gamemode':
                if source == 'internal':
                    if argstring == '':
                        output = '''Options:
0: xvx arena
1: deathmatch
2: team deathmatch
3: pve survival'''
                    else:
                        output = ['Gamemode not supported by this map', 'Gamemode changed successfully', 'This is already the gamemode - no action taken'][self.set_gamemode(int(argstring))]
                else:
                    output = 'No permissions'
                    
            elif name == 'mp_respawn_all':
                if source == 'internal':
                    self.respawn_all()
                    output = 'Done!'
                else:
                    output = 'No permissions'
                    
            elif name.startswith('mp_scoreline_'):
                if name == 'mp_scoreline_team1':
                    if argstring == '':
                        output = 'Score for team 1: {}'.format(self.serverdata.scoreline[0])
                    elif source == 'internal':
                        self.set_scoreline(score0 = int(argstring))
                    else:
                        output = 'No permissions'
                        
                elif name == 'mp_scoreline_team2':
                    if argstring == '':
                        output = 'Score for team 2: {}'.format(self.serverdata.scoreline[1])
                    elif source == 'internal':
                        self.set_scoreline(score1 = int(argstring))
                    else:
                        output = 'No permissions'
                        
                else:
                    output = 'Command not found, try \'help\''
                    
            else:
                output = 'Command not found, try \'help\''
        
        elif name.startswith('db_'):
            if name == 'db_commit':
                if source == 'internal':
                    self.database.commit()
                    output = 'Temporary database changes committed'
                else:
                    output = 'No permissions'
            
            elif name == 'db_reset':
                if source == 'internal':
                    self.database.reset()
                    output = 'Database reset'
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
        
        self.set_gamemode(self.serverdata.mapdata['gamemode']['default'])
        
        for client in self.clients:
            if client.metadata.active:
                client.write_var('map', {'map name': self.serverdata.map})
                client.give(self.serverdata.mapdata['player']['starting items'][client.metadata.team_id])
                client.write_var('team', client.metadata.team_id)
                client.metadata.model = random.choice(self.serverdata.mapdata['entity models']['player'])
        
        self.serverdata.item_dicts = {}
        for name in os.listdir(os.path.join(sys.path[0], 'server', 'maps', self.serverdata.map, 'items')):
            if name.endswith('.json'):
                with open(os.path.join(sys.path[0], 'server', 'maps', self.serverdata.map, 'items', name), 'r') as file:
                    self.serverdata.item_dicts[name] = json.load(file)
        
        self.modloader = modules.modloader.ModLoader(os.path.join(sys.path[0], 'server', 'maps', self.serverdata.map, 'items'))
        scripts = self.modloader.load('ItemScript')
        self.serverdata.item_scripts = {}
        for script in scripts:
            self.serverdata.item_scripts[script.internal_name] = script
                
    def kick_address(self, target_address):
        i = 0
        to_delete = []
        for client in self.clients:
            if client.interface.address[0] == target_address:
                client.close()
                to_delete.append(i)
            i += 1
            
        to_delete.reverse()
        for i in to_delete:
            self.serverdata.connections.pop(i)
    
    def send(self, connection, data):
        self.log.add('sent', 'Data sent to {} - {}'.format(connection.getpeername(), data.pretty_print()))
        connection.send(data.as_json().encode())
        
    def send_all(self, data):
        for client in self.clients:
            client.send(data)
    
    def quit(self):
        self.send_all(Request(command = 'disconnect', arguments = {'clean': True}))
        self.serverdata.running = False
        self.connection.close()
        self.database.close()
    
    def get_team_id(self, team_quantities):
        return team_quantities.index(min(team_quantities))
    
    def get_team_distributions(self):
        team_quantities = [0, 0]
        for client in self.clients:
            if client.metadata.active and client.metadata.team_id is not None:
                team_quantities[client.metadata.team_id] += 1
        return team_quantities
    
    def handle_items(self):
        delayed_instructions = {}
        
        while self.serverdata.running:
            start = time.time()
            
            to_remove = []
            data_to_send = []
            
            i = 0
            for item in self.serverdata.item_objects:
                data = item.tick()
                
                to_append = []
                if item.attributes.ticket in delayed_instructions:
                    j = 0
                    j_to_remove = []
                    for instruction, stamp in delayed_instructions[item.attributes.ticket]:
                        if instruction['delay'] + stamp <= time.time():
                            instruction.pop('delay')
                            to_append.append(instruction)
                            j_to_remove.append(j)
                        j += 1
                    
                    j_to_remove.sort()
                    j_to_remove.reverse()
                    for j in j_to_remove:
                        delayed_instructions[item.attributes.ticket].pop(j)
                
                for instruction in data + to_append:
                    if 'delay' in instruction:
                        if item.attributes.ticket in delayed_instructions:
                            delayed_instructions[item.attributes.ticket].append([instruction, time.time()])
                        else:
                            delayed_instructions[item.attributes.ticket] = [[instruction, time.time()]]
                    else:
                        data_to_send.append(instruction)
                        
                        if i not in to_remove and instruction['type'] == 'remove':
                            to_remove.append(i)
                    
                i += 1
			
            to_remove.sort()
            to_remove.reverse()
            for i in to_remove:
                self.serverdata.item_objects.pop(i)
            
            for client in self.clients:
                client.push_item_states(data_to_send)
                client.push_positions()
            
            time.sleep(max([0, self.serverdata.looptime - (time.time() - start)])) #prevent server from running too quickly
    
    def distance_to_point(self, x0, y0, x1, y1):
        return math.hypot(x1 - x0, y1 - y0)
    
    def send_text(self, path, formats = None, connection = None, category = 'general'):
        string = self.settingsdata['messages']
        for item in path:
            string = string[item]
        
        if type(string) == list:
            string = random.choice(list)
        
        if not type(string) == str:
            raise ValueError('Invalid string path {} - doesn\'t give a string'.format(path))
        
        if formats is not None:
            string = string.format(*formats)
        
        if path[0] == 'fullscreen':
            req = Request(command = 'popmsg', subcommand = 'welcome', arguments = {'text': string})
        elif path[0] == 'chat':
            req = Request(command = 'say', subcommand = category, arguments = {'text': string, 'category': category})
        else:
            raise ValueError('Invalid text mode "{}"'.format(path[0]))
        
        if connection is None:
            self.send_all(req)
        else:
            self.send(connection, req)
    
    def set_gamemode(self, gamemode, force = False):
        if gamemode in self.serverdata.mapdata['gamemode']['supported']:
            if self.serverdata.gamemode == gamemode and not force:
                return 2
            self.serverdata.gamemode = gamemode
            self.respawn_all()
            self.set_scoreline(0, 0)
            self.send_text(['fullscreen', 'gamemode change'], formats = [['PvP arena',
                                                                          'deathmatch',
                                                                          'team deathmatch',
                                                                          'PvE survival'][self.serverdata.gamemode]],
                           category = 'gamemode change')
        else:
            return 0
        return 1

    def respawn_all(self):
        for client in self.clients:
            if client.metadata.active:
                client.respawn()
                
        self.serverdata.round_in_progress = True
        self.serverdata.round_start_time = time.time()
    
    def set_scoreline(self, score0 = None, score1 = None):
        if score0 is None:
            score0 = self.serverdata.scoreline[0]
        if score1 is None:
            score1 = self.serverdata.scoreline[1]
        
        self.serverdata.scoreline = [score0, score1]
        self.send_all(Request(command = 'var update w', subcommand = 'scoreline', arguments = {'scores': self.serverdata.scoreline}))
        self.output_pipe.send('Scoreline is now {} - {}'.format(score0, score1))
    
    def increment_scoreline(self, score0 = None, score1 = None):
        if score0 is not None:
            score0 += self.serverdata.scoreline[0]
        if score1 is not None:
            score1 += self.serverdata.scoreline[1]
        self.set_scoreline(score0, score1)
        
    def round_ended(self, winner = None):
        self.serverdata.round_in_progress = False
        
        for client in self.clients:
            if client.metadata.active:
                self.database.add_user(client.metadata.username) #make sure the user is in the database first
                
                if winner is None or not client.metadata.team_id == winner:
                    self.database.increment_user(client.metadata.username, losses = 1)
                else:
                    self.database.increment_user(client.metadata.username, wins = 1)
        
        if self.serverdata.gamemode == 0:
            self.xvx_round_ended(winner = winner)
        
        elif self.serverdata.gamemode == 1:
            time.sleep(self.settingsdata['player']['gamemodes']['deathmatch']['after game time'])
            self.respawn_all()
        
        elif self.serverdata.gamemode == 2:
            time.sleep(self.settingsdata['player']['gamemodes']['team deathmatch']['after game time'])
            self.respawn_all()
        
        elif self.serverdata.gamemode == 3:
            time.sleep(self.settingsdata['player']['gamemodes']['pve survival']['after game time'])
            self.respawn_all()
        
    def num_alive(self):
        count = [0, 0]
        for client in self.clients:
            if client.metadata.active and client.metadata.mode == 'player' and client.metadata.health > 0:
                count[client.metadata.team_id] += 1
        return count
    
    def xvx_round_ended(self, winner):
        threading.Thread(target = self._xvx_round_ended, args = [winner]).start()
    
    def _xvx_round_ended(self, winner):
        self.serverdata.round_in_progress = False
        
        if winner == 0 and self.serverdata.scoreline[0] + 1 == self.settingsdata['player']['gamemodes']['xvx']['min rounds']:
            self.xvx_game_won(0)
            
        elif winner == 1 and self.serverdata.scoreline[1] + 1 == self.settingsdata['player']['gamemodes']['xvx']['min rounds']:
            self.xvx_game_won(1)
            
        else:
            if winner == 0:
                self.increment_scoreline(score0 = 1)
                self.output_pipe.send('Team 1 won the round')
                self.send_text(['fullscreen', 'xvx', 'round won'], ["1"], category = 'round end')
                
            elif winner == 1:
                self.increment_scoreline(score1 = 1)
                self.output_pipe.send('Team 2 won the round')
                self.send_text(['fullscreen', 'xvx', 'round won'], ["2"], category = 'round end')
            
            elif winner is None:
                self.output_pipe.send('Both teams ran out of time')
                self.send_text(['fullscreen', 'xvx', 'round draw'], category = 'round end')
        
            time.sleep(self.settingsdata['player']['gamemodes']['xvx']['after round time'])
            self.respawn_all()
        
    def get_all_positions(self, omit):
        output = []
        for client in self.clients:
            if client.metadata.active and client.metadata.mode == 'player' and (client not in omit):
                d = {'x': client.metadata.pos.x,
                     'y': client.metadata.pos.y,
                     'rotation': client.metadata.pos.rotation,
                     'id': client.metadata.id}
                output.append(d)
        return output
    
    def xvx_game_won(self, winner):
        self.send_text(['fullscreen', 'xvx', 'game won'], formats = [winner + 1], category = 'game end')
        
        self.output_pipe.send('Team {} won the game'.format(winner + 1))
        
        threading.Thread(target = self._xvx_game_won, daemon = True).start()
    
    def _xvx_game_won(self):
        time.sleep(self.settingsdata['player']['gamemodes']['xvx']['after game time'])
        self.set_gamemode(0, force = True)
    
    def gamemode_text(self):
        return ['xvx', 'deathmatch', 'team deathmatch', 'pve survival'][self.serverdata.gamemode]
    
    def get_timeleft(self):
        if self.serverdata.round_in_progress:
            gamemode_data = self.settingsdata['player']['gamemodes'][self.gamemode_text()]
            if 'round time' in gamemode_data:
                return gamemode_data['round time'] + self.serverdata.round_start_time - time.time()
            else:
                return None
        else:
            return None
    
    def push_timeleftd(self):
        while self.serverdata.running:
            if self.serverdata.round_in_progress:
                tleft = self.get_timeleft()
                
                self.send_all(Request(command = 'var update w', subcommand = 'round time', arguments = {'value': tleft}))
                
                if tleft is None:
                    time.sleep(0.1)
                elif tleft <= 0:
                    self.send_all(Request(command = 'var update w', subcommand = 'round time', arguments = {'value': None}))
                    self.round_ended()
                else:
                    delay = tleft - math.floor(tleft)
                    if delay <= 0:
                        time.sleep(0.5)
                    else:
                        time.sleep(delay)
            else:
                time.sleep(0.1)


class Lobby:
    def __init__(self, server, log, frame = None):
        self.server = server
        self.log = log

        #define attribute structure
        class cfgs:
            server = {}
        self.cfgs = cfgs

        class items:
            objects = []
            dicts = {}
            scripts = {}
            ticket = 0
        self.items = items

        class current_round:
            start_time = None
            in_progress = False
        self.current_round = current_round

        class map:
            name = None
            data = None
            script_loader = None
        self.map = map

        self.clients = []

        self.team_sizes = [0, 0]

        self.gamemode = None
        self.scoreline = [0, 0]

        self._tickrate = 10
        self._looptime = 1 / self._tickrate
        self.tickrate = property(self._set_tickrate, self._get_tickrate)
        self.looptime = property(self._set_looptime, self._get_looptime)

        #load configs
        with open(os.path.join(sys.path[0], 'server', 'config.json'), 'r') as file:
            self.cfgs.server = json.load(file)

        #load components
        self.cmdline_pipe, pipe = mp.Pipe()
        self.cmdline = modules.servercmds.ServerCommandLineUI(self.handle_command, pipe, frame)

        #run autoexec
        for script_name in self.cfgs.server['scripts']['autoexec']:
            with open(os.path.join(sys.path[0], 'server', 'scripts', '{}.txt'.format(script_name)), 'r') as file:
                self.run_script(file.read(), show_output = True)
        
        #wait for a map to be loaded
        while self.map.data is None:
            time.sleep(0.01)
        
        self.round.start_time = time.time()
        self.round.in_progress = True

        #start threads
        threading.Thread(target = self._roundtimerd, name = 'Round timer daemon', daemon = True).start()
        threading.Thread(target = self._itemhandlerd, name = 'Item handler daemon', daemon = True).start()

        self.running = True
    
    def new_client(self, client):
        self.clients.append(client)

        client.metadata.heatlth = 100
        client.metadata.username = 'guest'
        client.metadata.team_id = self._generate_team_id()

        for script in self.cfgs.server['scripts']['userconnect']:
            with open(os.path.join(sys.path[0], 'server', 'scripts', '{}.txt'.format(script)), 'r') as file:
                self.run_script(file.read())

        client.interface.start()
    
    def _generate_team_id(self):
        if self.team_sizes[0] > self.team_sizes[1]:
            team_id = 1
        else:
            team_id = 0

        self.team_sizes[team_id] += 1

        return team_id
    
    def send_all(self, req):
        for client in self.clients:
            client.send(req)
    
    def run_script(self, text, show_output = True):
        for line in text.split('\n'):
            output = self.handle_command(line)
            
            if show_output:
                for s in output:
                    self.console_output(s)
    
    def handle_command(self, command):
        operation = command.split(' ')[0]
        argument = command[len(operation) + 1:]

        self.log.add('command input', command)
        
        output = []
        if operation == 'help':
            output.append('''Commands:
map: load a map by name
exec: execute a script by name stored in the server/scripts directory
echo: output the text given to the console
clear: clear the console
close_window: close the console

say: send a message to all players
say_pop: send a fullscreen message to all players

mp_:
mp_gamemode: set the gamemode
mp_respawn_all: respawn all players
mp_scoreline_team1: set the scoreline of team 1
mp_scoreline_team2: set the scoreline of team 2

sv_:
sv_conns: list of connections to the server
sv_kick_addr: kick a player by address
sv_quit: destroy the server
sv_hitbox: choose whether or not to use accurate hitboxes

db_:
db_commit: push all database changes to the disk
db_reset: resets the database''')
        
        elif operation == 'map':
            try:
                self.load_map(argument)
                output.append('Loading map \'{}\'...'.format(argument))
            
            except ValueError:
                type, value, traceback = sys.exc_info()
                output.append('Error while loading map \'{}\'\nERROR: {}\n{}'.format(argument, type, value))
        
        elif operation == 'exec':
            with open(os.path.join(sys.path[0], 'server', 'scripts', '{}.txt'.format(argument)), 'r') as file:
                self.run_script(file.read())
        
        elif operation == 'echo':
            output.append(argument)
        
        elif operation == 'clear':
            output.append('$$clear$$')
        
        elif operation == 'close_window':
            output.append('$$close_window$$')
        
        elif operation == 'say':
            self.send_all(Request(command = 'say', arguments = {'text': argument}))
            output.append('Said \'{}\' to all users'.format(argument))
        
        elif operation == 'say_pop':
            self.send_all(Request(command = 'popmsg', subcommand = 'general', arguments = {'text': argument}))
            output.append('Said \'{}\' to all users with a fullscreen message'.format(argument))
        
        elif operation == 'mp_gamemode':
            if argument == '':
                output.append('''Options:
0: xvx arena
1: deathmatch
2: team deathmatch
3: pve survival''')

            elif not argument.isdigit():
                output.append('Must be an integer between 0 and 3')
            
            else:
                output.append('Gamemode not supported by this map', 'Gamemode changed successfully', 'This is already the gamemode - no action taken'][self.set_gamemode(int(argument))])
        
        elif operation == 'mp_respawn_all':
            self.respawn_all()
        
        elif operation == 'mp_scoreline_team1':
            if argument == '':
                output.append('SCoreline for team 1: {}'.format(self.scoreline[0])
            
            elif not argument.isdigit():
                output.append('Must be a non-zero integer')
            
            elif int(argument) < 0:
                output.append('Must be a non-zero integer')
            
            else:
                self.set_scoreline(score0 = int(argument))
        
        elif operation == 'mp_scoreline_team2':
            if argument == '':
                output.append('SCoreline for team 2: {}'.format(self.scoreline[0])
            
            elif not argument.isdigit():
                output.append('Must be a non-zero integer')
            
            elif int(argument) < 0:
                output.append('Must be a non-zero integer')
            
            else:
                self.set_scoreline(score1 = int(argument))
        
        elif operation == 'sv_kick_addr':
            try:
                self.server.kick_address(argument)
                output.append('Kicked connections via {}'.format(argument))
            
            except ValueError:
                output.append('Error while kicking all connections via {}'.format(argument))
        
        elif operation == 'sv_quit':
            self.quit()
        
        elif operation == 'sv_hitbox':
            try:
                for client in self.server.clients:
                    client.set_hitboxes(argument)
            except ValueError:
                output = 'Error while setting hitboxes to \'{}\''.format(argstring)

        elif operation == 'db_commit': #underlying process should happen anyway
            self.server.database.commit()
            output.append('Changes to database committed')
        
        elif operation == 'db_reset':
            self.server.database.reset()
    
    def load_map(self, map_name):
        self.map.name = map_name

        with open(os,path.join(sys.path[0], 'server', 'maps', self.map.name, 'list.json'), 'r') as file:
            self.map.data = json.load(file)
        
        self.set_gamemode(self.map.data['gamemode']['default'])

        for client in self.clients:
            if client.metadata.active:
                client.write_var('map', {'map': self.map.name})
                client.write_var('team', client.metadata.team_id)
                client.give(self.serverdata.mapdata['player']['starting items'][client.metadata.team_id])
                client.metadata.model = random.choice(self.map.data['entity models']['player'])

        self.items.dicts = {}
        for item_name in os.listdir(os.path.join(sys.path[0], 'server', 'maps', self.map.name, 'items')):
            if item_name.endswith('.json'):
                with open(os.path.join(sys.path[0], 'server', 'maps', self.map.name, 'items', item_name), 'r') as file:
                    self.items.dicts[item_name] = json.load(file)
        
        self.map.script_loader = modules.modloader.ModLoader(os.path.join(sys.path[0], 'server', 'maps', self.serverdata.map, 'items'))

        scripts = self.modloader.load('ItemScript')
        self.items.scripts = {}
        for script_obj in scripts:
            self.items.scripts[script_obj.internal_name] = script_obj
    
    def console_output(self, s):
        self.cmdline_pipe.send(s)
    
    def _itemhandlerd(self):
        delayed_handles = {}
        
        while self.running:
            loop_start = time.time()

            ####
            items_to_remove = [] #can't change length during iteration, have to use this ugly workaround
            item_states = []
            i = 0

            for item in self.items.objects:
                item_handle = item.tick()

                #look for instructions that have been delayed
                if item.attributes.ticket in delayed_handles:
                    instructions_to_remove = [] #can't change length during iteration, have to use this ugly workaround
                    j = 0
                    for instruction, stamp in delayed_handles[item.attributes.ticket]:
                        if instruction['delay'] + stamp <= time.time():
                            instruction.pop('delay')
                            item_handle.append(instruction)
                            instructions_to_remove.append(j)
                        j += 1
                    
                    instructions_to_remove.sort()
                    instructions_to_remove.reverse()
                    for j in instructions_to_remove:
                        delayed_handles[item.attributes.ticket].pop(j)
                
                #look for instructions from this item relevant to this thread
                for instruction in item_handle:
                    if 'delay' in instruction:
                        if item.attributes.ticket in delayed_handles:
                            delayed_handles[item.attributes.ticket].append([instruction, time.time()])
                        
                        else:
                            delayed_handles[item.attributes.ticket] = [[instruction, time.time()]]
                    
                    else:
                        item_states.append(instruction)

                        if i not in items_to_remove and instruction['type'] == 'remove':
                            items_to_remove.append(i)
                
                i += 1
            
            #remove deleted items
            items_to_remove.sort()
            items_to_remove.reverse()
            for i in items_to_remove:
                self.items.objects[i].destroy()
                self.items.objects.pop(i)
            
            #push new item states to clients
            for client in self.clients:
                client.push_item_states(item_states)
                client.push_positions()

            ####

            time.sleep(max([0, self.looptime - time.time() + loop_start])) #make sure the loop is running at a constant speed
    
    def close(self):
        self.running = False
    
    #properties
    def _set_tickrate(self, value):
        if value <= 0:
            raise ValueError('Tickrate must be a positive float')
        
        else:
            self._tickrate = value
            self._looptime = 1 / value
    
    def _get_tickrate(self):
        return self._tickrate
    
    def _set_looptime(self, value):
        if value <= 0:
            raise ValueError('Looptime must be a positive float')
        
        else:
            self._looptime = value
            self._tickrate = 1 / value
    
    def _get_looptime(self):
        return self._looptime
        

class Request:
    def __init__(self, data = None, **args):
        self.command = None
        self.subcommand = None
        self.arguments = {}
        
        #priorities data from the data variable over the flags
        if data is None:
            if args == {}:
                raise ValueError('Some arguments must be provided - one of args or data must be specified')
            else:
                self.dict_in(args)
        else:
            if type(data) == str:
                self.json_in(data)
                
            elif type(data) == dict:
                self.dict_in(data)
                
            else:
                raise TypeError('Data must be dict or str, not {} (value = {})'.format(type(data).__name__, data))
    
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
            self.command = None
            
        if 'subcommand' in data:
            self.subcommand = data['subcommand']
        else:
            self.subcommand = None
            
        if 'arguments' in data:
            self.arguments = data['arguments']
        else:
            self.arguments = {}
        
    def _clear_all_values(self):
        self.request_id = None
        self.response_id = None
    
    def pretty_print(self):
        return '<{}> - {} {}'.format(self.command, self.subcommand, self.arguments)