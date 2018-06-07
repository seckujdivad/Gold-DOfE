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

import modules.networking

class Game:
    def __init__(self, canvas, client):
        self.canvas = canvas
        self.client = client
        
        class server:
            mode = 'internal' #either 'internal' or 'external'
            allow_external = True
            name = 'localhost'
        self.server = server
        
        with open(os.path.join(sys.path[0], 'user', 'config.json'), 'r') as file:
            self.settingsdict = json.load(file)
        
        self.engine = Engine(self)
        
        self.client.recv_binds.append(self.recv_handler)
        self.client.send(modules.networking.Request(command = 'var update r', subcommand = 'map'))
        
        self.message_pipe, pipe = mp.Pipe()
        self.messagedisplay = CanvasMessages(self.canvas, pipe)
        self.messagedisplay.graphical_properties.font = (self.settingsdict['hud']['chat']['font'], self.settingsdict['hud']['chat']['fontsize'])
        self.messagedisplay.graphical_properties.persist = self.settingsdict['hud']['chat']['maxlen']
        self.messagedisplay.graphical_properties.height = self.settingsdict['hud']['chat']['spacing']
        self.messagedisplay.graphical_properties.colour = self.settingsdict['hud']['chat']['colour']
        self.messagedisplay.graphical_properties.alignment = ['tl', 'tr', 'bl', 'br'][self.settingsdict['hud']['chat']['position']]
        
        self.running = True        
        threading.Thread(target = self.main, daemon = True).start()
    
    def main(self):
        while self.running:
            time.sleep(1)
    
    def close(self):
        self.running = False
        self.client.disconnect()
        self.engine.inputs.stop()
        self.engine.unload_current_map()
    
    def recv_handler(self, request):
        data = request.as_dict()
        
        if request.command == 'say':
            self.message_pipe.send(['chat', request.arguments['text']])
        elif request.command == 'load map':
            self.engine.load_map(request.arguments['map name'])
        elif request.command == 'disconnect':
            if self.running == True:
                print('connection to server interrupted')
        elif request.command == 'var update w':
            if request.subcommand == 'map':
                if not self.engine.map.name == request.arguments['map name']:
                    self.engine.load_map(request.arguments['map name'])

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
            name = None
            cfg = None
            rendermethod = None
            player = None
        self.map = map
        
        class inputs:
            keystates = {}
            delay = 0.1
            binds = {}
            cont = None
            
            @classmethod
            def mainloop(self, canvas):
                self.cont = True
                self.keystates = {}
                self.binds = {}
            
                root = canvas.nametowidget('.')
                root.bind('<KeyPress>', self.onkeypress)
                root.bind('<KeyRelease>', self.onkeyrelease)
                threading.Thread(target = self.mainthread).start()
            
            @classmethod
            def mainthread(self):
                while self.cont:
                    for keysym in self.keystates:
                        if self.keystates[keysym]:
                            if keysym in self.binds:
                                for bind in self.binds[keysym]:
                                    threading.Thread(target = bind, name = 'Function bound to {}'.format(keysym)).start()
                    time.sleep(self.delay)
            
            @classmethod
            def onkeypress(self, event):
                self.keystates[event.keysym] = True
            
            @classmethod
            def onkeyrelease(self, event):
                self.keystates[event.keysym] = False
                
            @classmethod
            def stop(self):
                self.cont = False
        self.inputs = inputs
        self.inputs.mainloop(self.game.canvas)
    
    def load_map(self, name):
        if os.path.isdir(os.path.join(sys.path[0], 'server', 'maps', name)):
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
            with open(os.path.join(sys.path[0], 'server', 'maps', name, 'list.json'), 'r') as file:
                self.map.cfg = json.load(file)
            self.game.message_pipe.send(['map load', 'Loaded map cfg'])
            
            #render base and overlay
            self.map.textures.base = self.map.rendermethod(file = os.path.join(sys.path[0], 'server', 'maps', name, self.map.cfg['background']['base']))
            self.game.message_pipe.send(['map load', 'Loaded base texture'])
            self.map.textures.overlay = self.map.rendermethod(file = os.path.join(sys.path[0], 'server', 'maps', name, self.map.cfg['background']['overlay']))
            self.game.message_pipe.send(['map load', 'Loaded overlay texture'])
            
            #add base layer
            self.map.textures.obj_base = self.game.canvas.create_image(400, 300, image = self.map.textures.base)
            self.game.message_pipe.send(['map load', 'Rendered base texture'])
            
            #add scatters
            self.map.textures.obj_scatter = []
            for i in range(int(self.map.cfg['background']['scatternum'] / len(self.map.cfg['background']['scatters']))):
                for scatter in self.map.cfg['background']['scatters']:
                    scattermdl = Model(os.path.join(sys.path[0], 'server', 'maps', name, scatter), self.map.rendermethod, self.game.canvas)
                    scattermdl.setpos(random.randint(0, 800), random.randint(0, 600))
                    self.map.textures.obj_scatter.append(scattermdl)
            self.game.message_pipe.send(['map load', 'Loaded scatters'])
            
            #load player
            self.game.message_pipe.send(['map load', 'Creating player model...'])
            self.map.player = Player(os.path.join(sys.path[0], 'server', 'maps', name, self.map.cfg['player']), self)
            self.game.message_pipe.send(['map load', 'Loaded player model'])
            self.map.player.setpos(400, 300, 0)
            self.inputs.binds['Left'] = [self.map.player.rotate_right]
            self.inputs.binds['Right'] = [self.map.player.rotate_left]
            self.inputs.binds['Up'] = [self.map.player.move_forward]
            self.game.message_pipe.send(['map load', 'Added keybinds'])
            
            #add overlay
            self.map.textures.obj_overlay = self.game.canvas.create_image(400, 300, image = self.map.textures.overlay)
            self.game.message_pipe.send(['map load', 'Rendered overlay'])
    
    def unload_current_map(self):
        if not self.map.textures.obj_scatter == []:
            for scatter in self.map.textures.obj_scatter:
                scatter.destroy()
            self.map.textures.obj_scatter = []
        if not self.map.textures.obj_base == None:
            self.game.canvas.delete(self.map.textures.obj_base)
            self.map.textures.obj_base = None
        if not self.map.textures.obj_overlay == None:
            self.game.canvas.delete(self.map.textures.obj_overlay)
            self.map.textures.obj_overlay = None
        if not self.map.player == None:
            self.map.player.model.destroy()
        self.game.message_pipe.send(['map load', 'Cleared old map assets'])

