import tkinter as tk
import sqlite3 as sql
import multiprocessing as mp
import time
import threading
import os
import sys
import json
import random
import math
import importlib.util

import modules.networking
import modules.logging

class Game:
    def __init__(self, canvas, client):
        self.canvas = canvas
        self.client = client
        
        class server:
            mode = 'internal' #either 'internal' or 'external'
            allow_external = True
            name = 'localhost'
        self.server = server
        
        self.log = modules.logging.Log(os.path.join(sys.path[0], 'server', 'logs', 'game.txt'))
        
        self.vars = {}
        
        with open(os.path.join(sys.path[0], 'user', 'config.json'), 'r') as file:
            self.settingsdict = json.load(file)
        
        self.canvcont = CanvasController(self.canvas, self)
        
        self.message_pipe, pipe = mp.Pipe()
        self.messagedisplay = CanvasMessages(self.canvcont, pipe)
        self.messagedisplay.graphical_properties.font = (self.settingsdict['hud']['chat']['font'], self.settingsdict['hud']['chat']['fontsize'])
        self.messagedisplay.graphical_properties.maxlen = self.settingsdict['hud']['chat']['maxlen']
        self.messagedisplay.graphical_properties.persist = self.settingsdict['hud']['chat']['persist time']
        self.messagedisplay.graphical_properties.height = self.settingsdict['hud']['chat']['spacing']
        self.messagedisplay.graphical_properties.colour = self.settingsdict['hud']['chat']['colour']
        self.messagedisplay.graphical_properties.alignment = ['tl', 'tr', 'bl', 'br'][self.settingsdict['hud']['chat']['position']]
        self.messagedisplay.graphical_properties.is_ready = True
        
        self.popmsg = PopMessage(self.canvcont)
        self.popmsg.graphical_properties.font = self.settingsdict['hud']['popmsg']['font']
        self.popmsg.graphical_properties.colour = self.settingsdict['hud']['popmsg']['colour']
        
        self.engine = Engine(self)

        # display IP
        self.message_pipe.send(['info', 'Connected to {}:{}'.format(self.client.serverdata.host, self.client.serverdata.port)])
        
        self.client.recv_binds.append(self.recv_handler)
        self.client.send(modules.networking.Request(command = 'var update r', subcommand = 'map'))
        
        self.running = True
        threading.Thread(target = self.main, daemon = True).start()
        
        #make canvas take focus when the mouse enters, and lose it when it leaves
        self.canvas.bind('<Enter>', lambda event: self.canvas.focus_set())
        self.canvas.bind('<Leave>', lambda event: self.canvas.nametowidget('.').focus_set())
    
    def main(self):
        while self.running:
            time.sleep(0.05)
            if not self.engine.map.player == None:
                self.client.send(modules.networking.Request(command = 'var update w', subcommand = 'position', arguments = {'x': self.engine.map.player.pos.x, 'y': self.engine.map.player.pos.y, 'rotation': self.engine.map.player.pos.rotation}))
            self.client.send(modules.networking.Request(command = 'var update r', subcommand = 'all player positions'))
    
    def close(self):
        self.running = False
        self.client.disconnect()
        self.engine.keybindhandler.kill()
        self.engine.unload_current_map()
    
    def recv_handler(self, request):
        try:
            data = request.as_dict()
            self.log.add('received', 'Data received from the server - {}'.format(request.pretty_print()))
        except json.decoder.JSONDecoderError:
            self.log.add('error', 'Error while reading JSON "{}"'.format(data))
        
        if request.command == 'say':
            if 'category' in request.arguments:
                self.message_pipe.send([request.arguments['category'], request.arguments['text']])
            else:
                self.message_pipe.send(['chat', request.arguments['text']])
        elif request.command == 'disconnect':
            if self.running == True:
                print('Connection to server interrupted')
        elif request.command == 'var update w':
            if request.subcommand == 'map':
                if not self.engine.map.name == request.arguments['map name']:
                    self.engine.load_map(request.arguments['map name'])
                self.vars[request.subcommand] = request.arguments['map name']
            elif request.subcommand == 'player positions':
                positions = request.arguments['positions']
                if not len(positions) == len(self.engine.map.other_players.entities):
                    new_ent_list = self.engine.map.other_players.entities[:len(positions)]
                    excess_ents = self.engine.map.other_players.entities[len(positions):]
                    for entity in excess_ents:
                        entity.model.destroy()
                    if len(new_ent_list) < len(positions):
                        for i in range(len(positions) - len(new_ent_list)):
                            new_ent_list.append(Entity(random.choice(self.engine.map.cfg['entity models'][self.engine.map.cfg['player']['entity']]), self.engine.map.path, self.engine, 'player models', is_player = False))
                        self.engine.map.other_players.entities = new_ent_list
                
                for index in range(len(positions)):
                    self.engine.map.other_players.entities[index].setpos(positions[index]['x'], positions[index]['y'], positions[index]['rotation'])
            elif request.subcommand == 'team':
                self.vars['team'] = request.arguments['value']
            elif request.subcommand == 'client position':
                self.engine.map.player.setpos(request.arguments['x'], request.arguments['y'], request.arguments['rotation'])
            elif request.subcommand == 'health':
                self.engine.map.player.set_health(request.arguments['value'])
            else:
                self.vars[request.subcommand] = request.arguments['value']
        elif request.command == 'give':
            for item in request.arguments['items']:
                i = 0
                while self.engine.map.invdisp.inv_items[i]['quantity'] != 0:
                    i += 1
                self.engine.map.invdisp.set_slot(i, item['item'], item['quantity'])
        elif request.command == 'var update r':
            if request.subcommand == 'username':
                self.client.send(modules.networking.Request(command = 'var update w', subcommand = 'username', arguments = {'value': self.settingsdict['user']['name']}))
        
        elif request.command == 'update items':
            if request.subcommand == 'server tick':
                updates = request.arguments['pushed']
                for data in updates:
                    if data['type'] == 'add': #item has just been created
                        entity = Entity(data['data']['model'], os.path.join(sys.path[0], 'server', 'maps', self.engine.map.name), self.engine, 'items')
                        entity.setpos(x = data['position'][0], y = data['position'][1], rotation = data['rotation'])
                        self.engine.map.items.append({'ticket': data['ticket'],
                                                      'object': entity})
                        
                    elif data['type'] == 'remove':
                        to_remove = []
                        for i in self.engine.map.items:
                            if i['ticket'] == data['ticket']:
                                to_remove.append(i)
                                
                        for i in to_remove:
                            i['object'].destroy()
                            self.engine.map.items.remove(i)
                    
                    elif data['type'] == 'update position':
                        to_update = []
                        for i in self.engine.map.items:
                            if i['ticket'] == data['ticket']:
                                to_update.append(i)
                                
                        for i in to_update:
                            if 'position' in data:
                                i['object'].setpos(x = data['position'][0], y = data['position'][1])
                            if 'rotation' in data:
                                i['object'].setpos(rotation = data['rotation'])
        
        elif request.command == 'popmsg':
            if request.subcommand == 'general':
                self.popmsg.queue_message(request.arguments['text'], 2)
            elif request.subcommand == 'welcome':
                self.popmsg.queue_message(request.arguments['text'], 4)
        
        elif request.command == 'event':
            if request.subcommand == 'death':
                if request.arguments['username'] == self.engine.map.settingscfg['user']['name']:
                    pass
        
        elif request.command == 'set mode':
            if request.subcommand == 'spectator':
                if not self.engine.map.player == None or not self.engine.map.player.running:
                    self.engine.map.player.destroy()
            elif request.subcommand == 'player':
                if not self.engine.map.player.running:
                    self.engine.map.player = Entity(random.choice(self.map.cfg['entity models'][self.map.cfg['player']['entity']]), self.engine.map.path, self.engine, 'player models', is_player = True)
                self.engine.map.player.setpos(400, 300, 0)

