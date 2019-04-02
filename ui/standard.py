from tkinter import messagebox
import tkinter as tk
import os
import json
import sys
import shutil

import modules.ui

class UIMenu(modules.ui.UIObject):
    def __init__(self, frame, ui):
        super().__init__(frame, ui)
        
        self.name = 'Menu'
        self.internal_name = 'menu'
        
        #generate
        self._elements.label_title = tk.Label(self.frame, text = 'Hydrophobes', **self._styling.get(font_size = 'large', object_type = tk.Label))
        self._elements.button_editor = tk.Button(self.frame, text = 'Map editor', **self._styling.get(font_size = 'medium', object_type = tk.Button))
        self._elements.button_connect = tk.Button(self.frame, text = 'Connect to a server', **self._styling.get(font_size = 'medium', object_type = tk.Button))
        self._elements.button_host = tk.Button(self.frame, text = 'Host a server', **self._styling.get(font_size = 'medium', object_type = tk.Button))
        self._elements.button_settings = tk.Button(self.frame, text = 'Change client settings', **self._styling.get(font_size = 'medium', object_type = tk.Button))
        self._elements.button_server_settings = tk.Button(self.frame, text = 'Change server settings', **self._styling.get(font_size = 'medium', object_type = tk.Button))
        self._elements.button_quit = tk.Button(self.frame, text = 'Quit', **self._styling.get(font_size = 'medium', object_type = tk.Button))
        self._elements.label_userdata = tk.Label(self.frame, text = 'Loading...', **self._styling.get(font_size = 'small', object_type = tk.Label))
                
        self._elements.label_title.grid(row = 0, column = 0, sticky = 'NESW')
        self._elements.button_editor.grid(row = 1, column = 0, sticky = 'NESW')
        self._elements.button_connect.grid(row = 2, column = 0, sticky = 'NESW')
        self._elements.button_host.grid(row = 3, column = 0, sticky = 'NESW')
        self._elements.button_settings.grid(row = 4, column = 0, sticky = 'NESW')
        self._elements.button_server_settings.grid(row = 5, column = 0, sticky = 'NESW')
        self._elements.button_quit.grid(row = 6, column = 0, sticky = 'NESW')
        self._elements.label_userdata.grid(row = 7, column = 0, sticky = 'NESW')
        self._styling.set_weight(self.frame, 1, 8)
        
    def _on_load(self):
        with open(os.path.join(sys.path[0], 'user', 'config.json'), 'r') as file:
            settingsdict = json.load(file)
            
        pilrender_msg = settingsdict['graphics']['PILrender']
        if not pilrender_msg:
            pilrender_msg = 'False (WARNING! - disables sprite rotation)'
            
        text_ = 'Name: {}, PIL rendering: {} \nGo to settings to make sure all packages have been installed'.format(settingsdict['user']['name'], pilrender_msg)
        self._elements.label_userdata.config(text = text_)
        
        self._elements.button_editor.config(command = lambda: self._load_page('editor choose map'))
        self._elements.button_connect.config(command = lambda: self._load_page('server connect'))
        self._elements.button_host.config(command = lambda: self._load_page('server host'))
        self._elements.button_settings.config(command = lambda: self._load_page('client settings'))
        self._elements.button_server_settings.config(command = lambda: self._load_page('server settings'))
        self._elements.button_quit.config(command = lambda: self._call_trigger('quit'))
        

