from tkinter import messagebox
import tkinter as tk
import multiprocessing as mp
import time
import threading
import os
import sys
import json
import random
import math
import importlib.util

import modules.netclients
import modules.quicklogs
import modules.bettercanvas


class Game:
    def __init__(self, canvas, client, ui):
        self.canvas = canvas
        self.client = client
        self.ui = ui
        
        class server:
            mode = 'internal' #either 'internal' or 'external'
            allow_external = True
            name = 'localhost'
        self.server = server
        
        self.log = modules.quicklogs.Log(os.path.join(sys.path[0], 'user', 'logs', 'client recv.txt'))
        
        self.vars = {}
        
        with open(os.path.join(sys.path[0], 'user', 'config.json'), 'r') as file:
            self.settingsdict = json.load(file)
        
        self.canvcont = modules.bettercanvas.CanvasController(self.canvas, self, get_pil = self.settingsdict['graphics']['PILrender'])
        
        self.message_pipe, pipe = mp.Pipe()
        self.messagedisplay = CanvasMessages(self.canvcont, pipe)
        self.messagedisplay.graphical_properties.font = (self.settingsdict['hud']['chat']['font'], self.settingsdict['hud']['chat']['fontsize'])
        self.messagedisplay.graphical_properties.maxlen = self.settingsdict['hud']['chat']['maxlen']
        self.messagedisplay.graphical_properties.persist = self.settingsdict['hud']['chat']['persist time']
        self.messagedisplay.graphical_properties.height = self.settingsdict['hud']['chat']['spacing']
        self.messagedisplay.graphical_properties.colour = self.settingsdict['hud']['chat']['colour']
        self.messagedisplay.graphical_properties.alignment = ['tl', 'tr', 'bl', 'br'][self.settingsdict['hud']['chat']['position']]
        self.messagedisplay.graphical_properties.is_ready = True
        
        self.killfeed_pipe, pipe = mp.Pipe()
        self.killfeeddisplay = CanvasMessages(self.canvcont, pipe, chatbox = False)
        self.killfeeddisplay.graphical_properties.font = (self.settingsdict['hud']['killfeed']['font'], self.settingsdict['hud']['killfeed']['fontsize'])
        self.killfeeddisplay.graphical_properties.maxlen = self.settingsdict['hud']['killfeed']['maxlen']
        self.killfeeddisplay.graphical_properties.persist = self.settingsdict['hud']['killfeed']['persist time']
        self.killfeeddisplay.graphical_properties.height = self.settingsdict['hud']['killfeed']['spacing']
        self.killfeeddisplay.graphical_properties.colour = self.settingsdict['hud']['killfeed']['colour']
        self.killfeeddisplay.graphical_properties.alignment = ['tl', 'tr', 'bl', 'br'][self.settingsdict['hud']['killfeed']['position']]
        self.killfeeddisplay.graphical_properties.is_ready = True
        
        self.popmsg = PopMessage(self.canvcont)
        self.popmsg.graphical_properties.font = self.settingsdict['hud']['popmsg']['font']
        self.popmsg.graphical_properties.colour = self.settingsdict['hud']['popmsg']['colour']
        self.popmsg.graphical_properties.divisions = self.settingsdict['hud']['popmsg']['divisions'][self.settingsdict['graphics']['model quality']]
        self.popmsg.graphical_properties.transition_time = self.settingsdict['hud']['popmsg']['pop time']
        self.popmsg.graphical_properties.max_size = self.settingsdict['hud']['popmsg']['max size']

        self.scoreline_display = DynamicStringDisplay(self.canvcont, self.canvas.winfo_width() / 2, 30, 'hud')
        self.scoreline_display.set_twoitems(0, 0)
        self.scoreline_display.set_styling(typeface = self.settingsdict['hud']['scoreboard']['font'],
                                           size = self.settingsdict['hud']['scoreboard']['size'],
                                           colour = self.settingsdict['hud']['scoreboard']['colour'])
        
        self.engine = Engine(self)

        # display IP
        self.message_pipe.send(['info', 'Connected to {}:{}'.format(self.client.serverdata.host, self.client.serverdata.port)])
        
        self.client.listener.binds.append(self.recv_handler)
        self.client.read_var('map')
        
        self.running = True
        threading.Thread(target = self.main, name = 'Player position updater', daemon = True).start()
        
        #make canvas take focus when the mouse enters, and lose it when it leaves
        self.canvas.bind('<Enter>', lambda event: self.canvas.focus_set())
        self.canvas.bind('<Leave>', lambda event: self.canvas.nametowidget('.').focus_set())
    
    def main(self):
        while self.running:
            time.sleep(0.05)
            if self.engine.current_map.player is not None:
                self.client.write_var('position', {'x': self.engine.current_map.player.attributes.pos.x, 'y': self.engine.current_map.player.attributes.pos.y, 'rotation': self.engine.current_map.player.attributes.rotation})
    
    def close(self):
        self.client.listener.binds.remove(self.recv_handler)
        self.running = False
        self.engine.keybindhandler.kill()
        self.engine.unload_current_map()
    
    def recv_handler(self, request):
        self.log.add('received', 'Data received from the server - {}'.format(request.pretty_print()))
        
        if request.command == 'say':
            if 'category' in request.arguments:
                self.message_pipe.send([request.arguments['category'], request.arguments['text']])
            else:
                self.message_pipe.send(['chat', request.arguments['text']])
                
        elif request.command == 'disconnect':
            if self.running:
                print('Connection to server interrupted')
                
                if 'clean' in request.arguments and not request.arguments['clean']:
                    text ='Connection to the server was interrupted\nYou may have a connection problem, or the server might have been shut down unexpectedly'
                else:
                    text = 'This server has been shut down'
                
                messagebox.showerror('Disconnected', text + '\n\nClick OK to return to the menu')
                self.ui.load('menu')
                
        elif request.command == 'var update w':
            if request.subcommand == 'map':
                if not self.engine.current_map.name == request.arguments['map name']:
                    self.engine.load_map(request.arguments['map name'])
                self.vars[request.subcommand] = request.arguments['map name']
                
            elif request.subcommand == 'player positions':
                positions = request.arguments['positions']
                
                for data in positions:
                    if data['id'] in self.engine.current_map.other_players:
                        self.engine.current_map.other_players[data['id']].set(x = data['x'],
                                                                              y = data['y'],
                                                                              rotation = data['rotation'])
                    else:
                        self.engine.current_map.other_players[data['id']] = Entity(random.choice(self.engine.cfgs.current_map['entity models'][self.engine.cfgs.current_map['player']['entity']]),
                                                                                 self.engine.current_map.path,
                                                                                 self.engine,
                                                                                 'player models',
                                                                                 is_player = False, server_controlled = True)
                        self.engine.current_map.other_players[data['id']].set(x = data['x'],
                                                                              y = data['y'],
                                                                              rotation = data['rotation'])
                        self.engine.log.add('players', 'Client-server discrepancy, created id {}'.format(data['id']))
                
                to_remove = []
                for conn_id in self.engine.current_map.other_players:
                    destroy = True
                    for data in positions:
                        if data['id'] == conn_id:
                            destroy = False
                    if destroy:
                        self.engine.current_map.other_players[conn_id].destroy()
                        to_remove.append(conn_id)
                
                for conn_id in to_remove:
                    self.engine.current_map.other_players.pop(conn_id)
                    self.engine.log.add('players', 'Client-server discrepancy, destroyed id {}'.format(conn_id))
                    
            elif request.subcommand == 'team':
                self.vars['team'] = request.arguments['value']
                
            elif request.subcommand == 'client position':
                self.engine.current_map.player.set(request.arguments['x'], request.arguments['y'], request.arguments['rotation'])
                
            elif request.subcommand == 'health':
                self.engine.current_map.player.set_health(request.arguments['value'])
                
            elif request.subcommand == 'scoreline':
                self.scoreline_display.set_twoitems(*request.arguments['scores'])
            
            elif request.subcommand == 'round time':
                if request.arguments['value'] is None or request.arguments['value'] <= 0:
                    self.engine.hud.round_timer.set('')
                else:
                    request.arguments['value'] = math.ceil(request.arguments['value'])
                    t_mins = math.floor(request.arguments['value'] / 60)
                    t_secs = '{:0>2}'.format(math.ceil(request.arguments['value'] - t_mins * 60))
                    self.engine.hud.round_timer.set_twoitems(t_mins, t_secs, sep = ':')
                
            else:
                self.vars[request.subcommand] = request.arguments['value']
                
        elif request.command == 'give':
            print(request.pretty_print())
            for item in request.arguments['items']:
                i = 0
                while self.engine.hud.invdisp.inv_items[i]['quantity'] != 0:
                    i += 1
                    
                self.engine.hud.invdisp.set_slot(i, item['item'], item['quantity'])
                
        elif request.command == 'var update r':
            if request.subcommand == 'username':
                self.client.write_var('username', self.settingsdict['user']['name'])
        
        elif request.command == 'update items':
            if request.subcommand == 'server tick':
                updates = request.arguments['pushed']
                for data in updates:
                    if data['type'] == 'add': #item has just been created
                        item = Item(data['file name'], self.engine.current_map.path, self.engine, 'items')
                        item.set(x = data['position'][0],
                                 y = data['position'][1],
                                 rotation = self.engine.snap_angle(data['rotation']))
                        item.attributes.ticket = data['ticket']
                        
                        self.engine.current_map.items.append(item)
                        
                    elif data['type'] == 'remove':
                        to_remove = []
                        for item in self.engine.current_map.items:
                            if item.attributes.ticket == data['ticket']:
                                to_remove.append(item)
                                
                        for item in to_remove:
                            item.destroy()
                            self.engine.current_map.items.remove(item)
                    
                    elif data['type'] == 'update position':
                        to_update = []
                        for item in self.engine.current_map.items:
                            if item.attributes.ticket == data['ticket']:
                                to_update.append(item)
                                
                        for item in to_update:
                            item.set(x = data['position'][0],
                                     y = data['position'][1])
                    
                    elif data['type'] == 'animation':
                        current_item = None
                        for item in self.engine.current_map.items:
                            if item.attributes.ticket == data['ticket']:
                                current_item = item
                        
                        if current_item is None:
                            print('Item not found - instruction = {}'.format(data))
                        
                        else:
                            if data['loop']:
                                current_item.loop_anim(data['animation'])
                            
                            else:
                                current_item.play_anim(data['animation'])
                        
        elif request.command == 'popmsg':
            self.popmsg.queue_message(request.arguments['text'], self.settingsdict['hud']['popmsg']['duration'][request.subcommand])
        
        elif request.command == 'event':
            if request.subcommand == 'death':
                self.killfeed_pipe.send([request.arguments['weapon'], request.arguments['text']])
        
        elif request.command == 'set mode':
            if request.subcommand == 'spectator':
                if self.engine.current_map.player is not None or not self.engine.current_map.player.running:
                    self.engine.current_map.player.destroy()
                    
            elif request.subcommand == 'player':
                if not self.engine.current_map.player.attributes.running:
                    self.engine.current_map.player = Entity(random.choice(self.engine.cfgs.current_map['entity models'][self.engine.cfgs.current_map['player']['entity']]), self.engine.current_map.path, self.engine, 'player models', is_player = True)
                self.engine.current_map.player.set(x = 400, y = 300, rotation = 0)
        
        elif request.command == 'set hit model':
            if request.subcommand == 'accurate' and not self.engine.hitdetection.accurate:
                spec = importlib.util.spec_from_file_location('lineintersection', os.path.join(sys.path[0], 'modules', 'lineintersection.py'))
                self.engine.hitdetection.module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(self.engine.hitdetection.module)
            
            self.engine.hitdetection.accurate = request.subcommand == 'accurate' #accurate or loose
        
        elif request.command == 'clear inventory':
            self.engine.hud.invdisp.make_empty()
        
        elif request.command == 'increment inventory slot':
            if not self.engine.hud.invdisp.get_slot_info(request.arguments['index'])['data']['unlimited']:
                self.engine.hud.invdisp.increment_slot(request.arguments['index'], request.arguments['increment'])
                