class Engine:
    def __init__(self, game):
        self.game = game
        
        class map:
            class textures:
                base = None
                overlay = None
                
                obj_base = None
                obj_overlay = None
                obj_scatter = []
                
                event_overlays = {}
                event_overlays_models = {}
            class layout:
                data = {}
            class materials:
                data = {}
                textures = {}
                scripts = {}
            class other_players:
                entities = []
            name = None
            cfg = {}
            rendermethod = None
            player = None
            healthbar = None
            invdisp = None
            items = []
            pulse_in_progress = False
            settingscfg = None
        self.map = map
        
        #make keybind handler
        self.keybindhandler = KeyBind(self.game.canvas)
    
    def load_map(self, name):
        self.map.path = os.path.join(sys.path[0], 'server', 'maps', name)
        if os.path.isdir(self.map.path):
            self.game.message_pipe.send(['map load', 'Loading map "{}"'.format(name)])
            
            #check user cfg
            with open(os.path.join(sys.path[0], 'user', 'config.json'), 'r') as file:
                self.map.settingscfg = json.load(file)
            
            #use correct rendering method
            if self.map.settingscfg['graphics']['PILrender']:
                self.map.rendermethod = __import__('PIL.ImageTk').ImageTk.PhotoImage
                self.game.message_pipe.send(['map load', 'Loaded PIL image renderer'])
            else:
                self.map.rendermethod = tk.PhotoImage
                self.game.message_pipe.send(['map load', 'Loaded internal image renderer'])
        
            #delete old scatters, background and overlays
            self.unload_current_map()
            
            #open map cfg
            self.map.name = name
            with open(os.path.join(self.map.path, 'list.json'), 'r') as file:
                self.map.cfg = json.load(file)
            self.game.message_pipe.send(['map load', 'Loaded map cfg'])
            
            #load base and overlay into memory
            self.map.textures.base = self.map.rendermethod(file = os.path.join(self.map.path, self.map.cfg['background']['base']))
            self.game.message_pipe.send(['map load', 'Loaded base texture'])
            self.map.textures.overlay = self.map.rendermethod(file = os.path.join(self.map.path, self.map.cfg['background']['overlay']))
            self.game.message_pipe.send(['map load', 'Loaded overlay texture'])
            
            #render base layer
            self.map.textures.obj_base = self.game.canvcont.create_image(402, 302, image = self.map.textures.base, layer = 'base texture')
            self.game.message_pipe.send(['map load', 'Rendered base texture'])
            
            #load event textures into memory
            self.map.textures.event_overlays['damage'] = Model(self.map.settingscfg['hud']['overlays']['damage'], self.map.path, self.map.rendermethod, self.game.canvcont, 'event overlays')
            self.map.textures.event_overlays['damage'].setpos(402, 302, 0, 0)
            
            #open layout
            with open(os.path.join(self.map.path, 'layout.json'), 'r') as file:
                self.map.layout.data = json.load(file)
            self.game.message_pipe.send(['map load', 'Loaded layout data'])
            
            #load textures
            for texture_name in os.listdir(os.path.join(self.map.path, 'textures')):
                if texture_name.endswith('.png'):
                    self.map.materials.textures[texture_name] = self.map.rendermethod(file = os.path.join(self.map.path, 'textures', texture_name))
            self.game.message_pipe.send(['map load', 'Loaded material textures'])
            
            #load scripts
            self.map.materials.scripts = {}
            for script in os.listdir(os.path.join(self.map.path, 'scripts')):
                if not (script.startswith('.') or script.startswith('_')):
                    spec = importlib.util.spec_from_file_location('matscript', os.path.join(self.map.path, 'scripts', script))
                    script_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(script_module)
                    self.map.materials.scripts[script] = script_module.Script
            
            #render layout panels and give them their scripts
            for panel in self.map.layout.data['geometry']:
                with open(os.path.join(self.map.path, 'materials', panel['material']), 'r') as file:
                    panel['material data'] = json.load(file)
                panel['img obj'] = self.game.canvcont.create_image(panel['coordinates'][0], panel['coordinates'][1], image = self.map.materials.textures[panel['material data']['texture']['address']], layer = 'map panels')
                panel['scriptmodules'] = []
                if 'scripts' in panel['material data']:
                    for script in panel['material data']['scripts']:
                        panel['scriptmodules'].append(self.map.materials.scripts[script](panel))
                if 'scripts' in panel:
                    for script in panel['scripts']:
                        panel['scriptmodules'].append(self.map.materials.scripts[script](panel))
                
            self.game.message_pipe.send(['map load', 'Rendered layout panels'])
            
            #render scatters
            self.map.textures.obj_scatter = []
            for i in range(int(self.map.cfg['background']['scatternum'] / len(self.map.cfg['background']['scatters']))):
                for scatter in self.map.cfg['background']['scatters']:
                    scattermdl = Model(random.choice(self.map.cfg['entity models'][scatter]), self.map.path, self.map.rendermethod, self.game.canvcont, 'scatters')
                    scattermdl.setpos(random.randint(0, 800), random.randint(0, 600))
                    self.map.textures.obj_scatter.append(scattermdl)
            self.game.message_pipe.send(['map load', 'Loaded scatters'])
            
            #load player
            self.game.message_pipe.send(['map load', 'Creating player model...'])
            self.map.player = Entity(random.choice(self.map.cfg['entity models'][self.map.cfg['player']['entity']]), self.map.path, self, 'player models', is_player = True)
            self.game.message_pipe.send(['map load', 'Loaded player model'])
            self.map.player.setpos(400, 300, 0)
            
            #render overlay
            self.map.textures.obj_overlay = self.game.canvcont.create_image(402, 302, image = self.map.textures.overlay, layer = 'overlay')
            self.game.message_pipe.send(['map load', 'Rendered overlay'])
            
            #make healthbar
            self.map.healthbar = DisplayBar(self.game.canvcont, 0, 100, [10, 10, 100, 20], 'gray', 'red')
            self.map.healthbar.set_value(100)
            
            #make inventory display
            self.map.invdisp = InventoryBar(self.game.canvcont, [400, 550], os.path.join(self.map.path, 'textures'), os.path.join(self.map.path, 'items'), self.map.rendermethod)
            self.map.invdisp.select_index(0)
            
            #set up binds for inventory display
            with open(os.path.join(sys.path[0], 'user', 'keybinds.json'), 'r') as file:
                keybinds_data = json.load(file)
            self.keybindhandler.bind(keybinds_data['inventory']['slot0'], lambda: self.map.invdisp.select_index(0))
            self.keybindhandler.bind(keybinds_data['inventory']['slot1'], lambda: self.map.invdisp.select_index(1))
            self.keybindhandler.bind(keybinds_data['inventory']['slot2'], lambda: self.map.invdisp.select_index(2))
            self.keybindhandler.bind(keybinds_data['inventory']['slot3'], lambda: self.map.invdisp.select_index(3))
            self.keybindhandler.bind(keybinds_data['inventory']['slot4'], lambda: self.map.invdisp.select_index(4))
            self.keybindhandler.bind(keybinds_data['inventory']['use'], self.use_current_item)
            
            #set values for health bar and inventory bar
            self.map.healthbar.set_value(100)
            self.map.invdisp.select_index(0)
            
            #tell the server that the player has loaded in
            self.game.client.send(modules.networking.Request(command = 'map loaded'))
    
    def unload_current_map(self):
        if not self.map.textures.obj_scatter == []:
            for scatter in self.map.textures.obj_scatter:
                scatter.destroy()
            self.map.textures.obj_scatter = []
        if not self.map.textures.obj_base == None:
            self.game.canvcont.delete(self.map.textures.obj_base)
            self.map.textures.obj_base = None
        if not self.map.textures.obj_overlay == None:
            self.game.canvcont.delete(self.map.textures.obj_overlay)
            self.map.textures.obj_overlay = None
        if not self.map.player == None:
            self.map.player.model.destroy()
        if not self.map.healthbar == None:
            self.map.healthbar.destroy()
        if not self.map.invdisp == None:
            self.map.invdisp.destroy()
        for item in self.map.items:
            item['object'].destroy()
        self.game.message_pipe.send(['map load', 'Cleared old map assets'])
        
        self.keybindhandler.unbind_all()
    
    def find_materials_underneath(self, x, y):
        output = []
        for panel in self.map.layout.data['geometry']:
            relative_coords = [x - panel['coordinates'][0], y - panel['coordinates'][1]]
            mat_data = panel['material data']
            hitbox = mat_data['hitbox']
            if self.is_inside_hitbox(relative_coords[0], relative_coords[1], hitbox):
                output.append([panel, mat_data])
        return output
    
    def is_inside_hitbox(self, x, y, hitbox):
        nhitbox = []
        for hx, hy in hitbox:
            nhitbox.append([hx - x, hy - y])
        return self.origin_is_inside_hitbox(nhitbox)
    
    def origin_is_inside_hitbox(self, hitbox):
        'Find if (0, 0) is inside a hitbox (an ngon made up of pairs of values)'
        has_smaller = False
        has_bigger = False
        for hx, hy in hitbox:
            if hx > 0 and hy > 0:
                has_bigger = True
            if hx < 0 and hy < 0:
                has_smaller = True
        return has_smaller and has_bigger
    
    def use_current_item(self):
        if not self.map.invdisp.get_slot_info(self.map.invdisp.selection_index)['quantity'] == 0:
            self.game.client.send(modules.networking.Request(command = 'use', subcommand = 'client item', arguments = {'item': self.map.invdisp.get_slot_info(self.map.invdisp.selection_index)['file name'],
                                'rotation': self.map.player.angle_to_pos(self.game.canvas.winfo_pointerx() - self.game.canvas.winfo_rootx(), self.game.canvas.winfo_pointery() - self.game.canvas.winfo_rooty()),
                                'position': [self.map.player.pos.x, self.map.player.pos.y]}))
            if not self.map.invdisp.get_slot_info(self.map.invdisp.selection_index)['unlimited']:
                self.map.invdisp.increment_slot(self.map.invdisp.selection_index, -1)
    
    def pulse_item_transparency(self, model, timescale = 0.2):
        if not self.map.pulse_in_progress:
            self.map.pulse_in_progress = True
            threading.Thread(target = self._pulse_item_transparency, args = [model, timescale], name = 'Item transparency pulse').start()
    
    def _pulse_item_transparency(self, model, timescale):
        i = 0
        upstroke = True
        increment = 64
        delay = timescale * (increment / 256)
        
        while upstroke or not i <= 0:
            start = time.time()
            
            if upstroke:
                i += increment
                model.setpos(transparency = min(255, i))
                if i >= 256: 
                    upstroke = False
            else:
                i -= increment
                model.setpos(transparency = min(255, i))
                
            time.sleep(max(0, delay - (time.time() - start)))
            
        model.setpos(transparency = 0)
        self.map.pulse_in_progress = False