class UIClientSettings(modules.ui.UIObject):
    def __init__(self, frame, ui):
        super().__init__(frame, ui)
        
        self.name = 'Settings'
        self.internal_name = 'client settings'
        
        #create vars
        class chat:
            colour = tk.StringVar()
            size = tk.IntVar()
            font = tk.StringVar()
            maxlen = tk.IntVar()
            persist_time = tk.DoubleVar()
        self._vars.chat = chat
        self._vars.interps_per_second = tk.IntVar()
        self._vars.username = tk.StringVar()
        
        self._elements.settings_frame = tk.Frame(frame)
                
        self._elements.cat_general_label = tk.Label(self._elements.settings_frame, text = 'General', **self._styling.get(font_size = 'medium', object_type = tk.Label))
        self._elements.windowzoom_label = tk.Label(self._elements.settings_frame, text = 'Default window zoom', **self._styling.get(font_size = 'medium', object_type = tk.Label))
        self._elements.windowzoom_flipswitch = modules.ui.TkFlipSwitch(self._elements.settings_frame, options = [{'text': 'Windowed'}, {'text': 'Maximised'}, {'text': 'Fullscreen'}], **self._styling.get(font_size = 'medium', object_type = tk.Button))
        
        #graphics settings
        self._elements.cat_graphics_label = tk.Label(self._elements.settings_frame, text = 'Graphics', **self._styling.get(font_size = 'medium', object_type = tk.Label))
        self._elements.pilrender_label = tk.Label(self._elements.settings_frame, text = 'PIL rendering', **self._styling.get(font_size = 'medium', object_type = tk.Label))
        self._elements.pilrender_flipswitch = modules.ui.TkFlipSwitch(self._elements.settings_frame, options = [{'text': 'On'}, {'text': 'Off'}], **self._styling.get(font_size = 'medium', object_type = tk.Button))
        self._elements.mdlquality_label = tk.Label(self._elements.settings_frame, text = 'Model quality', **self._styling.get(font_size = 'medium', object_type = tk.Label))
        self._elements.mdlquality_flipswitch = modules.ui.TkFlipSwitch(self._elements.settings_frame, options = [{'text': 'Low'}, {'text': 'Medium'}, {'text': 'High'}, {'text': 'Full'}], **self._styling.get(font_size = 'medium', object_type = tk.Button))
        
        #hud settings
        self._elements.cat_hud_label = tk.Label(self._elements.settings_frame, text = 'HUD', **self._styling.get(font_size = 'medium', object_type = tk.Label))
        self._elements.chatalign_label = tk.Label(self._elements.settings_frame, text = 'Chat alignment', **self._styling.get(font_size = 'medium', object_type = tk.Label))
        self._elements.chatalign_flipswitch = modules.ui.TkFlipSwitch(self._elements.settings_frame, options = [{'text': 'Top left'}, {'text': 'Top right'}, {'text': 'Bottom left'}, {'text': 'Bottom right'}], **self._styling.get(font_size = 'medium', object_type = tk.Button))
        self._elements.chatcol_label = tk.Label(self._elements.settings_frame, text = 'Chat colour', **self._styling.get(font_size = 'medium', object_type = tk.Label))
        self._elements.chatcol_entry = tk.Entry(self._elements.settings_frame, textvariable = self._vars.chat.colour, **self._styling.get(font_size = 'medium', object_type = tk.Entry))
        self._elements.chatfont_label = tk.Label(self._elements.settings_frame, text = 'Chat font', **self._styling.get(font_size = 'medium', object_type = tk.Label))
        self._elements.chatfont_entry = tk.Entry(self._elements.settings_frame, textvariable = self._vars.chat.font, **self._styling.get(font_size = 'medium', object_type = tk.Entry))
        self._elements.chatsize_label = tk.Label(self._elements.settings_frame, text = 'Chat size', **self._styling.get(font_size = 'medium', object_type = tk.Label))
        self._elements.chatsize_spinbox = tk.Spinbox(self._elements.settings_frame, from_ = 0, to = 128, textvariable = self._vars.chat.size, **self._styling.get(font_size = 'medium', object_type = tk.Spinbox))
        self._elements.chatmaxlen_label = tk.Label(self._elements.settings_frame, text = 'Chat messages to display', **self._styling.get(font_size = 'medium', object_type = tk.Label))
        self._elements.chatmaxlen_spinbox = tk.Spinbox(self._elements.settings_frame, from_ = 0, to = 128, textvariable = self._vars.chat.maxlen, **self._styling.get(font_size = 'medium', object_type = tk.Spinbox))
        self._elements.chatpersisttime_label = tk.Label(self._elements.settings_frame, text = 'Chat persist time', **self._styling.get(font_size = 'medium', object_type = tk.Label))
        self._elements.chatpersisttime_spinbox = tk.Spinbox(self._elements.settings_frame, from_ = 0, to = 128, textvariable = self._vars.chat.persist_time, **self._styling.get(font_size = 'medium', object_type = tk.Spinbox))
        
        #network settings
        self._elements.cat_user_label = tk.Label(self._elements.settings_frame, text = 'Network', **self._styling.get(font_size = 'medium', object_type = tk.Label))
        self._elements.username_label = tk.Label(self._elements.settings_frame, text = 'Username', **self._styling.get(font_size = 'medium', object_type = tk.Label))
        self._elements.username_entry = tk.Entry(self._elements.settings_frame, textvariable = self._vars.username, **self._styling.get(font_size = 'medium', object_type = tk.Entry))
        self._elements.interp_label = tk.Label(self._elements.settings_frame, text = 'Interpolations per second', **self._styling.get(font_size = 'medium', object_type = tk.Label))
        self._elements.interp_spinbox = tk.Spinbox(self._elements.settings_frame, textvariable = self._vars.interps_per_second, from_ = 0, to = 9999, **self._styling.get(font_size = 'medium', object_type = tk.Spinbox))
        
        self._elements.button_close = tk.Button(frame, text = 'Accept', command = self._choice_accept, **self._styling.get(font_size = 'medium', object_type = tk.Button))
        self._elements.button_cancel = tk.Button(frame, text = 'Cancel', command = self._choice_cancel, **self._styling.get(font_size = 'medium', object_type = tk.Button))
        self._elements.button_reset_default = tk.Button(frame, text = 'Reset to default', command = self._choice_reset, **self._styling.get(font_size = 'medium', object_type = tk.Button))
        self._elements.button_match_requirements = tk.Button(frame, text = 'Click to install any required packages...', command = self._meet_requirements, **self._styling.get(font_size = 'medium', object_type = tk.Button))
        
        widget_row = 0
        
        self._elements.cat_general_label.grid(row = widget_row, column = 0, columnspan = 2, sticky = 'NESW')
        self._elements.windowzoom_label.grid(row = widget_row + 1, column = 0, sticky = 'NESW')
        self._elements.windowzoom_flipswitch.grid(row = widget_row + 1, column = 1, sticky = 'NESW')
        
        widget_row += 2
        
        self._elements.cat_graphics_label.grid(row = widget_row, column = 0, columnspan = 2, sticky = 'NESW')
        self._elements.pilrender_label.grid(row = widget_row + 1, column = 0, sticky = 'NESW')
        self._elements.pilrender_flipswitch.grid(row = widget_row + 1, column = 1, sticky = 'NESW')
        self._elements.mdlquality_label.grid(row = widget_row + 2, column = 0, sticky = 'NESW')
        self._elements.mdlquality_flipswitch.grid(row = widget_row + 2, column = 1, sticky = 'NESW')
        
        widget_row += 3
        
        self._elements.cat_hud_label.grid(row = widget_row, column = 0, columnspan = 2, sticky = 'NESW')
        self._elements.chatalign_label.grid(row = widget_row + 1, column = 0, sticky = 'NESW')
        self._elements.chatalign_flipswitch.grid(row = widget_row + 1, column = 1, sticky = 'NESW')
        self._elements.chatcol_label.grid(row = widget_row + 2, column = 0, sticky = 'NESW')
        self._elements.chatcol_entry.grid(row = widget_row + 2, column = 1, sticky = 'NESW')
        self._elements.chatfont_label.grid(row = widget_row + 3, column = 0, sticky = 'NESW')
        self._elements.chatfont_entry.grid(row = widget_row + 3, column = 1, sticky = 'NESW')
        self._elements.chatsize_label.grid(row = widget_row + 4, column = 0, sticky = 'NESW')
        self._elements.chatsize_spinbox.grid(row = widget_row + 4, column = 1, sticky = 'NESW')
        self._elements.chatmaxlen_label.grid(row = widget_row + 5, column = 0, sticky = 'NESW')
        self._elements.chatmaxlen_spinbox.grid(row = widget_row + 5, column = 1, sticky = 'NESW')
        self._elements.chatpersisttime_label.grid(row = widget_row + 6, column = 0, sticky = 'NESW')
        self._elements.chatpersisttime_spinbox.grid(row = widget_row + 6, column = 1, sticky = 'NESW')
        
        widget_row += 7
        
        self._elements.cat_user_label.grid(row = widget_row, column = 0, columnspan = 2, sticky = 'NESW')
        self._elements.username_label.grid(row = widget_row + 1, column = 0, sticky = 'NESW')
        self._elements.username_entry.grid(row = widget_row + 1, column = 1, sticky = 'NESW')
        self._elements.interp_label.grid(row = widget_row + 2, column = 0, sticky = 'NESW')
        self._elements.interp_spinbox.grid(row = widget_row + 2, column = 1, sticky = 'NESW')
        
        widget_row += 3
        
        self._elements.settings_frame.grid(row = 0, column = 0, columnspan = 3, sticky = 'NESW')
        self._elements.button_match_requirements.grid(row = 1, column = 0, columnspan = 3, sticky = 'NESW')
        self._elements.button_close.grid(row = 2, column = 0, sticky = 'NESW')
        self._elements.button_cancel.grid(row = 2, column = 1, sticky = 'NESW')
        self._elements.button_reset_default.grid(row = 2, column = 2, sticky = 'NESW')
        
        self._styling.set_weight(self._elements.settings_frame, 2, widget_row, dorows = False)
        frame.columnconfigure(0, weight = 1)
        frame.columnconfigure(1, weight = 1)
        frame.columnconfigure(2, weight = 1)
        frame.rowconfigure(0, weight = 1)
        
    def _on_load(self):
        self._read_settings(os.path.join(sys.path[0], 'user', 'config.json'))
    
    def _meet_requirements(self):
        messagebox.showinfo('Installing packages...', 'Installation of all required packages will now start in the console\n\nThe "install packages" button will always remain in settings because the requirements may change over time')
        print('Running pip using "requirements.txt...')
        os.system('py -m pip install -r "{}"'.format(os.path.join(sys.path[0], 'requirements.txt')))
        print('All installations are now finished!')
        messagebox.showinfo('All installations have finished!\n\nCheck the console to make sure they completed without any errors')
    
    def _read_settings(self, path):
        with open(path, 'r') as file:
            settingsdict = json.load(file)
            
        if settingsdict['graphics']['PILrender']:
            self._elements.pilrender_flipswitch.on_option_press(0, run_binds = False)
        else:
            self._elements.pilrender_flipswitch.on_option_press(1, run_binds = False)
        
        self._vars.chat.colour.set(settingsdict['hud']['chat']['colour'])
        self._vars.chat.size.set(settingsdict['hud']['chat']['fontsize'])
        self._vars.chat.font.set(settingsdict['hud']['chat']['font'])
        self._vars.chat.maxlen.set(settingsdict['hud']['chat']['maxlen'])
        self._vars.chat.persist_time.set(settingsdict['hud']['chat']['persist time'])
        self._vars.username.set(settingsdict['user']['name'])
        self._vars.interps_per_second.set(settingsdict['network']['interpolations per second'])
        
        self._elements.windowzoom_flipswitch.on_option_press(settingsdict['default window state'], run_binds = False)
        self._elements.mdlquality_flipswitch.on_option_press(settingsdict['graphics']['model quality'], run_binds = False)
        self._elements.chatalign_flipswitch.on_option_press(settingsdict['hud']['chat']['position'], run_binds = False)
    
    def _write_settings(self):
        with open(os.path.join(sys.path[0], 'user', 'config.json'), 'r') as file:
            settingsdict = json.load(file)
            
        settingsdict['graphics']['PILrender'] = [True, False][self._elements.pilrender_flipswitch.state]
        settingsdict['graphics']['model quality'] = self._elements.mdlquality_flipswitch.state
        settingsdict['hud']['chat']['position'] = self._elements.chatalign_flipswitch.state
        settingsdict['hud']['chat']['colour'] = self._vars.chat.colour.get()
        settingsdict['hud']['chat']['fontsize'] = self._vars.chat.size.get()
        settingsdict['hud']['chat']['font'] = self._vars.chat.font.get()
        settingsdict['hud']['chat']['maxlen'] = self._vars.chat.maxlen.get()
        settingsdict['hud']['chat']['persist time'] = self._vars.chat.persist_time.get()
        settingsdict['user']['name'] = self._vars.username.get()
        settingsdict['network']['interpolations per second'] = self._vars.interps_per_second.get()
        settingsdict['default window state'] = self._elements.windowzoom_flipswitch.state
        
        with open(os.path.join(sys.path[0], 'user', 'config.json'), 'w') as file:
           json.dump(settingsdict, file, sort_keys=True, indent='\t')
        
    def _choice_accept(self):
        self._write_settings()
        self._load_page('menu')
    
    def _choice_cancel(self):
        self._load_page('menu')
    
    def _choice_reset(self):
        self._read_settings(os.path.join(sys.path[0], 'user', 'default_config.json'))

