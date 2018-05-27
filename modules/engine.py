import tkinter as tk
import sqlite3 as sql
import time
import threading
import os
import sys
import json
import random

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
            self.map.player.setpos(400, 300)
            
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
        self.pos = pos
        
        self.model = Model(path, self.engine.map.rendermethod, self.engine.game.canvas)
        self.setpos()
    
    def setpos(self, x = None, y = None):
        if not x == None:
            self.pos.x = x
        if not y == None:
            self.pos.y = y
        self.model.setpos(self.pos.x, self.pos.y)

class Model:
    def __init__(self, path, imageloader, canvas):
        self.path = path
        self.imageloader = imageloader
        self.canvas = canvas
        
        class graphics:
            x = 0
            y = 0
            rotation = 0
            displaytype = None
            class flat:
                texture = None
                imgobj = None
                canvobj = None
            class stack:
                class offsets:
                    x = 0
                    y = -0.8
                textures = []
                imgobjs = []
                canvobjs = []
        self.graphics = graphics
        
        with open(os.path.join(self.path, 'list.json'), 'r') as file:
            self.config = json.load(file)
        
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
                    self.graphics.stack.textures.append(self.imageloader(file = os.path.join(self.path, 'stack', img)))
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
            for tex in self.graphics.stack.textures:
                self.graphics.stack.canvobjs.append(self.canvas.create_image(self.graphics.x, self.graphics.y, image = tex))
    
    def setpos(self, x = None, y = None, rotation = None):
        if not x == None:
            self.graphics.x = x
        if not y == None:
            self.graphics.y = y
            
        if self.graphics.displaytype == 'flat':
            self.canvas.coords(self.graphics.flat.canvobj, self.graphics.x, self.graphics.y)
        elif self.graphics.displaytype == 'stack':
            i = 0
            for canvobj in self.graphics.stack.canvobjs:
                self.canvas.coords(canvobj, self.graphics.x + (i * self.graphics.stack.offsets.x), self.graphics.y + (i * self.graphics.stack.offsets.y))
                i += 1

class DBAccess:
    def __init__(self, address):
        self.address = address
        
        self.connection = sql.connect(self.address)
    
    def load_map(self, name):
        pass
    
    def close(self):
        self.connection.commit()
        self.connection.close()