class Entity:
    def __init__(self, ent_name, map_path, engine, layer, is_player = False):
        self.ent_name = ent_name
        self.engine = engine
        self.map_path = map_path
        self.is_player = is_player
        self.layer = layer
        
        self.running = True
        self.health = None
        
        class pos:
            x = 0
            y = 0
            rotation = 0
            class momentum: #doesn't do anything when not player
                base_increment = 1
                xmomentum = 0
                ymomentum = 0
                delay = 0.05
            class strafemove: #doesn't do anything when not player
                mult = 1.5
                increment = 0.05
                current_strafe = None
                current_mult = 1
            script_delay = 0.05
        self.pos = pos
        
        self.set_health(100)
        
        self.setpos_queue, pipe = mp.Pipe()
        
        self.model = Model(self.ent_name, self.map_path, self.engine.map.rendermethod, self.engine.game.canvcont, self.layer)
        
        threading.Thread(target = self._setpos_queue, name = 'Entity setpos queue', args = [pipe]).start()
        
        if self.is_player: #only the player has momentum calculations applied using the keyboard
            threading.Thread(target = self._momentum_updater, name = 'Player momentum updating thread').start()
        threading.Thread(target = self.script_bind_handler, name = 'Entity script handler thread').start()
        
        self.setpos(100, 100)
    
    def setpos(self, x = None, y = None, rotation = None):
        self.setpos_queue.send([time.time(), x, y, rotation])
        
    def _setpos_queue(self, pipe):
        while True:
            timestamp, x, y, rotation = pipe.recv()
            if time.time() - timestamp < 1: #block older inputs
                event = threading.Event()
                event.clear()
                threading.Thread(target = self._setpos, args = [event, x, y, rotation]).start()
                event.wait()
    
    def _setpos(self, event, x = None, y = None, rotation = None):
        if not x == None:
            self.pos.x = x
        if not y == None:
            self.pos.y = y
        if not rotation == None:
            self.pos.rotation = rotation % 360
        self.model.setpos(self.pos.x, self.pos.y, self.pos.rotation)
            
        event.set()
    
    def _momentum_updater(self):
        with open(os.path.join(sys.path[0], 'user', 'keybinds.json'), 'r') as file:
            keybind_data = json.load(file)
        
        while self.running:
            time.sleep(self.pos.momentum.delay)
            
            accel = 0
            decel = 0
            velcap = 0
            damage = 0
            data = self.engine.find_materials_underneath(self.pos.x, self.pos.y)
            for panel, material in data:
                if material['entities'][self.ent_name]['accelerate'] != None:
                    accel = max(accel, material['entities'][self.ent_name]['accelerate'])
                if material['entities'][self.ent_name]['decelerate'] != None:
                    decel += material['entities'][self.ent_name]['decelerate']
                if material['entities'][self.ent_name]['velcap'] != None:
                    velcap = max(velcap, material['entities'][self.ent_name]['velcap'])
                if material['entities'][self.ent_name]['damage'] != None:
                    damage += material['entities'][self.ent_name]['damage']
            
            self.set_health(self.health - (damage * self.pos.momentum.delay))
            
            if self.is_player:
                if not accel == 0:
                    if self.engine.keybindhandler.get_state(keybind_data['movement']['up']):
                        self.pos.momentum.ymomentum -= accel
                    if self.engine.keybindhandler.get_state(keybind_data['movement']['down']):
                        self.pos.momentum.ymomentum += accel
                    if self.engine.keybindhandler.get_state(keybind_data['movement']['left']):
                        self.pos.momentum.xmomentum -= accel
                    if self.engine.keybindhandler.get_state(keybind_data['movement']['right']):
                        self.pos.momentum.xmomentum += accel
                
                if not decel == 0:
                    self.pos.momentum.xmomentum /= decel
                    self.pos.momentum.ymomentum /= decel
                
                #is adadadading (skill based movement)
                if self.engine.keybindhandler.get_state(keybind_data['movement']['up']) and self.engine.keybindhandler.get_state(keybind_data['movement']['left']):
                    current_strafe = 'ul'
                elif self.engine.keybindhandler.get_state(keybind_data['movement']['up']) and self.engine.keybindhandler.get_state(keybind_data['movement']['right']):
                    current_strafe = 'ur'
                elif self.engine.keybindhandler.get_state(keybind_data['movement']['down']) and self.engine.keybindhandler.get_state(keybind_data['movement']['left']):
                    current_strafe = 'dl'
                elif self.engine.keybindhandler.get_state(keybind_data['movement']['down']) and self.engine.keybindhandler.get_state(keybind_data['movement']['right']):
                    current_strafe = 'dr'
                else:
                    current_strafe = None
                
                if not current_strafe == None:
                    
                    if self.pos.strafemove.current_strafe == None or self.pos.strafemove.current_strafe != current_strafe:
                        self.pos.strafemove.current_mult = self.pos.strafemove.mult
                    else:
                        self.pos.strafemove.current_mult = max(self.pos.strafemove.current_mult - self.pos.strafemove.increment, 1)
                    
                    self.pos.strafemove.current_strafe = current_strafe
                    
                    self.pos.momentum.xmomentum *= self.pos.strafemove.current_mult
                    self.pos.momentum.ymomentum *= self.pos.strafemove.current_mult
                    
                else: #not doing any movement acceleration - apply speed cap
                    if self.pos.momentum.xmomentum > velcap:
                        self.pos.momentum.xmomentum = velcap
                    if self.pos.momentum.ymomentum > velcap:
                        self.pos.momentum.ymomentum = velcap
                
                self.pos.x += self.pos.momentum.xmomentum
                self.pos.y += self.pos.momentum.ymomentum
                
                self.setpos()
    
    def script_bind_handler(self):
        touching_last_loop = []
        while self.running:
            start = time.time()
        
            touching_this_loop = []
            data = self.engine.find_materials_underneath(self.pos.x, self.pos.y)
            for panel, material in data:
                touching_this_loop.append(panel)
                if not panel['scriptmodules'] == []:
                    for script in panel['scriptmodules']:
                        if 'when touching' in script.binds:
                            for func in script.binds['when touching']:
                                func(self)
                        if not panel in touching_last_loop:
                            if 'on enter' in script.binds:
                                for func in script.binds['on enter']:
                                    func(self)
            for panel in touching_last_loop:
                if not panel in touching_this_loop:
                    if not panel['scriptmodules'] == []:
                        for script in panel['scriptmodules']:
                            if 'on leave' in script.binds:
                                for func in script.binds['on leave']:
                                    func(self)
            touching_last_loop = touching_this_loop
            
            if self.pos.x < 0 or self.pos.x > self.engine.map.cfg['geometry'][0] or self.pos.y < 0 or self.pos.y > self.engine.map.cfg['geometry'][1]:
                if self.is_player:
                    if 'player' in self.engine.map.cfg['events']:
                        if 'outside map' in self.engine.map.cfg['events']['player']:
                            for path in self.engine.map.cfg['events']['player']['outside map']:
                                if path in self.engine.map.materials.scripts:
                                    for func in self.engine.map.materials.scripts[path](touching_last_loop).binds['player']['when outside map']:
                                        func(self)
                if 'outside map' in self.engine.map.cfg['events']:
                    for path in self.engine.map.cfg['events']['outside map']:
                        if path in self.engine.map.materials.scripts:
                            self.engine.map.materials.scripts[path](self)
            
            delay = self.pos.script_delay - (time.time() - start)
            if delay > 0:
                time.sleep(delay)
    
    def set_health(self, value):
        if (not self.health == None) and (not self.health == value) and self.is_player:
            self.engine.pulse_item_transparency(self.engine.map.textures.event_overlays['damage'])
    
        self.health = value
        if not self.engine.map.healthbar == None: #make sure healthbar has been created
            self.engine.map.healthbar.set_value(self.health)
        self.engine.game.client.send(modules.networking.Request(command = 'var update w', subcommand = 'health', arguments = {'value': self.health}))
    
    def angle_to_pos(self, x, y):
        dx = x - self.pos.x
        dy = y - self.pos.y
        
        if dx == 0:
            if dy > 0:
                return 270
            else:
                return 90
        elif dx < 0:
            return (math.degrees(math.atan(dy / dx)) + 180) % 360
        else:
            return math.degrees(math.atan(dy / dx)) % 360
    
    def destroy(self):
        self.model.destroy()
        self.running = False

