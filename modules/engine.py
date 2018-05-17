import tkinter as tk
import sqlite3 as sql
import time
import threading

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
        
        self.running = True        
        threading.Thread(target = self.main, daemon = True).start()
    
    def main(self):
        while self.running:
            time.sleep(1)
    
    def connect_to_server(self, serverdata = None):
        'Connect to a server. If the hostname is None, a server will be created'
        if serverdata == None:
            self.server.mode = 'internal'
            self.server.name = 'localhost'
            self.server.object = mocules.networking.Server(4321)
        else:
            self.server.mode = 'external'
            self.server.name = serverdata['address']
        self.client = modules.networking.Client(self.server.name, 4321)
        self.client.send_raw('hello world!')
    
    def close(self):
        self.running = False

class Engine:
    pass

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