class UIConnectToServer(modules.ui.UIObject):
    def __init__(self, frame, ui):
        super().__init__(frame, ui)
        
        self._vars.address = tk.StringVar()
        self._vars.port = tk.StringVar()
        self._vars.name = tk.StringVar()
        self._vars.tickrate = tk.IntVar()
        
        self._elements.serverlist_frame = tk.Frame(frame)
        self._elements.serverlist_list = tk.Listbox(self._elements.serverlist_frame, **self._styling.get(font_size = 'small', object_type = tk.Listbox))
        self._elements.serverlist_bar = tk.Scrollbar(self._elements.serverlist_frame, command = self._elements.serverlist_list.yview)
        self._elements.serverlist_list.config(yscrollcommand = self._elements.serverlist_bar.set)
        
        self._elements.button_connect = tk.Button(frame, text = 'Connect', command = self._choose_server, **self._styling.get(font_size = 'medium', object_type = tk.Button))
        self._elements.button_back = tk.Button(frame, text = 'Return to menu', command = lambda: self._load_page('menu'), **self._styling.get(font_size = 'medium', object_type = tk.Button))
        
        self._elements.addserver_frame = tk.Frame(frame)
        self._elements.addserver_choose_button = tk.Button(self._elements.addserver_frame, command = self._add_server, text = 'Add server', **self._styling.get(font_size = 'medium', object_type = tk.Button))
        self._elements.addserver_name_label = tk.Label(self._elements.addserver_frame, text = 'Name', **self._styling.get(font_size = 'small', object_type = tk.Label))
        self._elements.addserver_name_entry = tk.Entry(self._elements.addserver_frame, textvariable = self._vars.name, **self._styling.get(font_size = 'small', object_type = tk.Entry))
        self._elements.addserver_address_label = tk.Label(self._elements.addserver_frame, text = 'Address', **self._styling.get(font_size = 'small', object_type = tk.Label))
        self._elements.addserver_address_entry = tk.Entry(self._elements.addserver_frame, textvariable = self._vars.address, **self._styling.get(font_size = 'small', object_type = tk.Entry))
        self._elements.addserver_port_label = tk.Label(self._elements.addserver_frame, text = 'Port', **self._styling.get(font_size = 'small', object_type = tk.Label))
        self._elements.addserver_port_spinbox = tk.Spinbox(self._elements.addserver_frame, textvariable = self._vars.port, from_ = 1024, to = 65535, **self._styling.get(font_size = 'small', object_type = tk.Spinbox))
        self._elements.addserver_tickrate_label = tk.Label(self._elements.addserver_frame, text = 'Tickrate', **self._styling.get(font_size = 'small', object_type = tk.Label))
        self._elements.addserver_tickrate_spinbox = tk.Spinbox(self._elements.addserver_frame, textvariable = self._vars.tickrate, from_ = 1, to = 1024, **self._styling.get(font_size = 'small', object_type = tk.Spinbox))
        self._elements.addserver_islocal_flipswitch = modules.ui.TkFlipSwitch(self._elements.addserver_frame, options = [{'text': 'Local machine (host server)'}, {'text': 'Open to LAN'}], **self._styling.get(font_size = 'small', object_type = tk.Button))
        
        self._elements.serverlist_bar.pack(side = tk.RIGHT, fill = tk.Y)
        self._elements.serverlist_list.pack(side = tk.LEFT, fill = tk.BOTH, expand = True)
        
        self._elements.serverlist_frame.grid(row = 0, column = 0, columnspan = 2, sticky = 'NESW')
        self._elements.button_back.grid(row = 1, column = 0, sticky = 'NESW')
        self._elements.button_connect.grid(row = 1, column = 1, sticky = 'NESW')
        self._elements.addserver_frame.grid(row = 2, column = 0, columnspan = 2, sticky = 'NESW')
        
        self._elements.addserver_name_label.grid(row = 0, column = 0, sticky = 'NESW')
        self._elements.addserver_name_entry.grid(row = 0, column = 1, sticky = 'NESW')
        self._elements.addserver_address_label.grid(row = 1, column = 0, sticky = 'NESW')
        self._elements.addserver_address_entry.grid(row = 1, column = 1, sticky = 'NESW')
        self._elements.addserver_port_label.grid(row = 2, column = 0, sticky = 'NESW')
        self._elements.addserver_port_spinbox.grid(row = 2, column = 1, sticky = 'NESW')
        self._elements.addserver_tickrate_label.grid(row = 3, column = 0, sticky = 'NESW')
        self._elements.addserver_tickrate_spinbox.grid(row = 3, column = 1, sticky = 'NESW')
        self._elements.addserver_islocal_flipswitch.grid(row = 4, column = 0, columnspan = 2, sticky = 'NESW')
        self._elements.addserver_choose_button.grid(row = 0, column = 2, rowspan = 4, sticky = 'NESW')
        
        self._styling.set_weight(frame, 2, 4)
        frame.rowconfigure(1, weight = 0)
        frame.rowconfigure(2, weight = 0)
        frame.rowconfigure(3, weight = 0)
        
        self._styling.set_weight(self._elements.addserver_frame, 3, 4)
        
        self._elements.serverlist_list.bind('<Return>', self._choose_server)
        
    def _on_load(self):
        self._populate_server_list()
        
        with open(os.path.join(sys.path[0], 'user', 'config.json')) as file:
            settingsdata = json.load(file)
        
        self._vars.tickrate.set(settingsdata['network']['default tickrate'])
        self._vars.port.set(settingsdata['network']['default port'])
    
    def _populate_server_list(self):
        with open(os.path.join(sys.path[0], 'user', 'config.json')) as file:
            settingsdata = json.load(file)
            
        self._elements.serverlist_list.delete(0, tk.END)
        
        formatter = '{} ({}:{}){}'
        for server in settingsdata['network']['servers']:
            if server['port'] == 'normal':
                server['port'] = settingsdata['network']['default port']
                
            if server['internal']:
                additional_text = ' - limited to local network'
                
            else:
                additional_text = ''
                
            self._elements.serverlist_list.insert(tk.END, formatter.format(server['name'], server['address'], server['port'], additional_text))
    
    def _choose_server(self, event = None):
        curselection = self._elements.serverlist_list.curselection()
        if not curselection == ():
            with open(os.path.join(sys.path[0], 'user', 'config.json')) as file:
                settingsdata = json.load(file)
                
            self._call_trigger('connect to server', [settingsdata['network']['servers'][curselection[0]]])
    
    def _add_server(self):
        with open(os.path.join(sys.path[0], 'user', 'config.json')) as file:
            settingsdata = json.load(file)
            
        sv_dict = {'address': self._vars.address.get(),
                   'internal': not bool(self._elements.addserver_islocal_flipswitch.state),
                   'name': self._vars.name.get(),
                   'port': self._vars.port.get(),
                   'tickrate': self._vars.tickrate.get()}
        try:
            sv_dict['port'] = int(sv_dict['port'])
            
        except ValueError: #is a word (normal), do nothing
            sv_dict['port'] = 'normal'
            
        settingsdata['network']['servers'].append(sv_dict)
        
        with open(os.path.join(sys.path[0], 'user', 'config.json'), 'w') as file:
            json.dump(settingsdata, file, sort_keys = True, indent = '\t')
    
        self._populate_server_list()
        self._vars.address.set('')
        self._vars.name.set('')
        self._vars.tickrate.set(settingsdata['network']['default tickrate'])
        self._vars.port.set(settingsdata['network']['default port'])

