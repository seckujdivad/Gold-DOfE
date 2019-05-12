import json
import os
import sys
import threading

import modules.ui
import modules.engine
import modules.logging
import modules.networking
import modules.editor
import modules.netclients

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
        
        if not os.path.isfile(os.path.join(sys.path[0], 'user', 'debug.json')):
            with open(os.path.join(sys.path[0], 'user', 'default_debug.json'), 'r') as file:
                with open(os.path.join(sys.path[0], 'user', 'debug.json'), 'w') as writeto_file:
                    writeto_file.write(file.read())
    
        self.ui = modules.ui.UI(autostart = False)
        threading.Thread(target = self.initialise_ui).start()
        self.ui.tkthread()
    
    def initialise_ui(self):
        self.ui.wait_for_checkin()
        
        with open(os.path.join(sys.path[0], 'user', 'config.json'), 'r') as file:
            settingsdata = json.load(file)
        
        self.ui.load('menu')
        self.ui.set_base_title('Hydrophobes')
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

        self.ui.set_trigger('request client', self.get_network_client)
    
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
            
        self.client = modules.netclients.Client(server_data, self.ui)
        
        self.ui.load('server connected')
    
    def host_server(self, console_frame):
        with open(os.path.join(sys.path[0], 'server', 'config.json'), 'r') as file:
            serversettingsdata = json.load(file)
        
        self.server = modules.networking.Server(serversettingsdata['network']['port'], console_frame)
    
    def close_server(self):
        pass
    
    def create_game_object(self, canvas):
        self.game = modules.engine.Game(canvas, self.client, self.ui)
        
    def close_game(self):
        self.game.close()
    
    def map_edit(self, map_name):
        self.editor_mapname = map_name
        self.ui.load('editor')
    
    def map_make_new(self, map_name):
        pass
    
    def start_editor(self, page):
        self.editor = modules.editor.Editor(page)
        self.editor.load(self.editor_mapname)
    
    def close_editor(self):
        self.editor.close()
    
    def on_window_close(self):
        with open(os.path.join(sys.path[0], 'user', 'config.json'), 'r') as file:
            settingsdata = json.load(file)
        
        if settingsdata['force close']: #recommended - not all threads close when this is turned off (hopefully this will be fixed in the future)
            os._exit(0)
        else:
            sys.exit(0)
    
    def get_network_client(self):
        return self.client
    
    def close(self):
        self.ui.root.destroy()
        self.on_window_close()

if __name__ == '__main__':
    App()