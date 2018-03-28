import tkinter as tk
import socket
import threading
import time

class Game:
    def __init__(self, canvas):
        self.canvas = canvas
        
        class server:
            mode = 'internal' #either 'internal' or 'external'
            allow_external = True
        self.server = server
        
        self.running = True        
        threading.Thread(target = self.main).start()
    
    def main(self):
        while self.running:
            time.sleep(1)
    
    def connect_to_server(self, hostname = None):
        'Connect to a server. If the hostname is None, a server will be created'
        if hostname == None:
            self.server.mode = 'internal'
        else:
            self.server.mode = 'external'
    
    def close(self):
        self.running = False

class Engine:
    pass

class Water:
    pass

class Player:
    pass

    
class Server:
    def __init__(self, port):
        class serverdata:
            host = socket.gethostname()
            port = port
        self.serverdata = serverdata
        
        self.connection = socket.socket(socket.AF_INET, socket.STREAM)
        self.connection.bind((self.serverdata.host, self.serverdata.port))
        self.connection.listen(5)

class Client:
    def __init__(self, host, port):
        class serverdata:
            host = host
            port = port
        self.serverdata = serverdata
        
        self.connection = socket.socket(socket.AF_INET, socket.STREAM)
        self.connection.connect((self.serverdata.host, self.serverdata.port))