from tkinter import messagebox
from typing import Type, Union
import tkinter as tk
import threading
import time
import json
import os
import sys
import functools
import shutil

class UI:
    def __init__(self, autostart = True):
        self.ready = {'tkthread': False}
        self.triggers = {}
        
        self.root = None
        
        if autostart:
            threading.Thread(target = self.tkthread).start() #start tkinter window in separate thread
            self.wait_for_checkin()
    
    def wait_for_checkin(self):
        clearpass = False
        while not clearpass:  # wait for all threads to check in before returning
            time.sleep(0.05)
            clearpass = True
            for name in self.ready:
                if not self.ready[name]:
                    clearpass = False
    
    def tkthread(self):
        self.root = tk.Tk() #create tkinter window
        
        class styling: #consistent styling tools
            @classmethod
            def get(self, font_size = 'medium', object_type: Union[Type[tk.Label],
                                                                   Type[tk.Button],
                                                                   Type[tk.Canvas],
                                                                   Type[tk.Scrollbar],
                                                                   Type[tk.Frame],
                                                                   Type[tk.Text],
                                                                   Type[tk.Entry],
                                                                   Type[tk.Spinbox],
                                                                   Type[tk.Listbox]] = tk.Label, relief = 'default', fonts = 'default') -> dict:
                'Get styling for a specific type of widget'
                output = {}
                if object_type == tk.Button:
                    output['overrelief'] = self.reliefs[relief]['overrelief']
                
                output['relief'] = self.reliefs[relief]['relief']
            
                if not object_type in [tk.Canvas, tk.Scrollbar]:
                    output['font'] = self.fonts[fonts][font_size]
                
                return output
            
            @classmethod
            def set_weight(self, frame, width, height, weight_ = 1, dorows = True, docolumns = True):
                'Set uniform weighting across a frame'
                for cheight in range(height):
                    if dorows:
                        frame.rowconfigure(cheight, weight = weight_)
                    for cwidth in range(width):
                        if docolumns:
                            frame.columnconfigure(cwidth, weight = weight_)
            fonts = {}
            reliefs = {}
            with open(os.path.join(sys.path[0], 'user', 'config.json'), 'r') as file:
                settingsdata = json.load(file)
            for style_type in settingsdata['styling']:
                fonts[style_type] = settingsdata['styling'][style_type]['fonts']
                reliefs[style_type] = settingsdata['styling'][style_type]['reliefs']
        self.styling = styling        
        
        class main: #store data to do with ui
            title = ''
            geometry = None
            current = None
            page_frame = tk.Frame(self.root)
            page_frame.pack(fill = tk.BOTH, expand = True)
            
            class connect_server:
                config = {'name': 'Connect'}
                
                @classmethod
                def on_load(self):
                    self.frame.pack(fill = tk.BOTH, expand = True)
                    self.populate_server_list()
                    
                    self.serverlist_list.bind('<Return>', self.choose_server)
                    self.addserver_choose_button.config(command = self.add_server)
                    
                    self.button_back.config(command = self.return_to_menu)
                    self.button_connect.config(command = self.choose_server)
                    
                    with open(os.path.join(sys.path[0], 'user', 'config.json')) as file:
                        settingsdata = json.load(file)
                    
                    self.vars.tickrate.set(settingsdata['network']['default tickrate'])
                    self.vars.port.set(settingsdata['network']['default port'])
                
                @classmethod
                def on_close(self):
                    self.frame.pack_forget()
                
                @classmethod
                def populate_server_list(self):
                    with open(os.path.join(sys.path[0], 'user', 'config.json')) as file:
                        settingsdata = json.load(file)
                    self.serverlist_list.delete(0, tk.END)
                    formatter = '{} ({}:{}){}'
                    for server in settingsdata['network']['servers']:
                        port = server['port']
                        if port == 'normal':
                            port = settingsdata['network']['default port']
                        if server['internal']:
                            additional_text = ' - limited to local network'
                        else:
                            additional_text = ''
                        self.serverlist_list.insert(tk.END, formatter.format(server['name'], server['address'], server['port'], additional_text))
                
                @classmethod
                def return_to_menu(self):
                    self.config['methods'].uiobject.load(self.config['methods'].uiobject.uiobjects.menu)
                
                @classmethod
                def choose_server(self, event = None):
                    curselection = self.serverlist_list.curselection()
                    if not curselection == ():
                        with open(os.path.join(sys.path[0], 'user', 'config.json')) as file:
                            settingsdata = json.load(file)
                        server_target = settingsdata['network']['servers'][curselection[0]]
                        self.config['methods'].uiobject.call_trigger('connect to server', [server_target])
                
                @classmethod
                def add_server(self):
                    with open(os.path.join(sys.path[0], 'user', 'config.json')) as file:
                        settingsdata = json.load(file)
                        
                    sv_dict = {'address': self.vars.address.get(),
                               'internal': not bool(self.addserver_islocal_flipswitch.state),
                               'name': self.vars.name.get(),
                               'port': self.vars.port.get(),
                               'tickrate': self.vars.tickrate.get()}
                    try:
                        sv_dict['port'] = int(sv_dict['port'])
                    except: #is a word (normal), do nothing
                        sv_dict['port'] = 'normal'
                    settingsdata['network']['servers'].append(sv_dict)
                    
                    with open(os.path.join(sys.path[0], 'user', 'config.json'), 'w') as file:
                        json.dump(settingsdata, file, sort_keys=True, indent='\t')
                
                    self.populate_server_list()
                    self.vars.address.set('')
                    self.vars.name.set('')
                    self.vars.tickrate.set(settingsdata['network']['default tickrate'])
                    self.vars.port.set(settingsdata['network']['default port'])
                
                class vars:
                    address = tk.StringVar()
                    port = tk.StringVar()
                    name = tk.StringVar()
                    tickrate = tk.IntVar()
                
                frame = tk.Frame(main.page_frame)
                
                serverlist_frame = tk.Frame(frame)
                serverlist_list = tk.Listbox(serverlist_frame, **self.styling.get(font_size = 'small', object_type = tk.Listbox))
                serverlist_bar = tk.Scrollbar(serverlist_frame, command = serverlist_list.yview)
                serverlist_list.config(yscrollcommand = serverlist_bar.set)
                
                button_connect = tk.Button(frame, text = 'Connect', **self.styling.get(font_size = 'medium', object_type = tk.Button))
                button_back = tk.Button(frame, text = 'Return to menu', **self.styling.get(font_size = 'medium', object_type = tk.Button))
                
                addserver_frame = tk.Frame(frame)
                addserver_choose_button = tk.Button(addserver_frame, text = 'Add server', **self.styling.get(font_size = 'medium', object_type = tk.Button))
                addserver_name_label = tk.Label(addserver_frame, text = 'Name', **self.styling.get(font_size = 'small', object_type = tk.Label))
                addserver_name_entry = tk.Entry(addserver_frame, textvariable = vars.name, **self.styling.get(font_size = 'small', object_type = tk.Entry))
                addserver_address_label = tk.Label(addserver_frame, text = 'Address', **self.styling.get(font_size = 'small', object_type = tk.Label))
                addserver_address_entry = tk.Entry(addserver_frame, textvariable = vars.address, **self.styling.get(font_size = 'small', object_type = tk.Entry))
                addserver_port_label = tk.Label(addserver_frame, text = 'Port', **self.styling.get(font_size = 'small', object_type = tk.Label))
                addserver_port_spinbox = tk.Spinbox(addserver_frame, textvariable = vars.port, from_ = 1024, to = 65535, **self.styling.get(font_size = 'small', object_type = tk.Spinbox))
                addserver_tickrate_label = tk.Label(addserver_frame, text = 'Tickrate', **self.styling.get(font_size = 'small', object_type = tk.Label))
                addserver_tickrate_spinbox = tk.Spinbox(addserver_frame, textvariable = vars.tickrate, from_ = 1, to = 1024, **self.styling.get(font_size = 'small', object_type = tk.Spinbox))
                addserver_islocal_flipswitch = TkFlipSwitch(addserver_frame, options = [{'text': 'Local machine (host server)', 'command': print},
                                                                                        {'text': 'Open to LAN', 'command': print}], **self.styling.get(font_size = 'small', object_type = tk.Button))
                
                serverlist_bar.pack(side = tk.RIGHT, fill = tk.Y)
                serverlist_list.pack(side = tk.LEFT, fill = tk.BOTH, expand = True)
                
                serverlist_frame.grid(row = 0, column = 0, columnspan = 2, sticky = 'NESW')
                button_back.grid(row = 1, column = 0, sticky = 'NESW')
                button_connect.grid(row = 1, column = 1, sticky = 'NESW')
                addserver_frame.grid(row = 2, column = 0, columnspan = 2, sticky = 'NESW')
                
                addserver_name_label.grid(row = 0, column = 0, sticky = 'NESW')
                addserver_name_entry.grid(row = 0, column = 1, sticky = 'NESW')
                addserver_address_label.grid(row = 1, column = 0, sticky = 'NESW')
                addserver_address_entry.grid(row = 1, column = 1, sticky = 'NESW')
                addserver_port_label.grid(row = 2, column = 0, sticky = 'NESW')
                addserver_port_spinbox.grid(row = 2, column = 1, sticky = 'NESW')
                addserver_tickrate_label.grid(row = 3, column = 0, sticky = 'NESW')
                addserver_tickrate_spinbox.grid(row = 3, column = 1, sticky = 'NESW')
                addserver_islocal_flipswitch.grid(row = 4, column = 0, columnspan = 2, sticky = 'NESW')
                addserver_choose_button.grid(row = 0, column = 2, rowspan = 4, sticky = 'NESW')
                
                self.styling.set_weight(frame, 2, 4)
                frame.rowconfigure(1, weight = 0)
                frame.rowconfigure(2, weight = 0)
                frame.rowconfigure(3, weight = 0)
                
                self.styling.set_weight(addserver_frame, 3, 4)
                
            class game:
                config = {'name': 'Game'}
                
                @classmethod
                def on_load(self):
                    self.frame.pack(fill = tk.BOTH, expand = True)
                    self.config['methods'].uiobject.call_trigger('create game object', [self.canvas])
                    
                    #set keybinds for returning to the menu
                    with open(os.path.join(sys.path[0], 'user', 'keybinds.json'), 'r') as file:
                        keybinds_data = json.load(file)
                    if type(keybinds_data['window']['return to menu']) == str:
                        keybinds_data['window']['return to menu'] = [keybinds_data['window']['return to menu']]
                    for key in keybinds_data['window']['return to menu']:
                        self.canvas.bind('<{}>'.format(key), self.return_to_menu)
                
                @classmethod
                def on_close(self):
                    self.frame.pack_forget()
                    self.config['methods'].uiobject.call_trigger('close game')
                    self.config['methods'].uiobject.call_trigger('close server', [])
                
                @classmethod
                def return_to_menu(self, event = None):
                    self.config['methods'].uiobject.load(self.config['methods'].uiobject.uiobjects.menu)
                
                frame = tk.Frame(main.page_frame)
                
                canvas = tk.Canvas(frame, width = 800, height = 600, bg = 'purple', **self.styling.get(font_size = 'medium', object_type = tk.Canvas))
                
                canvas.grid(row = 0, column = 0)
                
                self.styling.set_weight(frame, 1, 1)
                frame.rowconfigure(1, weight = 0)
            
            class editor_choose_file:
                config = {'name': 'Editor'}
                
                @classmethod
                def on_load(self):
                    for name in os.listdir(os.path.join(sys.path[0], 'server', 'maps')):
                        if (not name.startswith('_')) and os.path.isdir(os.path.join(sys.path[0], 'server', 'maps', name)):
                            self.listbox_box.insert(tk.END, name)
                    
                    self.button_choose.config(command = self.open_map)
                    self.button_go_back.config(command = self.return_to_menu)
                    self.button_new.config(command = self.create_new_map)
                    
                    self.listbox_box.bind('<Return>', self.open_map)
                    
                    self.frame.pack(fill = tk.BOTH, expand = True)
                
                @classmethod
                def on_close(self):
                    self.listbox_box.delete(0, tk.END)
                    self.frame.pack_forget()
                
                @classmethod
                def open_map(self, event = None):
                    index = self.listbox_box.curselection()
                    if type(index[0]) == int: #if there is a selection
                        map_name = self.listbox_box.get(index[0])
                        self.config['methods'].uiobject.call_trigger('edit map', [map_name])
                
                @classmethod
                def return_to_menu(self):
                    self.config['methods'].uiobject.load(self.config['methods'].uiobject.uiobjects.menu)
                
                @classmethod
                def create_new_map(self):
                    if self.entry_mapname.get() == '':
                        messagebox.showerror('Error while creating new map', 'You must enter a map name')
                    elif os.path.isdir(os.path.join(sys.path[0], 'server', 'maps', self.entry_mapname.get())):
                        messagebox.showerror('Error while creating new map', 'The map name "{}" is already in use'.format(self.entry_mapname.get()))
                    else:
                        try:
                            shutil.copytree('_template', self.entry_mapname.get())
                        except:
                            messagebox.showerror('Unidentified error', 'Unidentified error while creating map with name "{}"\n\nRemember! It must be a valid directory name'.format(self.entry_mapname.get()))
                
                frame = tk.Frame(main.page_frame)
                
                listbox_frame = tk.Frame(frame)
                listbox_box = tk.Listbox(listbox_frame, **self.styling.get(font_size = 'small', object_type = tk.Listbox))
                listbox_bar = tk.Scrollbar(listbox_frame, command = listbox_box.yview)
                listbox_box.config(yscrollcommand = listbox_bar.set)
                
                listbox_bar.pack(side = tk.RIGHT, fill = tk.Y)
                listbox_box.pack(side = tk.LEFT, fill = tk.BOTH, expand = True)
                
                entry_mapname = tk.Entry(frame, **self.styling.get(font_size = 'medium', object_type = tk.Entry))
                button_new = tk.Button(frame, text = 'Create new map', **self.styling.get(font_size = 'medium', object_type = tk.Button))
                button_choose = tk.Button(frame, text = 'Open map', **self.styling.get(font_size = 'medium', object_type = tk.Button))
                button_go_back = tk.Button(frame, text = 'Return to menu', **self.styling.get(font_size = 'medium', object_type = tk.Button))
                
                listbox_frame.grid(row = 0, column = 0, columnspan = 4, sticky = 'NESW')
                
                entry_mapname.grid(row = 1, column = 0, sticky = 'NESW')
                button_new.grid(row = 1, column = 1, sticky = 'NESW')
                button_choose.grid(row = 1, column = 2, sticky = 'NESW')
                button_go_back.grid(row = 1, column = 3, sticky = 'NESW')
                
                self.styling.set_weight(frame, 4, 2)
                frame.rowconfigure(1, weight = 0)
            
            class editor:
                config = {'name': 'Editor'}
                
                @classmethod
                def on_load(self):
                    self.frame.pack(fill = tk.BOTH, expand = True)
                    self.config['methods'].uiobject.call_trigger('start editor', [self.frame, self.config['methods']])
                
                @classmethod
                def on_close(self):
                    self.config['methods'].uiobject.call_trigger('close editor', [])
                    self.frame.pack_forget()
                
                frame = tk.Frame(main.page_frame)
            
            class server_settings:
                config = {'name': 'Server settings'}
                
                @classmethod
                def on_load(self):
                    self.button_close.config(command = self.choose_accept)
                    self.button_cancel.config(command = self.choose_cancel)
                    self.button_reset_default.config(command = self.choose_reset_default)
                    
                    self.frame.pack(fill = tk.BOTH, expand = True)
                    
                    self.fetch_settings(os.path.join(sys.path[0], 'server', 'config.json'))
                
                @classmethod
                def on_close(self):
                    self.frame.pack_forget()
                
                @classmethod
                def choose_cancel(self):
                    self.config['methods'].uiobject.load(self.config['methods'].uiobject.uiobjects.menu)
                
                @classmethod
                def choose_accept(self):
                    self.push_settings(os.path.join(sys.path[0], 'server', 'config.json'))
                       
                    self.config['methods'].uiobject.load(self.config['methods'].uiobject.uiobjects.menu)
                
                @classmethod
                def choose_reset_default(self):
                    self.fetch_settings(os.path.join(sys.path[0], 'server', 'default_config.json'))
                
                @classmethod
                def push_settings(self, path):
                    with open(path, 'r') as file:
                        settingsdict = json.load(file)
                    
                    settingsdict['network']['accurate hit detection'] = bool(self.hitbox_precision_flipswitch.state)
                    settingsdict['network']['tickrate'] = int(self.vars.tickrate.get())
                    settingsdict['network']['port'] = int(self.vars.port.get())
                    
                    with open(os.path.join(sys.path[0], 'server', 'config.json'), 'w') as file:
                       json.dump(settingsdict, file, sort_keys=True, indent='\t')
                
                @classmethod
                def fetch_settings(self, path):
                    with open(path, 'r') as file:
                        settingsdict = json.load(file)
                    
                    self.hitbox_precision_flipswitch.on_option_press(settingsdict['network']['accurate hit detection'])
                    self.vars.tickrate.set(settingsdict['network']['tickrate'])
                    self.vars.port.set(settingsdict['network']['port'])
                    
                #variables
                class vars:
                    tickrate = tk.IntVar()
                    port = tk.IntVar()
                self.vars = vars
                
                frame = tk.Frame(main.page_frame)
                
                settings_frame = tk.Frame(frame)
                
                widget_row = 0
                
                #network
                cat_network = tk.Label(settings_frame, text = 'Network', **self.styling.get(font_size = 'medium', object_type = tk.Label))
                hitbox_precision_label = tk.Label(settings_frame, text = 'Hitbox precision', **self.styling.get(font_size = 'medium', object_type = tk.Label))
                hitbox_precision_flipswitch = TkFlipSwitch(settings_frame, options = [{'text': 'Low (stock python)'},
                                                                                      {'text': 'High (requires numpy)'}], **self.styling.get(font_size = 'medium', object_type = tk.Button))
                tickrate_label = tk.Label(settings_frame, text = 'Tickrate', **self.styling.get(font_size = 'medium', object_type = tk.Label))
                tickrate_spinbox = tk.Spinbox(settings_frame, from_ = 1, to = 1024, textvariable = self.vars.tickrate, **self.styling.get(font_size = 'medium', object_type = tk.Spinbox))
                port_label = tk.Label(settings_frame, text = 'Port', **self.styling.get(font_size = 'medium', object_type = tk.Label))
                port_spinbox = tk.Spinbox(settings_frame, from_ = 1024, to = 49151, textvariable = self.vars.port, **self.styling.get(font_size = 'medium', object_type = tk.Spinbox))
                
                cat_network.grid(row = widget_row, column = 0, columnspan = 2, sticky = 'NESW')
                hitbox_precision_label.grid(row = widget_row + 1, column = 0, sticky = 'NESW')
                hitbox_precision_flipswitch.grid(row = widget_row + 1, column = 1, sticky = 'NESW')
                tickrate_label.grid(row = widget_row + 2, column = 0, sticky = 'NESW')
                tickrate_spinbox.grid(row = widget_row + 2, column = 1, sticky = 'NESW')
                port_label.grid(row = widget_row + 3, column = 0, sticky = 'NESW')
                port_spinbox.grid(row = widget_row + 3, column = 1, sticky = 'NESW')
                
                widget_row += 4
                
                #functional buttons
                button_close = tk.Button(frame, text = 'Accept', **self.styling.get(font_size = 'medium', object_type = tk.Button))
                button_cancel = tk.Button(frame, text = 'Cancel', **self.styling.get(font_size = 'medium', object_type = tk.Button))
                button_reset_default = tk.Button(frame, text = 'Reset to default', **self.styling.get(font_size = 'medium', object_type = tk.Button))
                
                settings_frame.grid(row = 0, column = 0, columnspan = 3, sticky = 'NESW')
                button_close.grid(row = 2, column = 0, sticky = 'NESW')
                button_cancel.grid(row = 2, column = 1, sticky = 'NESW')
                button_reset_default.grid(row = 2, column = 2, sticky = 'NESW')
                
                #set weights
                self.styling.set_weight(settings_frame, 2, widget_row, dorows = False)
                frame.columnconfigure(0, weight = 1)
                frame.columnconfigure(1, weight = 1)
                frame.columnconfigure(2, weight = 1)
                frame.rowconfigure(0, weight = 1)
            
            class server_host:
                config = {'name': 'Hosting server'}
                
                @classmethod
                def on_load(self):
                    self.frame.pack(fill = tk.BOTH, expand = True)
                    self.config['methods'].uiobject.call_trigger('host server', [self.console_frame])
                    
                    self.button_exit.config(command = self.choose_exit)
                
                @classmethod
                def on_close(self):
                    self.config['methods'].uiobject.call_trigger('close server', [])
                    self.frame.pack_forget()
                
                @classmethod
                def choose_exit(self):
                    self.config['methods'].uiobject.load(self.config['methods'].uiobject.uiobjects.menu)
                
                frame = tk.Frame(main.page_frame)
                
                console_frame = tk.Frame(frame)
                button_exit = tk.Button(frame, text = 'Exit', **self.styling.get(font_size = 'medium', object_type = tk.Button))
                
                console_frame.grid(column = 0, row = 0, sticky = 'NESW')
                button_exit.grid(column = 0, row = 1, sticky = 'NESW')
                
                self.styling.set_weight(frame, 1, 2, dorows = False)
                frame.rowconfigure(0, weight = 1)
            
            class settings_debug:
                config = {'name': 'Settings - Debug'}
                
                @classmethod
                def on_load(self):
                    self.frame.pack(fill = tk.BOTH, expand = True)
                
                @classmethod
                def on_close(self):
                    self.frame.pack_forget()
                
                frame = tk.Frame(main.page_frame)
                
        uiobjects.main = main
        self.uiobjects = uiobjects
        
        #apply additional setup to pages
        for itemname in dir(self.uiobjects):
            ismagicvariable = itemname.startswith('__') and itemname.endswith('__')
            isspecialcase = itemname in ['main']
            if not (ismagicvariable or isspecialcase):
                item = self.uiobjects.__getattribute__(self.uiobjects, itemname) #get class from name
                if not 'config' in dir(item):
                    item.config = {'name': itemname}
                item.config['methods'] = PageMethods(self, item)
        
        self.ready['tkthread'] = True
        self.root.mainloop()
        
        self.call_trigger('window closed')
    
    def load(self, page, *pageargs, **pagekwargs):
        'Load a page'
        if self.uiobjects.main.current is not None and 'on_close' in dir(self.uiobjects.main.current):
            self.uiobjects.main.current.on_close() #close current page if one exists
        self.uiobjects.main.current = page #set loading page as current page
        if 'on_load' in dir(page):
            page.on_load(*pageargs, **pagekwargs) #run the load function for the page
        page.config['methods'].set_title(page.config["name"]) #set correct window title
    
    def set_title(self, title):
        self.uiobjects.main.title = title
        if self.uiobjects.main.current is None:
            self.uiobjects.root.title(self.uiobjects.main.title)
            
        elif self.uiobjects.main.current.config['methods'].current_title is None:
            self.uiobjects.root.title(self.uiobjects.main.title)
            
        else:
            self.uiobjects.main.current.config['methods'].set_title(self.uiobjects.main.current.config['methods'].current_title)
    
    def set_geometry(self, geometry):
        self.uiobjects.main.geometry = geometry
        self.root.geometry(self.uiobjects.main.geometry)
    
    def set_trigger(self, string, function):
        if string in self.triggers:
            self.triggers[string].append(function)
        else:
            self.triggers[string] = [function]
    
    def clear_triggers(self, string):
        if string in self.triggers:
            self.triggers.pop(string)
    
    def call_trigger(self, string, args = None):
        if string in self.triggers:
            for function in self.triggers[string]:
                if args is None:
                    function()
                else:
                    function(*args)
        else:
            raise ValueError('Trigger "{}" hasn\'t been registered'.format(string))

