import json
import os
import sys
import threading

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
        self.ui = None
        
        if not os.path.isfile(os.path.join(sys.path[0], 'user', 'config.json')):
            with open(os.path.join(sys.path[0], 'user', 'default_config.json'), 'r') as file:
                with open(os.path.join(sys.path[0], 'user', 'config.json'), 'w') as writeto_file:
                    writeto_file.write(file.read())
    
        self.ui = modules.ui.UI(autostart = False)
        threading.Thread(target = self.initialise_ui).start()
        self.ui.tkthread()
    
    def initialise_ui(self):
        self.ui.wait_for_checkin()
        
        with open(os.path.join(sys.path[0], 'user', 'config.json'), 'r') as file:
            settingsdata = json.load(file)
        
        self.ui.load(self.ui.uiobjects.menu)
        self.ui.set_title('Hydrophobes')
        self.ui.set_geometry('800x600')
        if settingsdata['default window state'] in [0, 1]:
            self.ui.root.state(['normal', 'zoomed'][settingsdata['default window state']])
            self.ui.root.attributes('-fullscreen', False)
        else:
            self.ui.root.attributes('-fullscreen', True)
        
        self.ui.set_trigger('connect to server', self.connect_to_server)
        self.ui.set_trigger('create game object', self.create_game_object)
        self.ui.set_trigger('window closed', self.on_window_close)
        self.ui.set_trigger('close game', self.close_game)
        self.ui.set_trigger('edit map', self.map_edit)
        self.ui.set_trigger('new map', self.map_make_new)
        self.ui.set_trigger('start editor', self.start_editor)
        self.ui.set_trigger('close editor', self.close_editor)
        self.ui.set_trigger('quit', self.close)
        self.ui.set_trigger('host server', self.host_server)
        self.ui.set_trigger('close server', self.close_server)
    
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
            server_data['port'] = settingsdata['network']['default port']
            
        self.client = modules.networking.Client(server_data, self.ui)
        
        self.ui.load(self.ui.uiobjects.game)
    
    def host_server(self, console_frame):
        with open(os.path.join(sys.path[0], 'server', 'config.json'), 'r') as file:
            serversettingsdata = json.load(file)
        
        self.server = modules.networking.Server(serversettingsdata['network']['port'], console_frame)
    
    def close_server(self):
        pass
    
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
    
    def on_window_close(self):
        sys.exit()
    
    def close(self):
        self.ui.root.destroy()
        self.on_window_close()

if __name__ == '__main__':
    App()