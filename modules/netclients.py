from tkinter import messagebox
import socket
import threading
import json

from modules.networking import Request

class Client:
    def __init__(self, server_data, ui):
        class serverdata:
            raw = server_data
            host = raw['address']
            port = raw['port']
        self.serverdata = serverdata
        
        self.ui = ui
        
        self.recv_binds = [] #functions to be called when data is received
        
        self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        try:
            self.connection.connect((self.serverdata.host, self.serverdata.port))
        except ConnectionRefusedError:
            messagebox.showerror('Connection refused', 'The connection was refused by the target machine. Make sure that the IP you are trying to connect to has a server running')
            raise ConnectionRefusedError()
        except socket.gaierror:
            messagebox.showerror('Address not found', 'The server address could not be found. Check it for misspellings and make sure that it is accessible on your network')
            raise socket.gaierror()
        
        threading.Thread(target = self.recv_loop, name = 'Client receiver loop').start()
    
    def send_raw(self, text):
        self.connection.send(text.encode())
    
    def send(self, data):
        self.send_raw(data.as_json())
    
    def recv_loop(self):
        cont = True
        while cont:
            reqs = []
            try:
                data = self.connection.recv(4096).decode('UTF-8')
                
                #unpack the data - often will get multiple dictionaries
                escape_level = 0
                output = []
                current_string = ''
                for char in data:
                    if char == '{':
                        escape_level += 1
                    elif char == '}':
                        escape_level -= 1
                    current_string += char
                    if escape_level == 0 and not len(current_string) == 0:
                        output.append(current_string)
                        current_string = ''
                
                for json_data in output:
                    reqs.append(Request(json_data))
            except ConnectionAbortedError:
                reqs = [Request(command = 'disconnect')]
                cont = False
            except json.decoder.JSONDecodeError:
                pass
            for bind in self.recv_binds:
                for req in reqs:
                    bind(req)
    
    def disconnect(self):
        self.connection.close()