class Engine:
    def __init__(self, game):
        self.game = game
        
        self.log = modules.quicklogs.Log(os.path.join(sys.path[0], 'user', 'logs', 'engine.txt'))
        
        self.rendermethod = None
        
        self.running = True
        
        class cfgs:
            layout = {}
            current_map = {}
            user = {}
        self.cfgs = cfgs
        
        class current_map:
            event_overlays = {}
            player = None
            lightmap = None
            
            name = None
            path = None
            
            class materials:
                data = {}
                scripts = {}
                scripts_generic = {}
            
            class statics:
                panels = []
                scatters = []
                base = None
                overlay = None
            
            items = []
            
            other_players = {}
        self.current_map = current_map
        
        class hud:
            healthbar = None
            invdisp = None
            round_timer = None
            
            pulse_in_progress = False
        self.hud = hud
        
        class hitdetection:
            accurate = False
            module = None
        self.hitdetection = hitdetection
        
        class debug:
            flags = None
            panel_intersections = None
            player_pos = None
            player_speed = None
            cursor_pos = None
        self.debug = debug
        
        #check user cfg
        with open(os.path.join(sys.path[0], 'user', 'config.json'), 'r') as file:
            self.cfgs.user = json.load(file)
        
        #get debugging settings
        with open(os.path.join(sys.path[0], 'user', 'debug.json'), 'r') as file:
            self.debug.flags = json.load(file)
        
        if self.debug.flags['engine']['panels']['show intersections']:
            self.debug.panel_intersections = DynamicStringDisplay(self.game.canvcont, 70, 300, 'debug')
            self.debug.panel_intersections.set_styling(size = 18, colour = '#FFFFFF')

        if self.debug.flags['engine']['player']['pos']:
            self.debug.player_pos = DynamicStringDisplay(self.game.canvcont, 620, 270, 'debug')
            self.debug.player_pos.set_styling(size = 18, colour = '#FFFFFF')

        if self.debug.flags['engine']['player']['speed']:
            self.debug.player_speed = DynamicStringDisplay(self.game.canvcont, 620, 240, 'debug')
            self.debug.player_speed.set_styling(size = 18, colour = '#FFFFFF')
        
        if self.debug.flags['engine']['cursor pos']:
            self.debug.cursor_pos = DynamicStringDisplay(self.game.canvcont, 620, 300, 'debug')
            self.debug.cursor_pos.set_styling(size = 18, colour = '#FFFFFF')
            self.game.canvcont.bind('<Motion>', lambda event: self.debug.cursor_pos.set('CURSOR: ({}, {})'.format(event.x, event.y)))
            self.game.canvcont.bind('<Leave>', lambda event: self.debug.cursor_pos.set('CURSOR: Outside of screen'))
        
        self.hud.round_timer = DynamicStringDisplay(self.game.canvcont, 50, 35, 'hud')
        self.hud.round_timer.set_styling(size = self.cfgs.user['hud']['round timer']['size'],
                                         typeface = self.cfgs.user['hud']['round timer']['font'],
                                         colour = self.cfgs.user['hud']['round timer']['colour'])
        self.hud.round_timer.set_twoitems(0, 0, sep = ':')

        #make keybind handler
        self.keybindhandler = KeyBind(self.game.canvas)
        
        #player rotation thread
        threading.Thread(target = self._player_rotationd, name = 'Player rotation daemon').start()
    
    def load_map(self, name):
        path = os.path.join(sys.path[0], 'server', 'maps', name)
        
        if os.path.isdir(path):
            #unload current map
            self.unload_current_map()
            
            #set new map name and path
            self.current_map.path = path
            self.current_map.name = name
            
            self.game.message_pipe.send(['map load', 'Loading map "{}"'.format(name)])
            
            #use correct rendering method
            if self.cfgs.user['graphics']['PILrender']:
                self.rendermethod = __import__('PIL.ImageTk').ImageTk.PhotoImage
                self.game.message_pipe.send(['map load', 'Loaded PIL image renderer'])
            else:
                self.rendermethod = tk.PhotoImage
                self.game.message_pipe.send(['map load', 'Loaded internal image renderer'])
            
            #open map cfg
            with open(os.path.join(self.current_map.path, 'list.json'), 'r') as file:
                self.cfgs.current_map = json.load(file)
            self.game.message_pipe.send(['map load', 'Loaded map cfg'])
            
            #load and render base and overlay textures
            if self.cfgs.current_map['background']['base'] is None:
                self.game.message_pipe.send(['map load', 'No base texture'])
            else:
                self.current_map.statics.base = modules.bettercanvas.Model(self.game.canvcont, self.cfgs.current_map['background']['base'], self.current_map.path, 'base texture')
                self.current_map.statics.base.set(x = 402, y = 302)
                self.game.message_pipe.send(['map load', 'Loaded base texture'])
            
            if self.cfgs.current_map['background']['overlay'] is None:
                self.game.message_pipe.send(['map load', 'No overlay texture'])
            else:
                self.current_map.statics.overlay = modules.bettercanvas.Model(self.game.canvcont, self.cfgs.current_map['background']['overlay'], self.current_map.path, 'overlay')
                self.current_map.statics.overlay.set(x = 402, y = 302)
                self.game.message_pipe.send(['map load', 'Loaded overlay texture'])
            
            #create lightmap model
            self.current_map.lightmap = modules.bettercanvas.Model(self.game.canvcont, os.path.join('system', 'lightmap'), self.current_map.path, 'lightmap')
            self.current_map.lightmap.setpos(402, 302)
            
            #load all event textures into memory
            for name in self.cfgs.user['hud']['overlays']:
                self.current_map.event_overlays[name] = modules.bettercanvas.Model(self.game.canvcont, self.cfgs.user['hud']['overlays'][name], self.current_map.path, 'event overlays')
                self.current_map.event_overlays[name].set(x = 402, y = 302, rotation = 0, transparency = 0)
            
            #open layout
            with open(os.path.join(self.current_map.path, 'layout.json'), 'r') as file:
                self.cfgs.layout = json.load(file)
            self.game.message_pipe.send(['map load', 'Loaded layout data'])
            
            #load scripts
            self.current_map.materials.scripts = {}
            for script in os.listdir(os.path.join(self.current_map.path, 'scripts')):
                if not (script.startswith('.') or script.startswith('_')):
                    spec = importlib.util.spec_from_file_location('matscript', os.path.join(self.current_map.path, 'scripts', script))
                    script_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(script_module)
                    self.current_map.materials.scripts[script] = script_module.Script
                    
                    self.current_map.materials.scripts_generic[script] = script_module.Script()
            
            #make layout panels
            anim_panels = []
            for panel in self.cfgs.layout['geometry']:
                panel_object = Panel(self.game.canvcont, panel['material'], self.current_map.path, 'map panels', autoplay_anims = False)
                panel_object.load_scripts(self.current_map.materials.scripts)
                panel_object.set(x = panel['coordinates'][0], y = panel['coordinates'][1])
                self.current_map.statics.panels.append(panel_object)
                
                if panel_object.attributes.anim_controller.run_loop:
                    anim_panels.append(panel_object)
        
            self.game.canvcont.set_time(time.time() + self.cfgs.current_map['animation']['sync window'][self.cfgs.user['graphics']['model quality']])
            
            for panel in anim_panels:
                panel.start_anims()
            
            self.game.message_pipe.send(['map load', 'Rendered layout panels'])
            
            #render scatters
            if len(self.cfgs.current_map['background']['scatters']) > 0:
                for i in range(int(self.cfgs.current_map['background']['scatternum'] / len(self.cfgs.current_map['background']['scatters']))):
                    for scatter in self.cfgs.current_map['background']['scatters']:
                        scattermdl = modules.bettercanvas.Model(self.game.canvcont, random.choice(self.cfgs.current_map['entity models'][scatter]), self.current_map.path, 'scatters')
                        scattermdl.set(x = random.randint(0, 800), y = random.randint(0, 600))
                        self.current_map.statics.scatters.append(scattermdl)
                        
                self.game.message_pipe.send(['map load', 'Loaded scatters'])
            
            #load player
            self.game.message_pipe.send(['map load', 'Creating player model...'])
            self.current_map.player = Entity(random.choice(self.cfgs.current_map['entity models'][self.cfgs.current_map['player']['entity']]), self.current_map.path, self, 'player models', is_player = True, server_controlled = False)
            self.game.message_pipe.send(['map load', 'Loaded player model'])
            self.current_map.player.set(x = 400, y = 300, rotation = 0)
            
            #make healthbar
            self.hud.healthbar = DisplayBar(self.game.canvcont, 0, 100, [10, 10, 100, 20], 'gray', 'red')
            self.hud.healthbar.set_value(100)
            
            #make inventory display
            self.hud.invdisp = InventoryBar(self.game.canvcont, [400, 550], os.path.join(self.current_map.path, 'textures'), os.path.join(self.current_map.path, 'items'), self.rendermethod)
            self.hud.invdisp.select_index(0)
            
            #set up binds for inventory display
            with open(os.path.join(sys.path[0], 'user', 'keybinds.json'), 'r') as file:
                keybinds_data = json.load(file)
            self.keybindhandler.bind(keybinds_data['inventory']['slot0'], lambda: self.hud.invdisp.select_index(0))
            self.keybindhandler.bind(keybinds_data['inventory']['slot1'], lambda: self.hud.invdisp.select_index(1))
            self.keybindhandler.bind(keybinds_data['inventory']['slot2'], lambda: self.hud.invdisp.select_index(2))
            self.keybindhandler.bind(keybinds_data['inventory']['slot3'], lambda: self.hud.invdisp.select_index(3))
            self.keybindhandler.bind(keybinds_data['inventory']['slot4'], lambda: self.hud.invdisp.select_index(4))
            self.keybindhandler.bind(keybinds_data['inventory']['use'], self.use_current_item)
            
            #set values for health bar and inventory bar
            self.hud.healthbar.set_value(100)
            self.hud.invdisp.select_index(0)
            
            #tell the server that the player has loaded in
            self.game.client.notify_map_load_finished()
            self.log.add('map', 'Finished loading map "{}"'.format(self.current_map.name))
            
            #centre scoreline display
            self.game.scoreline_display.pos.x = self.game.canvas.winfo_width() / 2
            self.game.scoreline_display.refresh()
    
    def unload_current_map(self):
        for scatter in self.current_map.statics.scatters:
            scatter.destroy()
        self.current_map.scatters = []
        
        for panel in self.current_map.statics.panels:
            panel.destroy()
        self.current_map.panels = []
        
        for overlay in self.current_map.event_overlays:
            self.current_map.event_overlays[overlay].destroy()
        self.current_map.event_overlays = {}
        
        if self.current_map.player is not None:
            self.current_map.player.destroy()
            self.current_map.player = None
        
        if self.current_map.lightmap is not None:
            self.current_map.lightmap.destroy()
            self.current_map.lightmap = None
        
        self.current_map.materials.data = None
        self.current_map.materials.scripts = {}
        
        for script_name in self.current_map.materials.scripts_generic: #these have all been activated
            script = self.current_map.materials.scripts_generic[script_name]
            if 'destroy' in dir(script):
                script.destroy()
        self.current_map.materials.scripts_generic = {}
        
        for item in self.current_map.items:
            item.destroy()
            
        self.game.message_pipe.send(['map load', 'Cleared old map assets'])
        
        if self.keybindhandler is not None:
            self.keybindhandler.unbind_all()
        
        self.current_map.name = None
        self.current_map.path = None
    
    def find_panels_underneath(self, x, y):
        output = []
        for panel in self.current_map.statics.panels:
            relative_coords = [x - panel.attributes.pos.x, y - panel.attributes.pos.y]
            
            if math.hypot(*relative_coords) <= panel.attributes.hitbox.maxdist:
                if self.is_inside_hitbox(relative_coords[0], relative_coords[1], panel.attributes.hitbox.geometry):
                    output.append(panel)
        
        if self.debug.panel_intersections is not None:
            text = 'Intersections:'
            for panel, mat_data in output:
                text += '\n({}, {}) - {}'.format(round(panel.attributes.pos.x, 1), round(panel.attributes.pos.x, 1), panel.cfgs.material['display name'])
            self.debug.panel_intersections.set(text)
        
        return output
    
    def is_inside_hitbox(self, x, y, hitbox):
        nhitbox = []
        for hx, hy in hitbox:
            nhitbox.append([hx - x, hy - y])
        return self.origin_is_inside_hitbox(nhitbox)
    
    def origin_is_inside_hitbox(self, hitbox):
        """Find if (0, 0) is inside a hitbox (an ngon made up of pairs of values)"""
        if self.hitdetection.accurate:
            max_x = max(hitbox, key = lambda index: abs(index[0]))[0]
            max_y = max(hitbox, key = lambda index: abs(index[1]))[1]
            
            m = max(max_x, max_y)
            
            num_intersections = 0
            for i in range(0, len(hitbox), 1):
                if self.hitdetection.module.does_intersect([[m, m], [0, 0]], [hitbox[i], hitbox[(i + 1) % len(hitbox)]]):
                    num_intersections += 1
            return [False, True][num_intersections % 2]
        else:
            has_smaller = False
            has_bigger = False
            for hx, hy in hitbox:
                if hx > 0 and hy > 0:
                    has_bigger = True
                if hx < 0 and hy < 0:
                    has_smaller = True
            return has_smaller and has_bigger
    
    def use_current_item(self):
        if self.hud.invdisp.get_slot_info(self.hud.invdisp.selection_index)['quantity'] > 0:
            angle = self.angle(self.game.canvas.winfo_pointerx() - self.game.canvas.winfo_rootx() - self.current_map.player.attributes.pos.x, self.game.canvas.winfo_pointery() - self.game.canvas.winfo_rooty() - self.current_map.player.attributes.pos.y)
            angle = math.degrees(angle)
            
            self.game.client.use_item(self.hud.invdisp.get_slot_info(self.hud.invdisp.selection_index)['file name'], angle, [self.current_map.player.attributes.pos.x, self.current_map.player.attributes.pos.y], self.hud.invdisp.selection_index)
            
            self.current_map.player.play_anim('attack')
    
    def pulse_item_transparency(self, model, timescale = 0.2):
        if not self.hud.pulse_in_progress:
            self.hud.pulse_in_progress = True
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
                model.set(transparency = min(255, i))
                if i >= 256: 
                    upstroke = False
            else:
                i -= increment
                model.set(transparency = min(255, i))
                
            time.sleep(max(0, delay - (time.time() - start)))
            
        model.set(transparency = 0)
        self.hud.pulse_in_progress = False
    
    def angle(self, delta_x, delta_y, maths_mode = False):
        if maths_mode: #anticlockwise from right hand horizontal
            return ((math.pi / 2) - self.angle(delta_x, delta_y)) % (2 * math.pi)

        else: #clockwise from top
            if delta_x == 0:
                if delta_y > 0:
                    return math.pi / 2
                else:
                    return (3 * math.pi) / 2

            elif delta_x < 0:
                return math.atan(delta_y / delta_x) + math.pi

            else:
                return math.atan(delta_y / delta_x)
    
    @staticmethod
    def snap_angle(angle):
        angle = angle % 360
        if 45 <= angle < 135:
            return 90
        elif 135 <= angle < 225:
            return 180
        elif 225 <= angle < 315:
            return 270
        else:
            return 0
    
    def _player_rotationd(self):
        while self.running:
            while self.current_map.player is not None:
                self.current_map.player.set(rotation = self.snap_angle(math.degrees(self.angle(self.keybindhandler.mouse.x - self.current_map.player.attributes.pos.x,
                                                                                               self.keybindhandler.mouse.y - self.current_map.player.attributes.pos.y))))
                time.sleep(0.1)
            time.sleep(0.1)
        
        