class Model:
    def __init__(self, ent_name, map_path, imageloader, canvcont, layer):
        self.ent_name = ent_name
        self.map_path = map_path
        self.ent_path = os.path.join(self.map_path, 'models', self.ent_name)
        self.imageloader = imageloader
        self.canvcont = canvcont
        self.layer = layer
        self.transparency_precision = 1
        
        class graphics:
            x = 0
            y = 0
            rotation = 0
            prev_rotation = None
            displaytype = None
            preimgloader = None
            usesPIL = False
            transparency = 255
            prev_transparency = None
            PILImage = None
            PILImageChops = None
            class flat:
                texture = None
                textures = []
                imgobj = None
                canvobjs = []
            class stack:
                class offsets:
                    x = 0
                    y = 0
                textures = []
                imgobjs = []
                canvobjs = []
                numlayers = None
        self.graphics = graphics
        
        if not self.imageloader == tk.PhotoImage:
            self.graphics.PILImageChops = __import__('PIL.ImageChops').ImageChops
            self.graphics.PILImage = __import__('PIL.Image').Image
            self.preimgloader = self.graphics.PILImage.open
            
            self.graphics.usesPIL = True
        
        with open(os.path.join(self.ent_path, 'list.json'), 'r') as file:
            self.config = json.load(file)
        
        with open(os.path.join(sys.path[0], 'user', 'config.json'), 'r') as file:
            self.userconfig = json.load(file)
        
        if 'transparencies' in self.config:
            self.transparency_precision = self.config['transparencies'][self.userconfig['graphics']['stacked model quality']]
        
        #load textures
        self.graphics.displaytype = self.config['type']
        if self.graphics.displaytype == 'flat':
            self.graphics.flat.texture = self.preimgloader(os.path.join(self.ent_path, self.config['texture']))
        elif self.graphics.displaytype == 'stack':
            if type(self.config['textures']) == list:
                for img in self.config['textures']:
                    self.graphics.stack.textures.append(self.preimgloader(os.path.join(self.ent_path, img)))
            else:
                for img in os.listdir(os.path.join(self.ent_path, 'stack')):
                    self.graphics.stack.textures.append(self.preimgloader(os.path.join(self.ent_path, 'stack', img)))
            
            self.graphics.stack.numlayers = self.config['numlayers'][self.userconfig['graphics']['stacked model quality']]
            
            if self.graphics.stack.numlayers == len(self.graphics.stack.textures):
                self.graphics.stack.offsets.y = self.config['offsets'][1]
            else:
                self.graphics.stack.offsets.y = self.config['offsets'][1] * (len(self.graphics.stack.textures) / self.graphics.stack.numlayers)
            self.graphics.stack.offsets.x = self.config['offsets'][0]
        else:
            raise ValueError('Display type \'{}\' doesn\'t exist'.format(self.config['type']))
        self._render()
        
        self.setpos(x = self.config['offscreen'][0], y = self.config['offscreen'][1], transparency = 255, rotation = 0)
    
    def _render(self, x = None, y = None):
        if not x == None:
            self.graphics.x = x
        if not y == None:
            self.graphics.y = y

        self.create_rotations(self.config['rotations'][self.userconfig['graphics']['stacked model quality']])
    
    def setpos(self, x = None, y = None, rotation = None, transparency = None):
        if not x == None:
            self.graphics.x = x
        if not y == None:
            self.graphics.y = y
            
        if not transparency == None:
            self.graphics.prev_transparency = self.graphics.transparency
            self.graphics.transparency = transparency
            
        if not rotation == None:
            self.graphics.prev_rotation = self.graphics.rotation
            self.graphics.rotation = rotation
            
        if self.graphics.displaytype == 'flat':
            self.canvcont.coords(self.obj_from_angle(self.graphics.rotation, self.graphics.transparency), self.graphics.x, self.graphics.y)
            if self.graphics.prev_rotation != None and self.graphics.prev_transparency != None and (self.graphics.prev_rotation != self.graphics.rotation or self.graphics.prev_transparency != self.graphics.transparency):
                self.canvcont.coords(self.obj_from_angle(self.graphics.prev_rotation, self.graphics.prev_transparency), self.config['offscreen'][0], self.config['offscreen'][1])
                
        elif self.graphics.displaytype == 'stack':
            i = 0
            if not (self.graphics.prev_rotation == None or self.graphics.prev_rotation == self.graphics.rotation):
                for canvobj in self.objset_from_angle(self.graphics.prev_rotation):
                    self.canvcont.coords(canvobj, self.config['offscreen'][0], self.config['offscreen'][1])
            for canvobj in self.objset_from_angle(self.graphics.rotation):
                self.canvcont.coords(canvobj, self.graphics.x + (i * self.graphics.stack.offsets.x), self.graphics.y + (i * self.graphics.stack.offsets.y))
                i += 1
    
    def create_rotations(self, num_rotations):
        'Premake all canvas objects for different rotations to speed up rendering'
        if self.graphics.displaytype == 'stack':
            if self.graphics.stack.numlayers == len(self.graphics.stack.textures): #find out the indexes of the images to be used
                    iterator = range(len(self.graphics.stack.textures))
            else:
                iterator = []
                mult = len(self.graphics.stack.textures) / self.graphics.stack.numlayers
                for i in range(self.graphics.stack.numlayers):
                    iterator.append(int(i * mult))
            
            angle_increment = 360 / num_rotations
            i = 0
            for rot in range(num_rotations):
                #create sublists
                self.graphics.stack.canvobjs.append([])
                self.graphics.stack.imgobjs.append([])
                
                angle = angle_increment * rot #precalculate angle
                
                for tex in iterator:
                    if self.graphics.usesPIL:
                        loaded_image = self.imageloader(image = self.graphics.stack.textures[tex].rotate(angle))
                    else:
                        loaded_image = self.imageloader(image = self.graphics.stack.textures[tex])
                    new_canv_obj = self.canvcont.create_image(self.config['offscreen'][0], self.config['offscreen'][1], image = loaded_image, layer = self.layer)
                    self.graphics.stack.canvobjs[i].append(new_canv_obj)
                    self.canvcont.coords(new_canv_obj, self.config['offscreen'][0], self.config['offscreen'][1])
                    
                    self.graphics.stack.imgobjs[i].append(loaded_image)
                i += 1
        else:
            angle_increment = 360 / num_rotations
            transp_increment = 256 / self.transparency_precision
            for rot in range(num_rotations):
                transparency_list = []
                for transp in range(self.transparency_precision + 1):
                    angle = angle_increment * rot
                    if self.graphics.usesPIL:
                        img = self.graphics.flat.texture.rotate(0 - angle)
                        img = self.alphamult_im(img, (transp * transp_increment))
                        loaded_image = self.imageloader(image = img)
                    else:
                        loaded_image = self.imageloader(image = self.graphics.flat.texture)
                    new_canv_obj = self.canvcont.create_image(self.config['offscreen'][0], self.config['offscreen'][1], image = loaded_image, layer = self.layer)
                    transparency_list.append(new_canv_obj)
                    self.graphics.flat.textures.append(loaded_image)
                self.graphics.flat.canvobjs.append(transparency_list)
    
    def objset_from_angle(self, angle):
        return self.graphics.stack.canvobjs[int((angle / 360) * len(self.graphics.stack.canvobjs))]
    
    def obj_from_angle(self, angle, transparency):
        objs = self.graphics.flat.canvobjs[int((angle / 360) * len(self.graphics.flat.canvobjs))]
        #print(objs[int((transparency / 256) * len(objs))])
        if transparency == None:
            return objs[0]
        else:
            return objs[int((transparency / 256) * len(objs))]
    
    def tex_from_angle(self, angle):
        return self.graphics.flat.textures[int((angle / 360) * len(self.graphics.flat.canvobjs))]
    
    def alphamult_im(self, im, mult):
        try:
            return self.graphics.PILImageChops.multiply(im, self.graphics.PILImage.new('RGBA', im.size, color = (255, 255, 255, int(mult))))
        except ValueError:
            raise ValueError('Model texture doesn\'t have an alpha channel - make sure it uses 32 bit colour')
        
    def destroy(self):
        if self.graphics.displaytype == 'flat':
            for objs in self.graphics.flat.canvobjs:
                for obj in objs:
                    self.canvcont.delete(obj)
        else:
            for rotationset in self.graphics.stack.canvobjs:
                for obj in rotationset:
                    self.canvcont.delete(obj)
            

