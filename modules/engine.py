import tkinter as tk
import sqlite3 as sql
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
        
        self.engine = Engine(self)
        
        self.client.recv_binds.append(self.recv_handler)
        
        self.running = True        
        threading.Thread(target = self.main, daemon = True).start()
    
    def main(self):
        while self.running:
            time.sleep(1)
    
    def close(self):
        self.running = False
    
    def recv_handler(self, request):
        data = request.as_dict()
        
        if request.command == 'say':
            print(request.arguments['text'])
        elif request.command == 'load map':
            print('map:', request.arguments['map name'])
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
            
            @classmethod
            def mainloop(self, canvas):
                root = canvas.nametowidget('.')
                root.bind('<KeyPress>', self.onkeypress)
                root.bind('<KeyRelease>', self.onkeyrelease)
                threading.Thread(target = self.mainthread).start()
            
            @classmethod
            def mainthread(self):
                while True:
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
            else:
                self.map.rendermethod = tk.PhotoImage
        
            #delete old scatters, background and overlays
            if not self.map.textures.obj_scatter == []:
                for scatter in self.map.textures.obj_scatter:
                    self.game.canvas.delete(scatter)
            if not self.map.textures.obj_base == None:
                self.game.canvas.delete(self.map.textures.obj_base)
            if not self.map.textures.obj_overlay == None:
                self.game.canvas.delete(self.map.textures.obj_overlay)
            
            #open map cfg
            self.map.name = name
            with open(os.path.join(sys.path[0], 'server', 'maps', name, 'list.json'), 'r') as file:
                self.map.cfg = json.load(file)
            
            #render base and overlay
            self.map.textures.base = self.map.rendermethod(file = os.path.join(sys.path[0], 'server', 'maps', name, self.map.cfg['background']['base']))
            self.map.textures.overlay = self.map.rendermethod(file = os.path.join(sys.path[0], 'server', 'maps', name, self.map.cfg['background']['overlay']))
            
            #add base layer
            self.map.textures.obj_base = self.game.canvas.create_image(400, 300, image = self.map.textures.base)
            
            #add scatters
            self.map.textures.obj_scatter = []
            for i in range(int(self.map.cfg['background']['scatternum'] / len(self.map.cfg['background']['scatters']))):
                for scatter in self.map.cfg['background']['scatters']:
                    scattermdl = Model(os.path.join(sys.path[0], 'server', 'maps', name, scatter), self.map.rendermethod, self.game.canvas)
                    scattermdl.setpos(random.randint(0, 800), random.randint(0, 600))
                    self.map.textures.obj_scatter.append(scattermdl)
            
            #load player
            self.map.player = Player(os.path.join(sys.path[0], 'server', 'maps', name, self.map.cfg['player']), self)
            self.map.player.setpos(400, 300, 0)
            self.inputs.binds['Left'] = [self.map.player.rotate_right]
            self.inputs.binds['Right'] = [self.map.player.rotate_left]
            self.inputs.binds['Up'] = [self.map.player.move_forward]
            
            #add overlay
            self.map.textures.obj_overlay = self.game.canvas.create_image(400, 300, image = self.map.textures.overlay)

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

class DBAccess:
    def __init__(self, address):
        self.address = address
        
        self.connection = sql.connect(self.address)
    
    def load_map(self, name):
        pass
    
    def close(self):
        self.connection.commit()
        self.connection.close()