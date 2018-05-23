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
                scatters = []
                base = None
                overlay = None
                
                obj_scatter = []
                obj_base = None
                obj_overlay = None
            name = None
            cfg = None
            rendermethod = None
        self.map = map
    
    def load_map(self, name):
        if os.path.isdir(os.path.join(sys.path[0], 'server', 'maps', name)):
            with open(os.path.join(sys.path[0], 'user', 'config.json'), 'r') as file:
                self.map.settingscfg = json.load(file)
                
            if self.map.settingscfg['graphics']['PILrender']:
                self.map.rendermethod = __import__('PIL').ImageTk.PhotoImage
            else:
                self.map.rendermethod = tk.PhotoImage
        
            if not self.map.textures.obj_scatter == []:
                for scatter in self.map.textures.obj_scatter:
                    self.game.canvas.delete(scatter)
            if not self.map.textures.obj_base == None:
                self.game.canvas.delete(self.map.textures.obj_base)
            if not self.map.textures.obj_overlay == None:
                self.game.canvas.delete(self.map.textures.obj_overlay)
            
            self.map.name = name
            with open(os.path.join(sys.path[0], 'server', 'maps', name, 'list.json'), 'r') as file:
                self.map.cfg = json.load(file)
            
            self.map.textures.base = self.map.rendermethod(file = os.path.join(sys.path[0], 'server', 'maps', name, self.map.cfg['background']['base']))
            self.map.textures.overlay = self.map.rendermethod(file = os.path.join(sys.path[0], 'server', 'maps', name, self.map.cfg['background']['overlay']))
            
            self.map.textures.obj_base = self.game.canvas.create_image(400, 300, image = self.map.textures.base)
            
            for i in range(int(self.map.cfg['background']['scatternum'] / len(self.map.cfg['background']['scatters']))):
                for scatter in self.map.cfg['background']['scatters']:
                    scattermdl = Model(os.path.join(sys.path[0], 'server', 'maps', name, scatter), self.map.rendermethod, self.game.canvas)
                    scattermdl.setpos(random.randint(0, 800), random.randint(0, 600))
                    self.map.textures.obj_scatter.append(scattermdl)
            
            self.map.textures.obj_overlay = self.game.canvas.create_image(400, 300, image = self.map.textures.overlay)

class Water:
    pass

class Player:
    pass

class Model:
    def __init__(self, path, imageloader, canvas):
        self.path = path
        self.imageloader = imageloader
        self.canvas = canvas
        
        class graphics:
            x = 0
            y = 0
            displaytype = None
            class flat:
                texture = None
                imgobj = None
            class stack:
                pass
        self.graphics = graphics
        
        with open(os.path.join(self.path, 'list.json'), 'r') as file:
            self.config = json.load(file)
        
        self.graphics.displaytype = self.config['type']
        if self.graphics.displaytype == 'flat':
            self.graphics.flat.texture = self.imageloader(file = os.path.join(self.path, self.config['texture']))
        else:
            raise ValueError('Display type \'{}\' doesn\'t exist'.format(self.config['type']))
        self._render()
    
    def _render(self, x = None, y = None):
        if not x == None:
            self.graphics.x = x
        if not y == None:
            self.graphics.y = y
        if self.graphics.displaytype == 'flat':
            self.graphics.flat.imgobj = self.canvas.create_image(self.graphics.x, self.graphics.y, image = self.graphics.flat.texture)
    
    def setpos(self, x = None, y = None):
        if not x == None:
            self.graphics.x = x
        if not y == None:
            self.graphics.y = y
        if self.graphics.displaytype == 'flat':
            self.canvas.coords(self.graphics.flat.imgobj, self.graphics.x, self.graphics.y)

class DBAccess:
    def __init__(self, address):
        self.address = address
        
        self.connection = sql.connect(self.address)
    
    def load_map(self, name):
        pass
    
    def close(self):
        self.connection.commit()
        self.connection.close()