class CanvasMessages:
    def __init__(self, canvcont, pipe, chatbox = True):
        self.canvcont = canvcont
        self.pipe = pipe
        self.chatbox = chatbox
        
        self.messages = []
        self.running = True
        self.layer = 'log text'
        self.textentry_entry = None
        self.textentry_var = None
        self.textentry_window = None
        
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
        
        
        threading.Thread(target = self.pipe_receiver, name = 'Canvas messages pipe listener', daemon = True).start()
        threading.Thread(target = self.graphics_handler, name = 'Canvas messages graphics handler', daemon = True).start()
    
    def pipe_receiver(self):
        while self.running:
            data = self.pipe.recv()
            
            if type(data) == str:
                displaytext = data
            elif type(data) == list:
                displaytext = self.graphical_properties.formatlib[self.graphical_properties.alignment].format(data[0], data[1])
            else:
                displaytext = str(data)
                
            self.messages.insert(0, {'text': displaytext,
                                     'timestamp': time.time(),
                                     'obj': self.canvcont.create_text(0, 0,
                                                                      text = displaytext,
                                                                      fill = self.graphical_properties.colour,
                                                                      font = self.graphical_properties.font,
                                                                      anchor = self.graphical_properties.alignment_library[self.graphical_properties.alignment],
                                                                      layer = self.layer)})
            
            if len(self.messages) > self.graphical_properties.maxlen:
                for message in self.messages[self.graphical_properties.maxlen:]:
                    self.canvcont.delete(message['obj'])
                    
                self.messages = self.messages[:self.graphical_properties.maxlen]
    
    def graphics_handler(self):
        while not self.graphical_properties.is_ready:
            time.sleep(0.05)
        
        if self.chatbox:
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
        self.canvcont.game.client.say(text)
        
        self.textentry_var.set('')
        self.canvcont.canvas.focus_set()
        
    def stop(self):
        self.running = False
        
        
