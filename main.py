import json
import os
import sys

import modules.ui
import modules.engine
import modules.logging
import modules.networking
import modules.editor

class App:
    def __init__(self):
        self.editor = None
        self.game = None
        self.client = None
        self.server = None
    
        self.ui = modules.ui.UI()
        self.ui.load(self.ui.uiobjects.menu)
        self.ui.set_title('Hydrophobes')
        self.ui.set_geometry('800x600')
        
        self.ui.set_trigger('connect to server', self.connect_to_server)
        self.ui.set_trigger('create game object', self.create_game_object)
        self.ui.set_trigger('window closed', self.close)
        self.ui.set_trigger('close game', self.close_game)
        self.ui.set_trigger('edit map', self.map_edit)
        self.ui.set_trigger('new map', self.map_make_new)
        self.ui.set_trigger('start editor', self.start_editor)
        self.ui.set_trigger('close editor', self.close_editor)
        
        self.ui.root.state('zoomed')
    
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
    
    def map_edit(self, map_name):
        self.editor_mapname = map_name
        self.ui.load(self.ui.uiobjects.editor)
    
    def map_make_new(self, map_name):
        pass
    
    def start_editor(self, frame, pagemethods):
        self.editor = modules.editor.Editor(frame, pagemethods)
        self.editor.load(self.editor_mapname)
    
    def close_editor(self):
        self.editor.close()
    
    def close(self):
        print('closing')
        sys.exit()

if __name__ == '__main__':
    App()