class UIGame(modules.ui.UIObject):
    def __init__(self, frame, ui):
        super().__init__(frame, ui)
        
        self.name = 'Game'
        self.internal_name = 'game'
        
        #create UI elements
        self._elements.canvas = tk.Canvas(frame, width = 800, height = 600, bg = 'purple', **self._styling.get(font_size = 'medium', object_type = tk.Canvas))
                
        self._elements.canvas.grid(row = 0, column = 0)
        
        self._styling.set_weight(frame, 1, 1)
        frame.rowconfigure(1, weight = 0)
    
    def _on_load(self):
        self._call_trigger('create game object', [self._elements.canvas])
        
        #set keybinds for returning to the menu
        with open(os.path.join(sys.path[0], 'user', 'keybinds.json'), 'r') as file:
            keybinds_data = json.load(file)
            
        if type(keybinds_data['window']['return to menu']) == str:
            keybinds_data['window']['return to menu'] = [keybinds_data['window']['return to menu']]
            
        for key in keybinds_data['window']['return to menu']:
            self._elements.canvas.bind('<{}>'.format(key), lambda: self._load_page('menu'))
    
    def _on_close(self):
        self._call_trigger('close game')
        self._call_trigger('close server')

class UIEditorChooseFile(modules.ui.UIObject):
    def __init__(self, frame, ui):
        super().__init__(frame, ui)
        
        self.name = 'Editor - Choose map'
        self.internal_name = 'editor choose map'
        
        #create UI elements
        self._elements.listbox_frame = tk.Frame(frame)
        self._elements.listbox_box = tk.Listbox(self._elements.listbox_frame, **self._styling.get(font_size = 'small', object_type = tk.Listbox))
        self._elements.listbox_bar = tk.Scrollbar(self._elements.listbox_frame, command = self._elements.listbox_box.yview)
        self._elements.listbox_box.config(yscrollcommand = self._elements.listbox_bar.set)
        
        self._elements.listbox_bar.pack(side = tk.RIGHT, fill = tk.Y)
        self._elements.listbox_box.pack(side = tk.LEFT, fill = tk.BOTH, expand = True)
        
        self._elements.entry_mapname = tk.Entry(frame, **self._styling.get(font_size = 'medium', object_type = tk.Entry))
        self._elements.button_new = tk.Button(frame, text = 'Create new map', command = self._create_new_map, **self._styling.get(font_size = 'medium', object_type = tk.Button))
        self._elements.button_choose = tk.Button(frame, text = 'Open map', command = self._open_map, **self._styling.get(font_size = 'medium', object_type = tk.Button))
        self._elements.button_go_back = tk.Button(frame, text = 'Return to menu', command = lambda: self._load_page('menu'), **self._styling.get(font_size = 'medium', object_type = tk.Button))
        
        self._elements.listbox_frame.grid(row = 0, column = 0, columnspan = 4, sticky = 'NESW')
        
        self._elements.entry_mapname.grid(row = 1, column = 0, sticky = 'NESW')
        self._elements.button_new.grid(row = 1, column = 1, sticky = 'NESW')
        self._elements.button_choose.grid(row = 1, column = 2, sticky = 'NESW')
        self._elements.button_go_back.grid(row = 1, column = 3, sticky = 'NESW')
        
        self._styling.set_weight(frame, 4, 2)
        frame.rowconfigure(1, weight = 0)
        
        self._elements.listbox_box.bind('<Return>', self._open_map())
        
    def _on_load(self):
        self._elements.listbox_box.delete(0, tk.END)
        
        for name in os.listdir(os.path.join(sys.path[0], 'server', 'maps')):
            if (not name.startswith('_')) and os.path.isdir(os.path.join(sys.path[0], 'server', 'maps', name)):
                self._elements.listbox_box.insert(tk.END, name)
    
    def _open_map(self, event = None):
        index = self._elements.listbox_box.curselection()
        if type(index[0]) == int: #if there is a selection
            map_name = self._elements.listbox_box.get(index[0])
            self._call_trigger('edit map', [map_name])
    
    def _create_new_map(self):
        if self._elements.entry_mapname.get() == '':
            messagebox.showerror('Error while creating new map', 'You must enter a map name')
            
        elif os.path.isdir(os.path.join(sys.path[0], 'server', 'maps', self._elements.entry_mapname.get())):
            messagebox.showerror('Error while creating new map', 'The map name "{}" is already in use'.format(self._elements.entry_mapname.get()))
            
        else:
            shutil.copytree('_template', self._elements.entry_mapname.get())