class KeyBind:
    """
    Easily bind a function to a key being pressed. It works better than the internal tkinter keybinding because the internal method will act like holding down a key in a text box (i.e. function is called once, then a slight delay, then it is called lots of times). Using this method, the function can be called every 0.1 seconds (or however long the delay is) from when the key is pressed until the key is released.
    """
    def __init__(self, root, delay = 0.1, verbose = False):
        self.root = root
        self.delay = delay
        self.verbose = verbose
        
        self.binds = {}
        self._keystates = {}
        self._isactive = True #stores whether or not the keyboard
        
        class mouse:
            x = 0
            y = 0
        self.mouse = mouse
        
        threading.Thread(target = self._keyhandlerd, daemon = True, name = 'Keyboard input handler daemon').start()
        threading.Thread(target = self._checkfocusd, daemon = True, name = 'Root has focus daemon').start()
    
    def _keyhandlerd(self): #daemon to handle key inputs
        keypress_funcid = self.root.bind('<KeyPress>', self._onkeypress)
        keyrelease_funcid = self.root.bind('<KeyRelease>', self._onkeyrelease)
        m1_funcid = self.root.bind('<Button-1>', self._mouse1)
        mmove_funcid = self.root.bind('<Motion>', self._mousemove)
        
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
        self.root.unbind('<Motion>', mmove_funcid)
    
    def _onkeypress(self, event):
        self._keystates[event.keysym.lower()] = True
        
        if self.verbose:
            print('Key {} was just pressed'.format(event.keysym.lower()))
    
    def _onkeyrelease(self, event):
        self._keystates[event.keysym.lower()] = False
    
    def bind(self, keysym, func):
        """Keysym can be a string or a list of strings"""
        if type(keysym) == list:
            [self.bind(key, func) for key in keysym]
        elif keysym in self.binds:
            self.binds[keysym].append(func)
        else:
            self.binds[keysym] = [func]
    
    def unbind(self, keysym, func = None):
        if keysym in self.binds:
            if func is None or len(self.binds[keysym]) == 1:
                self.binds.pop(keysym)
            else:
                self.binds[keysym].delete(func)
    
    def unbind_all(self):
        self.binds = {}
    
    def get_state(self, keysym):
        if type(keysym) == list:
            for key in keysym:
                if self.get_state(key):
                    return True
        elif keysym.lower() in self._keystates:
            return self._keystates[keysym.lower()]
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
    
    def _mouse1(self, event = None):
        if "mouse1" in self.binds:
            for bind in self.binds["mouse1"]:
                bind()
    
    def _mousemove(self, event):
        self.mouse.x = event.x
        self.mouse.y = event.y
        
        if 'look' in self.binds:
            for bind in self.binds['look']:
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
    def __init__(self, canvcont, coords, textures_path, items_path, rendermethod, num_slots = 5, sprite_dimensions = None, backingcolour = '#A0A0A0', outlinewidth = 5, divider_size = 10, backingcolour_selected = '#EAEAEA'):
        self.canvcont = canvcont
        self.coords = coords #the coordinates for the top right of the inventory bar
        self.rendermethod = rendermethod
        self.num_slots = num_slots
        self.sprite_dimensions = sprite_dimensions
        self.backingcolour = backingcolour
        self.backingcolour_selected = backingcolour_selected
        self.outlinewidth = outlinewidth
        self.divider_size = divider_size
        
        if sprite_dimensions is None:
            self.sprite_dimensions = [64, 64]
        else:
            self.sprite_dimensions = sprite_dimensions
        
        self.layer = 'hud'
        self.numbers_layer = 'inventory numbers'
        
        class paths:
            textures = textures_path
            items = items_path
        self.paths = paths
        
        self.items_data = {}
        self.slot_objs = []
        self.selection_index = None
        self.inv_items = []
        
        for i in range(self.num_slots):
            self.inv_items.append({'item': None, 'image': None, 'quantity': 0, 'count obj': None})
        
        self.load_assets()
        self.draw_slots()
        
    def load_assets(self):
        for item in os.listdir(self.paths.items):
            if item.endswith('.json'):
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
            if self.selection_index is not None:
                self.canvcont.itemconfigure(self.slot_objs[self.selection_index], fill = self.backingcolour, outline = self.backingcolour)
            self.selection_index = index
            self.canvcont.itemconfigure(self.slot_objs[self.selection_index], fill = self.backingcolour_selected, outline = self.backingcolour_selected)
    
    def destroy(self):
        for obj in self.slot_objs:
            self.canvcont.delete(obj)
    
    def get_top_right_coords(self):
        x = self.coords[0] - ((self.sprite_dimensions[0] * (self.num_slots / 2)) + (self.divider_size * (self.num_slots / 2)))
        y = self.coords[1] - (self.sprite_dimensions[1] / 2)
        return [x, y]
    
    def increment_slot(self, index, increment):
        self.set_slot(index, quantity = int(self.inv_items[index]['quantity'] + increment))
    
    def set_slot(self, index, item = None, quantity = 0, override = False):
        if item is not None and self.inv_items[index]['item'] is not None and self.items_data[item]['unlimited'] and not override:
            quantity = max(quantity, 1)
        
        if quantity < 1:
            if not self.inv_items[index]['image'] is None:
                self.canvcont.delete(self.inv_items[index]['image'])
                self.canvcont.delete(self.inv_items[index]['count obj'])
            self.inv_items[index] = {'item': None, 'image': None, 'quantity': 0, 'count obj': None}
        else:
            self.inv_items[index]['quantity'] = quantity
            if item is not None:
                self.inv_items[index]['item'] = item
                
                if self.inv_items[index]['image'] is None:
                    coords = self.get_top_right_coords()
                    self.inv_items[index]['image'] = self.canvcont.create_image(coords[0] + (self.sprite_dimensions[0] * (index + 0.5)) + (self.divider_size * index), coords[1] + (self.sprite_dimensions[1] / 2), image = self.items_data[item]['sprite object'], layer = self.layer)
                    self.inv_items[index]['count obj'] = self.canvcont.create_text(coords[0] + (self.sprite_dimensions[0] * (index + 0.9)) + (self.divider_size * index), coords[1] + (self.sprite_dimensions[1] * 0.9), text = str(quantity), layer = self.numbers_layer)
            
            if self.inv_items[index]['item'] is not None and self.items_data[self.inv_items[index]['item']]['unlimited']:
                self.canvcont.itemconfigure(self.inv_items[index]['count obj'], text = '∞')
            else:
                self.canvcont.itemconfigure(self.inv_items[index]['count obj'], text = str(quantity))
    
    def get_item_info(self, item):
        if item in self.items_data:
            return self.items_data[item]
        else:
            return {}
    
    def get_slot_info(self, index):
        if self.inv_items[index]['quantity'] == 0:
            data = {}
        else:
            data = self.get_item_info(self.inv_items[index]['item'])
        data['quantity'] = self.inv_items[index]['quantity']
        data['file name'] = self.inv_items[index]['item']
        data['data'] = self.get_item_info(self.inv_items[index]['item'])
        return data

    def make_empty(self):
        for i in range(self.num_slots):
            self.set_slot(i, override = True)