class DBAccess:
    def __init__(self, address):
        self.address = address
        
        self.connection = sql.connect(self.address)
    
    def load_map(self, name):
        pass
    
    def close(self):
        self.connection.commit()
        self.connection.close()
        
class CanvasMessages:
    def __init__(self, canvcont, pipe):
        self.canvcont = canvcont
        self.pipe = pipe
        
        self.messages = []
        self.running = True
        self.layer = 'log text'
        
        class graphical_properties:
            updatedelay = 1
            maxlen = 10
            font = ('', 10)
            height = 20
            persist = 8
            colour = 'black'
            alignment = 'br' #tl: top left, tr: top right, bl: bottom left, br: bottom right
            '''alignment_library = {'tl': tk.SE,
                                 'tr': tk.SW,
                                 'bl': tk.NE,
                                 'br': tk.NW}'''
            alignment_library = {'tl': tk.NW,
                                 'tr': tk.NE,
                                 'bl': tk.SW,
                                 'br': tk.SE}
            formatlib = {'tl': '[{0:^8}] {1}',
                         'tr': '{1} [{0:^8}]',
                         'bl': '[{0:^8}] {1}',
                         'br': '{1} [{0:^8}]'}
            is_ready = False #hasn't been written to yet
        self.graphical_properties = graphical_properties
        
        
        threading.Thread(target = self.pipe_receiver).start()
        threading.Thread(target = self.graphics_handler).start()
    
    def pipe_receiver(self):
        while self.running:
            data = self.pipe.recv()
            if type(data) == str:
                displaytext = data
            elif type(data) == list:
                displaytext = self.graphical_properties.formatlib[self.graphical_properties.alignment].format(data[0], data[1])
            self.messages.insert(0, {'text': displaytext, 'timestamp': time.time(), 'obj': self.canvcont.create_text(0, 0, text = displaytext, fill = self.graphical_properties.colour, font = self.graphical_properties.font, anchor = self.graphical_properties.alignment_library[self.graphical_properties.alignment], layer = self.layer)})
            if len(self.messages) > self.graphical_properties.maxlen:
                for message in self.messages[self.graphical_properties.maxlen:]:
                    self.canvcont.delete(message['obj'])
                self.messages = self.messages[:self.graphical_properties.maxlen]
    
    def graphics_handler(self):
        while not self.graphical_properties.is_ready:
            time.sleep(0.05)
        
        self.textentry_var = tk.StringVar()
        self.textentry_entry = tk.Entry(self.canvcont.canvas, textvariable = self.textentry_var, width = 30, **self.canvcont.game.client.ui.styling.get(font_size = 'small', object_type = tk.Entry))
        self.textentry_window = self.canvcont.create_window(*self.calc_coords(0, inset_x = 2, inset_y = 2),
                                                            anchor = self.graphical_properties.alignment_library[self.graphical_properties.alignment],
                                                            window = self.textentry_entry,
                                                            layer = 31)
        self.textentry_entry.bind('<Return>', self.send_message)
        
        while self.running:
            todelete = []
            msgs = self.messages.copy()
            for i in range(len(msgs)):
                message = msgs[i]
                x, y = self.calc_coords(i)
                self.canvcont.coords(message['obj'], x, y)
                if time.time() - message['timestamp'] > self.graphical_properties.persist:
                    self.canvcont.delete(message['obj'])
                    todelete.insert(0, i)
            for i in todelete:
                self.messages.pop(i)
            time.sleep(self.graphical_properties.updatedelay)
    
    def calc_coords(self, position, inset_x = 10, inset_y = 30):
        if self.graphical_properties.alignment == 'tl':
            return inset_x, 10 + (position * self.graphical_properties.height)
        elif self.graphical_properties.alignment == 'tr':
            return self.canvcont.canvas.winfo_width() - inset_x, inset_y + (position * self.graphical_properties.height)
        elif self.graphical_properties.alignment == 'bl':
            return inset_x, self.canvcont.canvas.winfo_height() - (position * self.graphical_properties.height) - inset_y
        elif self.graphical_properties.alignment == 'br':
            return self.canvcont.canvas.winfo_width() - inset_x, self.canvcont.canvas.winfo_height() - (position * self.graphical_properties.height) - inset_y
    
    def send_message(self, event = None):
        text = self.textentry_var.get()
        
        self.canvcont.game.client.send(modules.networking.Request(command = 'say', arguments = {'text': text}))
        
        self.textentry_var.set('')
        
        self.canvcont.canvas.focus_set()
        
    def stop(self):
        self.running = False