class Water:
    pass

class Player:
    def __init__(self, path, engine):
        self.path = path
        self.engine = engine
        
        class pos:
            x = 0
            y = 0
            rotation = 0
            class movement:
                rotationincrement = 10
                forwardincrement = 10
        self.pos = pos
        
        self.model = Model(path, self.engine.map.rendermethod, self.engine.game.canvas)
        self.setpos(100, 100)
    
    def setpos(self, x = None, y = None, rotation = None):
        if not x == None:
            self.pos.x = x
        if not y == None:
            self.pos.y = y
        if not rotation == None:
            self.pos.rotation = rotation % 360
        self.model.setpos(self.pos.x, self.pos.y, self.pos.rotation)
    
    def rotate_left(self):
        self.setpos(rotation = self.pos.rotation - self.pos.movement.rotationincrement)
    
    def rotate_right(self):
        self.setpos(rotation = self.pos.rotation + self.pos.movement.rotationincrement)
    
    def move_forward(self):
        self.pos.x -= math.sin(math.radians(self.pos.rotation)) * self.pos.movement.forwardincrement
        self.pos.y -= math.cos(math.radians(self.pos.rotation)) * self.pos.movement.forwardincrement
        self.setpos(self.pos.x, self.pos.y)

class Model:
    def __init__(self, path, imageloader, canvas):
        self.path = path
        self.imageloader = imageloader
        self.canvas = canvas
        
        class graphics:
            x = 0
            y = 0
            rotation = None
            prev_rotation = None
            displaytype = None
            preimgloader = None
            class flat:
                texture = None
                imgobj = None
                canvobj = None
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
            self.preimgloader = __import__('PIL.Image').Image.open
        
        with open(os.path.join(self.path, 'list.json'), 'r') as file:
            self.config = json.load(file)
        
        with open(os.path.join(sys.path[0], 'user', 'config.json'), 'r') as file:
            self.userconfig = json.load(file)
        
        #load textures
        self.graphics.displaytype = self.config['type']
        if self.graphics.displaytype == 'flat':
            self.graphics.flat.texture = self.imageloader(file = os.path.join(self.path, self.config['texture']))
        elif self.graphics.displaytype == 'stack':
            if type(self.config['textures']) == list:
                for img in self.config['textures']:
                    self.graphics.stack.textures.append(self.imageloader(file = os.path.join(self.path, img)))
            else:
                for img in os.listdir(os.path.join(self.path, 'stack')):
                    self.graphics.stack.textures.append(self.preimgloader(os.path.join(self.path, 'stack', img)))
            
            self.graphics.stack.numlayers = self.config['numlayers'][self.userconfig['graphics']['stacked model quality']]
            
            if self.graphics.stack.numlayers == len(self.graphics.stack.textures):
                self.graphics.stack.offsets.y = self.config['offsets'][1]
            else:
                self.graphics.stack.offsets.y = self.config['offsets'][1] * (len(self.graphics.stack.textures) / self.graphics.stack.numlayers)
            self.graphics.stack.offsets.x = self.config['offsets'][0]
        else:
            raise ValueError('Display type \'{}\' doesn\'t exist'.format(self.config['type']))
        self._render()
    
    def _render(self, x = None, y = None):
        if not x == None:
            self.graphics.x = x
        if not y == None:
            self.graphics.y = y
            
        if self.graphics.displaytype == 'flat':
            self.graphics.flat.canvobj = self.canvas.create_image(self.graphics.x, self.graphics.y, image = self.graphics.flat.texture)
        elif self.graphics.displaytype == 'stack':
            self.create_rotations(self.config['rotations'])
    
    def setpos(self, x = None, y = None, rotation = None):
        if not x == None:
            self.graphics.x = x
        if not y == None:
            self.graphics.y = y
        if rotation == None and self.graphics.rotation == None:
            rotation = 0
        if not rotation == None:
            self.graphics.prev_rotation = self.graphics.rotation
            self.graphics.rotation = rotation
            
        if self.graphics.displaytype == 'flat':
            self.canvas.coords(self.graphics.flat.canvobj, self.graphics.x, self.graphics.y)
        elif self.graphics.displaytype == 'stack':
            i = 0
            if not (self.graphics.prev_rotation == None or self.graphics.prev_rotation == self.graphics.rotation):
                for canvobj in self.objset_from_angle(self.graphics.prev_rotation):
                    self.canvas.coords(canvobj, self.config['offscreen'][0], self.config['offscreen'][1])
            for canvobj in self.objset_from_angle(self.graphics.rotation):
                self.canvas.coords(canvobj, self.graphics.x + (i * self.graphics.stack.offsets.x), self.graphics.y + (i * self.graphics.stack.offsets.y))
                i += 1
    
    def create_rotations(self, num_rotations):
        'Premake all canvas objects for different rotations to speed up rendering'
        
        if self.graphics.stack.numlayers == len(self.graphics.stack.textures): #find out the indexes of the images to be used
                iterator = range(len(self.graphics.stack.textures))
        else:
            iterator = []
            mult = len(self.graphics.stack.textures) / self.graphics.stack.numlayers
            for i in range(self.graphics.stack.numlayers):
                iterator.append(int(i * mult))
            print(iterator)
        
        angle_increment = 360 / num_rotations
        i = 0
        for rot in range(num_rotations):
            #create sublists
            self.graphics.stack.canvobjs.append([])
            self.graphics.stack.imgobjs.append([])
            
            angle = angle_increment * rot #precalculate angle
            
            for tex in iterator:
                loaded_image = self.imageloader(image = self.graphics.stack.textures[tex].rotate(angle))
                new_canv_obj = self.canvas.create_image(self.config['offscreen'][0], self.config['offscreen'][1], image = loaded_image)
                self.graphics.stack.canvobjs[i].append(new_canv_obj)
                self.canvas.coords(new_canv_obj, self.config['offscreen'][0], self.config['offscreen'][1])
                self.graphics.stack.imgobjs[i].append(loaded_image)
            i += 1
    
    def objset_from_angle(self, angle):
        return self.graphics.stack.canvobjs[int((angle / 360) * len(self.graphics.stack.canvobjs))]
        
    def destroy(self):
        if self.graphics.displaytype == 'flat':
            self.canvas.delete(self.graphics.flat.canvobj)
        else:
            for rotationset in self.graphics.stack.canvobjs:
                for obj in rotationset:
                    self.canvas.delete(obj)

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
    def __init__(self, canvas, pipe):
        self.canvas = canvas
        self.pipe = pipe
        
        self.messages = []
        self.running = True
        
        class graphical_properties:
            updatedelay = 0.1
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
            formatlib = {'tl': '[{0:^16}] {1}',
                         'tr': '{1} [{0:^16}]',
                         'bl': '[{0:^16}] {1}',
                         'br': '{1} [{0:^16}]'}
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
            self.messages.insert(0, {'text': displaytext, 'timestamp': time.time(), 'obj': self.canvas.create_text(0, 0, text = displaytext, fill = self.graphical_properties.colour, font = self.graphical_properties.font, anchor = self.graphical_properties.alignment_library[self.graphical_properties.alignment])})
            if len(self.messages) > self.graphical_properties.maxlen:
                for message in self.messages[self.graphical_properties.maxlen:]:
                    self.canvas.delete(message['obj'])
                self.messages = self.messages[:self.graphical_properties.maxlen]
    
    def graphics_handler(self):
        while self.running:
            todelete = []
            for i in range(len(self.messages)):
                message = self.messages[i]
                x, y = self.calc_coords(i)
                self.canvas.coords(message['obj'], x, y)
                if time.time() - message['timestamp'] > self.graphical_properties.persist:
                    self.canvas.delete(message['obj'])
                    todelete.insert(0, i)
                else:
                    self.canvas.tag_raise(message['obj'])
            for i in todelete:
                self.messages.pop(i)
            time.sleep(self.graphical_properties.updatedelay)
    
    def calc_coords(self, position):
        if self.graphical_properties.alignment == 'tl':
            return 10, 10 + (position * self.graphical_properties.height)
        elif self.graphical_properties.alignment == 'tr':
            return self.canvas.winfo_width() - 10, 10 + (position * self.graphical_properties.height)
        elif self.graphical_properties.alignment == 'bl':
            return 10, self.canvas.winfo_height() - (position * self.graphical_properties.height) - 10
        elif self.graphical_properties.alignment == 'br':
            return self.canvas.winfo_width() - 10, self.canvas.winfo_height() - (position * self.graphical_properties.height) - 10
        
    def stop(self):
        self.running = False