class PopMessage:
    def __init__(self, canvcont):
        self.canvcont = canvcont
        
        self.canvobj = None
        
        class graphical_properties:
            font = ''
            colour = '#FFFFFF'
            divisions = 0
            transition_time = 0
            max_size = 0
        self.graphical_properties = graphical_properties
        
        self.message_queue, queue = mp.Pipe()
        
        threading.Thread(target = self._displayd, name = 'Message display daemon', daemon = True, args = [queue]).start()
    
    def queue_message(self, text, duration):
        if duration < 0.2:
            raise ValueError('Duration must be equal to or greater than 0.2')
        self.message_queue.send([text, duration])
    
    def _displayd(self, queue):
        while True:
            text_, duration = queue.recv()
            
            self.canvobj = self.canvcont.create_text(400, 300, text = text_, font = (self.graphical_properties.font, 0), fill = self.graphical_properties.colour, justify = tk.CENTER, layer = 'hud')
            
            delay = self.graphical_properties.transition_time / self.graphical_properties.divisions
            size_increase = self.graphical_properties.max_size / self.graphical_properties.divisions
            
            i = 0
            while i < self.graphical_properties.max_size:
                start = time.time()
                i += size_increase
                self.canvcont.itemconfigure(self.canvobj, font = (self.graphical_properties.font, int(i)))
                time.sleep(delay - min(delay, time.time() - start))
                
            time.sleep(duration - self.graphical_properties.transition_time)
            
            i = self.graphical_properties.max_size
            while i > 0:
                start = time.time()
                i -= size_increase
                self.canvcont.itemconfigure(self.canvobj, font = (self.graphical_properties.font, int(i)))
                time.sleep(delay - min(delay, time.time() - start))
                
            self.canvcont.delete(self.canvobj)
            self.canvobj = None