class colour:
    def increase(colour, increments):
        'Take a colour and increase each channel by the increments given in the list'
        colour_values = [int(colour[1:3], 16), int(colour[3:5], 16), int(colour[5:], 16)]
        output = [min(255, colour_values[0] + increments[0]), min(255, colour_values[1] + increments[1]), min(255, colour_values[2] + increments[2])]
        output = [max(0, output[0]), max(0, output[1]), max(0, output[2])]
        return '#{}{}{}'.format(hex(output[0])[2:], hex(output[1])[2:], hex(output[2])[2:])
    
    def multiply(colour, multipliers):
        'Take a colour and multiply each channel by the multipliers given in the list'
        colour_values = [int(colour[1:3], 16), int(colour[3:5], 16), int(colour[5:], 16)]
        output = [min(255, colour_values[0] * multipliers[0]), min(255, colour_values[1] * multipliers[1]), min(255, colour_values[2] * multipliers[2])]
        output = [max(0, output[0]), max(0, output[1]), max(0, output[2])]
        return '#{}{}{}'.format(hex(output[0])[2:], hex(output[1])[2:], hex(output[2])[2:])

class KeyBind:
    '''
    Easily bind a function to a key being pressed. It works better than the internal tkinter keybinding because the internal method will act like holding down a key in a text box (i.e. function is called once, then a slight delay, then it is called lots of times). Using this method, the function can be called every 0.1 seconds (or however long the delay is) from when the key is pressed until the key is released.
    '''
    def __init__(self, root, delay = 0.1, verbose = False):
        self.root = root
        self.delay = delay
        self.verbose = verbose
        
        self.binds = {}
        self._keystates = {}
        self._isactive = True #stores whether or not the keyboard
        
        threading.Thread(target = self._keyhandlerd, name = 'Keyboard input handler daemon').start()
        threading.Thread(target = self._checkfocusd, name = 'Root has focus daemon').start()
    
    def _keyhandlerd(self): #daemon to handle key inputs
        keypress_funcid = self.root.bind('<KeyPress>', self._onkeypress)
        keyrelease_funcid = self.root.bind('<KeyRelease>', self._onkeyrelease)
        m1_funcid = self.root.bind('<Button-1>', self._mouse1)
        
        while self._isactive:
            start = time.time()
            keypress_snapshot = self._keystates.copy() #so that the interacted dictionary doesn't change state (due to key presses or releases) when it is being iterated through
            for keysym in keypress_snapshot:
                if keypress_snapshot[keysym]:
                    if keysym in self.binds:
                        for bind in self.binds[keysym]:
                            bind()
            delay = self.delay - (time.time() - start)
            if delay > 0:
                time.sleep(delay)
        
        self.root.unbind('<KeyPress>', keypress_funcid)
        self.root.unbind('<KeyRelease>', keyrelease_funcid)
        self.root.unbind('<Button1>', m1_funcid)
    
    def _onkeypress(self, event):
        self._keystates[event.keysym.lower()] = True
        
        if self.verbose:
            print('Key {} was just pressed'.format(event.keysym.lower()))
    
    def _onkeyrelease(self, event):
        self._keystates[event.keysym.lower()] = False
    
    def bind(self, keysym, function):
        'Keysym can be a string or a list of strings'
        if type(keysym) == list:
            [self.bind(key, function) for key in keysym]
        elif keysym in self.binds:
            self.binds[keysym].append(function)
        else:
            self.binds[keysym] = [function]
    
    def unbind(self, keysym, function = None):
        if keysym in self.binds:
            if function == None or len(self.binds[keysym]) == 1:
                self.binds.pop(keysym)
            else:
                self.binds[keysym].delete(function)
    
    def unbind_all(self):
        self.binds = {}
    
    def get_state(self, keysym):
        if type(keysym) == list:
            for key in keysym:
                if self.get_state(key):
                    return True
            return False
        elif keysym.lower() in self._keystates:
            return self._keystates[keysym.lower()]
        else:
            return False
        
    def kill(self):
        self._isactive = False
    
    def _checkfocusd(self):
        while self._isactive:
            start = time.time()
            
            if not self.root == self.root.focus_get():
                keypress_snapshot = self._keystates.copy()
                for key in keypress_snapshot:
                    keypress_snapshot[key] = False
                self._keystates = keypress_snapshot
            
            delay = self.delay - (time.time() - start)
            if delay > 0:
                time.sleep(delay)
    
    def _mouse1(self, event):
        if "mouse1" in self.binds:
            for bind in self.binds["mouse1"]:
                bind()
        
        
