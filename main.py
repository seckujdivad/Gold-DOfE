'''Use blender to create images to use as 3d voxel layers: https://blendersushi.blogspot.co.uk/2012/01/volumetric-slicing-3d-object-using.html'''

import json
import os
import sys

import modules.ui
import modules.engine
import modules.logging
import modules.networking

class App:
    def __init__(self):
        self.ui = modules.ui.UI()
        self.ui.load(self.ui.uiobjects.menu)
        self.ui.set_title('Hydrophobes')
        self.ui.set_geometry('800x600')
        
        self.ui.set_trigger('connect to server', self.connect_to_server)
        self.ui.set_trigger('create game object', self.create_game_object)
        self.ui.set_trigger('window closed', self.close)
        self.ui.set_trigger('close game', self.close_game)
    
    def connect_to_server(self, server_data):
        with open(os.path.join(sys.path[0], 'user', 'config.json'), 'r') as file:
            settingsdata = json.load(file)
        
        with open(os.path.join(sys.path[0], 'server', 'config.json'), 'r') as file:
            serversettingsdata = json.load(file)
        
        if server_data['internal']:
            if server_data['port'] == 'normal':
                self.server = modules.networking.Server(serversettingsdata['network']['port'])
            else:
                self.server = modules.networking.Server(server_data['port'])
                
        if server_data['port'] == 'normal':
            self.client = modules.networking.Client(server_data['address'], settingsdata['network']['default port'])
        else:
            self.client = modules.networking.Client(server_data['address'], server_data['port'])
        
        self.ui.load(self.ui.uiobjects.game)
    
    def create_game_object(self, canvas):
        self.game = modules.engine.Game(canvas, self.client)
        
    def close_game(self):
        self.game.close()
    
    def close(self):
        print('closing')
        sys.exit()

if __name__ == '__main__':
    App()