class DynamicStringDisplay:
    def __init__(self, canvcont, pos_x, pos_y, layer):
        self.canvcont = canvcont
        self.layer = layer
        
        if pos_x is None:
            pos_x = self.canvcont.winfo_width() / 2
            
        if pos_y is None:
            pos_y = self.canvcont.winfo_height() / 2
        
        class pos:
            x = pos_x
            y = pos_y
        self.pos = pos
        
        class styling:
            align = tk.CENTER
            font = ['', 30]
            colour = '#000000'
        self.styling = styling
        
        self.text = ''
        
        self.text_obj = self.canvcont.create_text(self.pos.x, self.pos.x, layer = self.layer)
        
        self.refresh()
    
    def refresh(self):
        self.canvcont.coords(self.text_obj, self.pos.x, self.pos.y)
        self.canvcont.itemconfigure(self.text_obj, font = self.styling.font, anchor = self.styling.align, text = self.text, fill = self.styling.colour)
    
    def set(self, text):
        self.text = text
        self.refresh()
    
    def set_twoitems(self, item1, item2, sep = ' - ', fillchar = ' '):
        maxlen = max(len(str(item1)), len(str(item2)))
        self.set('{0:{2}>{3}}{4}{1:{2}>{3}}'.format(item1, item2, fillchar, maxlen, sep))
    
    def setpos(self, x = None, y = None):
        if x is not None:
            self.pos.x = x
        if y is not None:
            self.pos.y = y
        
        self.refresh()
    
    def set_styling(self, typeface = None, size = None, colour = None):
        if typeface is not None:
            self.styling.font[0] = typeface
        if size is not None:
            self.styling.font[1] = size
        if colour is not None:
            self.styling.colour = colour
        
        self.refresh()