class DisplayBar:
    def __init__(self, canvcont, min_value, max_value, coords, bg, fg):
        self.canvcont = canvcont
        self.min_value = min_value
        self.max_value = max_value
        self.coords = coords
        self.bg = bg
        self.fg = fg
        
        self.layer = 'hud'
        
        class objects:
            background = self.canvcont.create_rectangle(*coords, fill = self.bg, outline = self.bg, width = 5, layer = self.layer)
            display = self.canvcont.create_rectangle(*coords, fill = self.fg, outline = self.fg, width = 0, layer = self.layer)
        self.objects = objects
    
    def set_value(self, value):
        if value < self.min_value:
            value = self.min_value
        if value > self.max_value:
            value = self.max_value
        
        self.canvcont.coords(self.objects.display, self.coords[0], self.coords[1], self.coords[0] + ((self.coords[2] - self.coords[0]) * ((value - self.min_value) / (self.max_value - self.min_value))), self.coords[3])
    
    def destroy(self):
        self.canvcont.delete(self.objects.background)
        self.canvcont.delete(self.objects.display)

class InventoryBar:
    def __init__(self, canvcont, coords, textures_path, items_path, rendermethod, num_slots = 5, sprite_dimensions = [64, 64], backingcolour = '#A0A0A0', outlinewidth = 5, divider_size = 10, backingcolour_selected = '#EAEAEA'):
        self.canvcont = canvcont
        self.coords = coords #the coordinates for the top right of the inventory bar
        self.rendermethod = rendermethod
        self.num_slots = num_slots
        self.sprite_dimensions = sprite_dimensions
        self.backingcolour = backingcolour
        self.backingcolour_selected = backingcolour_selected
        self.outlinewidth = outlinewidth
        self.divider_size = divider_size
        
        self.layer = 'hud'
        
        class paths:
            textures = textures_path
            items = items_path
        self.paths = paths
        
        self.items_data = {}
        self.slot_objs = []
        self.selection_index = None
        self.inv_items = []
        
        for i in range(5):
            self.inv_items.append({'item': None, 'image': None, 'quantity': 0})
        
        self.load_assets()
        self.draw_slots()
        
    def load_assets(self):
        for item in os.listdir(self.paths.items):
            with open(os.path.join(self.paths.items, item), 'r') as file:
                data = json.load(file)
            self.items_data[item] = data
            self.items_data[item]['sprite object'] = self.rendermethod(file = os.path.join(self.paths.textures, self.items_data[item]['icon']))
    
    def draw_slots(self):
        coords = self.get_top_right_coords()
        for i in range(self.num_slots):
            x0 = coords[0] + (self.sprite_dimensions[0] * i) + (self.divider_size * i)
            x1 = x0 + self.sprite_dimensions[0]
            y0 = coords[1]
            y1 = y0 + self.sprite_dimensions[1]
            self.slot_objs.append(self.canvcont.create_rectangle(x0, y0, x1, y1, fill = self.backingcolour, outline = self.backingcolour, layer = self.layer))
    
    def select_index(self, index, force_refresh = False):
        if index != self.selection_index and not force_refresh:
            if not self.selection_index == None:
                self.canvcont.itemconfigure(self.slot_objs[self.selection_index], fill = self.backingcolour, outline = self.backingcolour)
            self.selection_index = index
            self.canvcont.itemconfigure(self.slot_objs[self.selection_index], fill = self.backingcolour_selected, outline = self.backingcolour_selected)
    
    def destroy(self):
        for object in self.slot_objs:
            self.canvcont.delete(object)
    
    def get_top_right_coords(self):
        x = self.coords[0] - ((self.sprite_dimensions[0] * (self.num_slots / 2)) + (self.divider_size * (self.num_slots / 2)))
        y = self.coords[1] - (self.sprite_dimensions[1] / 2)
        return [x, y]
    
    def increment_slot(self, index, increment):
        self.set_slot(index, quantity = int(self.inv_items[index]['quantity'] + increment))
    
    def set_slot(self, index, item = None, quantity = 0):
        if item == None:
            if self.items_data[self.inv_items[index]['item']]['unlimited']:
                quantity = max(quantity, 1)
        elif self.items_data[item]['unlimited']:
            quantity = max(quantity, 1)
        
        if quantity < 1:
            if not self.inv_items[index]['image'] == None:
                self.canvcont.delete(self.inv_items[index]['image'])
            self.inv_items[index] = {'item': None, 'image': None, 'quantity': 0}
        else:
            self.inv_items[index]['quantity'] = quantity
            if not item == None:
                self.inv_items[index]['item'] = item
                
                if self.inv_items[index]['image'] == None:
                    coords = self.get_top_right_coords()
                    self.inv_items[index]['image'] = self.canvcont.create_image(coords[0] + (self.sprite_dimensions[0] * (index + 0.5)) + (self.divider_size * index), coords[1] + (self.sprite_dimensions[1] / 2), image = self.items_data[item]['sprite object'], layer = self.layer)
    
    def get_item_info(self, item):
        return self.items_data[item]
    
    def get_slot_info(self, index):
        if self.inv_items[index]['quantity'] == 0:
            data = {}
        else:
            data = self.get_item_info(self.inv_items[index]['item'])
        data['quantity'] = self.inv_items[index]['quantity']
        data['file name'] = self.inv_items[index]['item']
        return data