class UIEditor(modules.ui.UIObject):
    def __init__(self, frame, ui):
        super().__init__(frame, ui)
        
        self.name = 'Editor'
        self.internal_name = 'editor'
    
    def _on_load(self):
        self._call_trigger('start editor', [self])
    
    def _on_close(self):
        self._call_trigger('close editor')

class UIServerSettings(modules.ui.UIObject):
    def __init__(self, frame, ui):
        super().__init__(frame, ui)
        
        self.name = 'Server settings'
        self.internal_name = 'server settings'
        
        self._vars.tickrate = tk.IntVar()
        self._vars.port = tk.IntVar()
        
        #create UI elements
        self._elements.settings_frame = tk.Frame(frame)
        
        widget_row = 0
        
        #network
        self._elements.cat_network = tk.Label(self._elements.settings_frame, text = 'Network', **self._styling.get(font_size = 'medium', object_type = tk.Label))
        self._elements.hitbox_precision_label = tk.Label(self._elements.settings_frame, text = 'Hitbox precision', **self._styling.get(font_size = 'medium', object_type = tk.Label))
        self._elements.hitbox_precision_flipswitch = modules.ui.TkFlipSwitch(self._elements.settings_frame, options = [{'text': 'Low (stock python)'}, {'text': 'High (requires numpy)'}], **self._styling.get(font_size = 'medium', object_type = tk.Button))
        self._elements.tickrate_label = tk.Label(self._elements.settings_frame, text = 'Tickrate', **self._styling.get(font_size = 'medium', object_type = tk.Label))
        self._elements.tickrate_spinbox = tk.Spinbox(self._elements.settings_frame, from_ = 1, to = 1024, textvariable = self._vars.tickrate, **self._styling.get(font_size = 'medium', object_type = tk.Spinbox))
        self._elements.port_label = tk.Label(self._elements.settings_frame, text = 'Port', **self._styling.get(font_size = 'medium', object_type = tk.Label))
        self._elements.port_spinbox = tk.Spinbox(self._elements.settings_frame, from_ = 1024, to = 49151, textvariable = self._vars.port, **self._styling.get(font_size = 'medium', object_type = tk.Spinbox))
        
        self._elements.cat_network.grid(row = widget_row, column = 0, columnspan = 2, sticky = 'NESW')
        self._elements.hitbox_precision_label.grid(row = widget_row + 1, column = 0, sticky = 'NESW')
        self._elements.hitbox_precision_flipswitch.grid(row = widget_row + 1, column = 1, sticky = 'NESW')
        self._elements.tickrate_label.grid(row = widget_row + 2, column = 0, sticky = 'NESW')
        self._elements.tickrate_spinbox.grid(row = widget_row + 2, column = 1, sticky = 'NESW')
        self._elements.port_label.grid(row = widget_row + 3, column = 0, sticky = 'NESW')
        self._elements.port_spinbox.grid(row = widget_row + 3, column = 1, sticky = 'NESW')
        
        widget_row += 4
        
        #functional buttons
        self._elements.button_close = tk.Button(frame, text = 'Accept', command = self._choice_accept, **self._styling.get(font_size = 'medium', object_type = tk.Button))
        self._elements.button_cancel = tk.Button(frame, text = 'Cancel', command = self._choice_cancel, **self._styling.get(font_size = 'medium', object_type = tk.Button))
        self._elements.button_reset_default = tk.Button(frame, text = 'Reset to default', command = self._choice_reset, **self._styling.get(font_size = 'medium', object_type = tk.Button))
        
        self._elements.settings_frame.grid(row = 0, column = 0, columnspan = 3, sticky = 'NESW')
        self._elements.button_close.grid(row = 2, column = 0, sticky = 'NESW')
        self._elements.button_cancel.grid(row = 2, column = 1, sticky = 'NESW')
        self._elements.button_reset_default.grid(row = 2, column = 2, sticky = 'NESW')
        
        #set weights
        self._styling.set_weight(self._elements.settings_frame, 2, widget_row, dorows = False)
        frame.columnconfigure(0, weight = 1)
        frame.columnconfigure(1, weight = 1)
        frame.columnconfigure(2, weight = 1)
        frame.rowconfigure(0, weight = 1)
        
    def _on_load(self):
        self._fetch_settings(os.path.join(sys.path[0], 'server', 'config.json'))
    
    def _fetch_settings(self, path):
        with open(path, 'r') as file:
            settingsdict = json.load(file)
        
        self._elements.hitbox_precision_flipswitch.on_option_press(settingsdict['network']['accurate hit detection'])
        self._vars.tickrate.set(settingsdict['network']['tickrate'])
        self._vars.port.set(settingsdict['network']['port'])
    
    def _push_settings(self, path):
        with open(path, 'r') as file:
            settingsdict = json.load(file)
        
        settingsdict['network']['accurate hit detection'] = bool(self._elements.hitbox_precision_flipswitch.state)
        settingsdict['network']['tickrate'] = int(self._vars.tickrate.get())
        settingsdict['network']['port'] = int(self._vars.port.get())
        
        with open(path, 'w') as file:
            json.dump(settingsdict, file, sort_keys=True, indent='\t')
    
    def _choice_accept(self):
        self._push_settings(os.path.join(sys.path[0], 'server', 'config.json'))
    
    def _choice_reset(self):
        self._fetch_settings(os.path.join(sys.path[0], 'server', 'default_config.json'))
    
    def _choice_cancel(self):
        self._load_page('menu')