class Panel(modules.bettercanvas.Model):
    def __init__(self, canvas_controller, mat_name, map_path, layer, autoplay_anims = True):
        self.mat_name = mat_name
        
        with open(os.path.join(map_path, 'materials', mat_name), 'r') as file:
            mat_cfg = json.load(file)
        
        super().__init__(canvas_controller, mat_cfg['model'], map_path, layer, autoplay_anims)
        
        self.cfgs.material = mat_cfg
        
        class hitbox:
            geometry = self.cfgs.material['hitbox']
            maxdist = self.cfgs.material['hitbox maxdist']
        self.attributes.hitbox = hitbox
    
    def load_scripts(self, library):
        self.attributes.scripts = []
        
        if 'scripts' in self.cfgs.material:
            for script in self.cfgs.material['scripts']:
                if script in library:
                    self.attributes.scripts.append(library[script](self))
                else:
                    print('Script "{}" not in script library'.format(script))

class Entity(modules.bettercanvas.Model):
    def __init__(self, ent_name, map_path, engine, layer, is_player = False, server_controlled = False):
        self.ent_name = ent_name
        self.engine = engine
        self.map_path = map_path
    
        super().__init__(self.engine.game.canvcont, self.ent_name, self.map_path, layer)
        
        self.engine = engine
        self.attributes.is_player = is_player
        self.attributes.server_controlled = server_controlled
        
        class velocity:
            x = 0
            y = 0
            base_increment = 1
            delay = 0.05
        self.attributes.pos.velocity = velocity
        
        self.attributes.health = 100
        self.attributes.clip = True
        self.attributes.script_delay = 0.05
        
        class _strafemove:
            mult = 1.5
            increment = 0.05
            current_strafe = None
            current_mult = 1
        self._strafemove = _strafemove
        
        threading.Thread(target = self._velocityd, name = 'Entity velocity daemon', daemon = True).start()
        threading.Thread(target = self._scriptd, name = 'Entity script handling daemon', daemon = True).start()
    
    def set_health(self, value):
        if value is not None:
            self.attributes.health = value
            
            if self.attributes.is_player:
                if self.attributes.health is not None and self.attributes.health > value:
                    self.engine.pulse_item_transparency(self.engine.current_map.event_overlays['damage'])

                if self.engine.hud.healthbar is not None:
                    self.engine.hud.healthbar.set_value(self.attributes.health)
                
                self.engine.game.client.write_var('health', self.attributes.health)
    
    def increment_health(self, inc):
        if inc is not None and self.attributes.health is not None:
            return self.set_health(self.attributes.health + inc)
    
    def _scriptd(self):
        touching_last_loop = []
        while self.attributes.running:
            start = time.time()
        
            touching_this_loop = []
            for panel in self.engine.find_panels_underneath(self.attributes.pos.x, self.attributes.pos.y):
                touching_this_loop.append(panel)
                for script in panel.attributes.scripts:
                    if 'when touching' in script.binds:
                        for func in script.binds['when touching']:
                            func(self)
                            
                    if not panel in touching_last_loop:
                        if 'on enter' in script.binds:
                            for func in script.binds['on enter']:
                                func(self)
                                    
            for panel in touching_last_loop:
                if not panel in touching_this_loop:
                    for script in panel.attributes.scripts:
                        if 'on leave' in script.binds:
                            for func in script.binds['on leave']:
                                func(self)
                                    
            touching_last_loop = touching_this_loop
            
            if self.attributes.pos.x < 0 or self.attributes.pos.x > self.cfgs.map['geometry'][0] or self.attributes.pos.y < 0 or self.attributes.pos.y > self.cfgs.map['geometry'][1]:
                if self.ent_name in self.cfgs.map['events'] and 'outside map' in self.cfgs.map['events'][self.ent_name]:
                    for path in self.cfgs.map['events'][self.ent_name]['outside map']:
                        obj = self.engine.current_map.materials.scripts_generic[path]
                        if 'when outside map' in obj.binds:
                            for func in obj.binds['when outside map']:
                                func(self)
            
            delay = self.attributes.script_delay - (time.time() - start)
            if delay > 0:
                time.sleep(delay)
    
    def _velocityd(self):
        with open(os.path.join(sys.path[0], 'user', 'keybinds.json'), 'r') as file:
            keybind_data = json.load(file)
        
        while self.attributes.running:
            time.sleep(self.attributes.pos.velocity.delay)
            
            accel = 0
            decel = 0
            velcap = 0
            damage = 0
            velcap_is_default = True
            
            if not self.attributes.server_controlled: #apply movement and damage values from tiles the entity is over
                for panel in self.engine.find_panels_underneath(self.attributes.pos.x, self.attributes.pos.y):
                    if self.ent_name in panel.cfgs.material['entities']:
                        velcap_is_default = False
                        
                        if panel.cfgs.material['entities'][self.ent_name]['accelerate'] is not None:
                            accel = max(accel, panel.cfgs.material['entities'][self.ent_name]['accelerate'])
                            
                        if panel.cfgs.material['entities'][self.ent_name]['decelerate'] is not None:
                            decel += panel.cfgs.material['entities'][self.ent_name]['decelerate']
                            
                        if panel.cfgs.material['entities'][self.ent_name]['velcap'] is not None:
                            velcap = max(velcap, panel.cfgs.material['entities'][self.ent_name]['velcap'])
                            
                        if panel.cfgs.material['entities'][self.ent_name]['damage'] is not None:
                            damage += panel.cfgs.material['entities'][self.ent_name]['damage']
                
                self.increment_health(0 - (damage * self.attributes.pos.velocity.delay))
            
            if self.attributes.is_player: #read keyboard inputs for player movement
                if not accel == 0:
                    if self.engine.keybindhandler.get_state(keybind_data['movement']['up']):
                        self.attributes.pos.velocity.y -= accel
                    if self.engine.keybindhandler.get_state(keybind_data['movement']['down']):
                        self.attributes.pos.velocity.y += accel
                    if self.engine.keybindhandler.get_state(keybind_data['movement']['left']):
                        self.attributes.pos.velocity.x -= accel
                    if self.engine.keybindhandler.get_state(keybind_data['movement']['right']):
                        self.attributes.pos.velocity.x += accel
                
                if not decel == 0:
                    self.attributes.pos.velocity.x /= decel
                    self.attributes.pos.velocity.y /= decel
                
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
                
                if current_strafe is None:  #not doing any movement acceleration - apply speed cap
                    self.attributes.pos.velocity.x = max(0 - velcap, min(velcap, self.attributes.pos.velocity.x))
                    self.attributes.pos.velocity.y = max(0 - velcap, min(velcap, self.attributes.pos.velocity.y))

                else:
                    if self._strafemove.current_strafe is None or self._strafemove.current_strafe != current_strafe:
                        self._strafemove.current_mult = self._strafemove.mult
                    else:
                        self._strafemove.current_mult = max(self._strafemove.current_mult - self._strafemove.increment, 1)
                    
                    self._strafemove.current_strafe = current_strafe
                    
                    self.attributes.pos.velocity.x *= self._strafemove.current_mult
                    self.attributes.pos.velocity.y *= self._strafemove.current_mult
                
                #debug messages
                if self.engine.debug.flags['engine']['player']['pos']:
                    self.engine.debug.player_pos.set('XPOS: {:<6} YPOS: {:<6}'.format(round(self.attributes.pos.x, 2), round(self.attributes.pos.y, 2)))

                if self.engine.debug.flags['engine']['player']['speed']:
                    self.engine.debug.player_speed.set('XSPEED: {:<6} YSPEED: {:<6}'.format(round(self.attributes.pos.velocity.x, 2), round(self.attributes.pos.velocity.y, 2)))
            
            else:
                new_vel_x = self.attributes.pos.velocity.x
                new_vel_y = self.attributes.pos.velocity.x
                
                if not decel == 0:
                    new_vel_x /= decel
                    new_vel_y /= decel
                
                if not velcap_is_default: #cap velocity
                    self.attributes.pos.velocity.x = max(0 - velcap, min(velcap, new_vel_x))
                    self.attributes.pos.velocity.y = max(0 - velcap, min(velcap, new_vel_y))
            
            #apply velocity to position and store last
            old_x = self.attributes.pos.x
            old_y = self.attributes.pos.y
            
            self.attributes.pos.x += self.attributes.pos.velocity.x
            self.attributes.pos.y += self.attributes.pos.velocity.y
            
            if self.attributes.is_player: #clip player movement on tile obstacles
                has_clipped = False
                for panel in self.engine.find_panels_underneath(self.attributes.pos.x, self.attributes.pos.y):
                    if self.attributes.clip and panel.cfgs.material['clip hitbox'] and not has_clipped:
                        has_clipped = True
                        normal_angle = None
                        
                        if self.engine.hitdetection.accurate:
                            lines = []
                            last_x, last_y = panel.attributes.hitbox.geometry[len(panel.attributes.hitbox.geometry) - 1]
                            for x, y in panel.attributes.hitbox.geometry:
                                lines.append([[x, last_x], [y, last_y]])
                                last_x = x
                                last_y = y
                            
                            resultant = None
                            for line in lines:
                                res = self.engine.hitdetection.module.wrap_np_seg_intersect([[old_x, self.attributes.pos.x], [old_y, self.attributes.pos.y]], line)
                                if type(res) != bool and res is not None:
                                    resultant = res
                            
                            if resultant is None:
                                mindist = None
                                minline = None
                                for line in lines:
                                    centre = sum(line[0]) / 2, sum(line[1]) / 2
                                    dist = math.hypot(*centre)
                                    
                                    if mindist is None or dist < mindist:
                                        mindist = dist
                                        minline = line
                                
                                if mindist is not None and minline is not None:
                                    normal_angle = self.engine.angle(minline[0][1] - minline[0][0], minline[1][1] - minline[1][0])
                                    
                            else:
                                normal_angle = self.engine.angle(resultant[0][1] - resultant[0][0], resultant[1][1] - resultant[1][0])
                        
                        else:
                            normal_angle = self.engine.angle(self.attributes.pos.x - panel.attributes.pos.x, self.attributes.pos.y - panel.attributes.pos.y)
                            
                        if normal_angle is not None:
                            self.attributes.pos.x -= self.attributes.pos.velocity.x
                            self.attributes.pos.y -= self.attributes.pos.velocity.y
                            
                            incidence_angle = self.engine.angle(0 - self.attributes.pos.velocity.x, 0 - self.attributes.pos.velocity.y)
                            resultant_angle = (2 * normal_angle) - incidence_angle
                            resultant_velocity = math.hypot(self.attributes.pos.velocity.x, self.attributes.pos.velocity.y)
                            
                            self.attributes.pos.velocity.x = math.cos(resultant_angle) * resultant_velocity
                            self.attributes.pos.velocity.y = math.sin(resultant_angle) * resultant_velocity
            
            #update the entity model's position
            self.set(force = True)


class Item(Entity):
    def __init__(self, item_name, map_path, engine, layer):
        self.item_name = item_name
        
        with open(os.path.join(map_path, 'items', item_name), 'r') as file:
            item_cfg = json.load(file)
        
        super().__init__(item_cfg['model'], map_path, engine, layer, is_player = False, server_controlled = True)
        
        self.cfgs.item = item_cfg
        
        self.attributes.ticket = None