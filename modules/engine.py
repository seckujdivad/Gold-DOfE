import tkinter as tk
import sqlite3 as sql
import time
import threading
import os

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
        
        self.client.recv_binds.append(self.recv_handler)
        
        self.running = True        
        threading.Thread(target = self.main, daemon = True).start()
        
        self.engine = Engine(self)
    
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

class Engine:
    def __init__(self, game):
        self.game = game
        
        class map:
            class textures:
                pass
            name = None
            cfg = None
        self.map = map
    
    def load_map(self, name):
        if os.path.isdir(os.path.join(sys.path[0], 'server', 'maps', name)):
            self.map.name = name
            with open(os.path.join(sys.path[0], 'server', 'maps', name, 'list.json'), 'r') as file:
                self.map.cfg = json.load(file)

class Water:
    pass

class Player:
    pass

class DBAccess:
    def __init__(self, address):
        self.address = address
        
        self.connection = sql.connect(self.address)
    
    def load_map(self, name):
        pass
    
    def close(self):
        self.connection.commit()
        self.connection.close()