class CanvasController:
    def __init__(self, canvas, game):
        self.canvas = canvas
        self.game = game
        
        self.layers = []
        self.reserved_args = ['layer']
        
        with open(os.path.join(sys.path[0], 'user', 'layers.json'), 'r') as file:
            self.layer_config = json.load(file)
        
    def create_rectangle(self, *coords, **args):
        'Wrapper function to provide tk canvas-like syntax'
        return self._create('rectangle', coords, args)
    
    def create_image(self, *coords, **args):
        'Wrapper function to provide tk canvas-like syntax'
        return self._create('image', coords, args)
    
    def create_text(self, *coords, **args):
        return self._create('text', coords, args)
    
    def create_window(self, *coords, **args):
        return self._create('window', coords, args)
    
    def _create(self, obj_type, coords, args):
        if not 'layer' in args:
            args['layer'] = 0
        
        if type(args['layer']) == str:
            if args['layer'] in self.layer_config:
                args['layer'] = self.layer_config[args['layer']]
            else:
                raise ValueError('Couldn\'t find layer name "{}" in config'.format(args['layer']))
            
        while not len(self.layers) >= args['layer'] + 1:
            self.layers.append([])
        
        filtered_args = {}
        for key in args:
            if not key in self.reserved_args:
                filtered_args[key] = args[key]
        
        if obj_type == 'rectangle':
            obj = self.canvas.create_rectangle(*coords, **filtered_args)
        elif obj_type == 'image':
            obj = self.canvas.create_image(*coords, **filtered_args)
        elif obj_type == 'text':
            obj = self.canvas.create_text(*coords, **filtered_args)
        elif obj_type == 'window':
            obj = self.canvas.create_window(*coords, **filtered_args)
        
        self.layers[args['layer']].append({'object': obj})
        
        ## objects are always created on the top
        
        if not len(self.layers) == args['layer'] + 1: ## logic to find next highest tag and move just below it
            next_layer = None
            for i in range(len(self.layers) - 1, args['layer'], -1):
                if not len(self.layers[i]) == 0:
                    next_layer = i
            if next_layer == None:
                if len(self.layers) == 1:
                    lower_to = None
                    for i in range(args['layer']):
                        if not len(self.layers[i]) == 0:
                            lower_to = self.layers[i][len(self.layers[args['layer']]) - 1]
                    if not lower_to == None:
                        self.canvas.tag_lower(obj, lower_to['object'])
                else:
                    self.canvas.tag_lower(obj, self.layers[args['layer']][len(self.layers[args['layer']]) - 2]['object'])
            else:
                self.canvas.tag_lower(obj, self.layers[next_layer][0]['object'])
        
        return obj
    
    def delete(self, obj):
        to_remove = []
        for a in range(len(self.layers)):
            for b in range(len(self.layers[a])):
                if self.layers[a][b]['object'] == obj:
                    to_remove.append([a, b])
        
        self.canvas.delete(obj)
        
        to_remove.reverse()
        for a, b in to_remove:
            self.layers[a].pop(b)
        
    def coords(self, obj, *coords):
        self.canvas.coords(obj, *coords)
    
    def itemconfigure(self, obj, **args):
        self.canvas.itemconfigure(obj, **args)

class PopMessage:
    def __init__(self, canvcont):
        self.canvcont = canvcont
        
        self.canvobj = None
        
        class graphical_properties:
            font = ''
            colour = '#FFFFFF'
        self.graphical_properties = graphical_properties
        
        self.message_queue, queue = mp.Pipe()
        
        threading.Thread(target = self._displayd, name = 'Message display daemon', args = [queue]).start()
    
    def queue_message(self, text, duration):
        if duration < 0.2:
            raise ValueError('Duration must be equal to or greater than 0.2')
        self.message_queue.send([text, duration])
    
    def _displayd(self, queue):
        while True:
            text_, duration = queue.recv()
            
            self.canvobj = self.canvcont.create_text(400, 300, text = text_, font = (self.graphical_properties.font, 0), fill = self.graphical_properties.colour, layer = 'hud')
            
            for i in range(0, 52, 2):
                self.canvcont.itemconfigure(self.canvobj, font = (self.graphical_properties.font, i))
                time.sleep(0.008)
            time.sleep(duration - 0.2)
            
            for i in range(50, -2, -2):
                self.canvcont.itemconfigure(self.canvobj, font = (self.graphical_properties.font, i))
                time.sleep(0.008)
                
            self.canvcont.delete(self.canvobj)
            self.canvobj = None