class PageMethods:
    def __init__(self, uiobject, page):
        self.uiobject = uiobject
        self.page = page
        
        self.current_title = None
    
    def set_title(self, title = None):
        if title is not None:
            self.current_title = title
        self.uiobject.root.title('{} - {}'.format(self.uiobject.uiobjects.main.title, self.current_title))

class TkFlipSwitch:
    def __init__(self, container, **kwargs):
        self.container = container

        self.required_internal_args = ['options']
        self.state = 0
        
        self.filtered_args = {}
        self.internal_args = {}
        for key in kwargs:
            if key in self.required_internal_args:
                self.internal_args[key] = kwargs[key]
            else:
                self.filtered_args[key] = kwargs[key]

        for arg in self.required_internal_args:
            if not arg in self.internal_args:
                raise TypeError('Missing keyword argument "{}"'.format(arg))

        self.frame = tk.Frame(container)
        self.buttons = []
        for option in self.internal_args['options']:
            self.buttons.append(tk.Button(self.frame, text = option['text'], command = functools.partial(self.on_option_press, len(self.buttons)), **self.filtered_args))

        self.on_option_press(self.state, run_binds = False)

        for i in range(len(self.buttons)):
            self.buttons[i].grid(column = i, row = 0, sticky = 'NESW')
            self.frame.columnconfigure(i, weight = 1)
        self.frame.rowconfigure(0, weight = 1)

        self.pack = self.frame.pack
        self.grid = self.frame.grid
        self.destroy = self.frame.destroy
        self.pack_forget = self.frame.pack_forget

    def on_option_press(self, index, run_binds = True):
        for button in self.buttons:
            button.config(state = tk.NORMAL, **self.filtered_args)
        self.buttons[index].config(relief = tk.FLAT, state = tk.DISABLED)
        self.state = index
        
        if run_binds and 'command' in self.internal_args['options'][index] and (not self.internal_args['options'][index]['command'] is None):
            self.internal_args['options'][index]['command']()

class UIObject:
    def __init__(self, frame, ui):
        self.name = ''
        self.internal_name = ''
        self.frame = frame
        self._ui = ui
        
        self._call_trigger = self._ui.call_trigger
        self._styling = self._ui.styling
        self._load_page = self._ui.load
        
        class _elements:
            pass
        self._elements = _elements
        
        class _vars:
            pass
        self._vars = _vars
        
    def on_load(self):
        self.frame.pack(fill = tk.BOTH, expand = True)
        self._on_load()
    
    def on_close(self):
        self._on_close()
        self.frame.pack_forget()
    
    def _on_load(self):
        'Empty method. To be overwritten by the inheriting class'
        pass
    
    def _on_close(self):
        'Empty method. To be overwritten by the inheriting class'
        pass