import tkinter as tk
import threading
import time
import json
import os
import sys
import functools

class UI:
    def __init__(self):
        self.ready = {'tkthread': False}
        self.triggers = {}
        
        threading.Thread(target = self.tkthread).start() #start tkinter window in separate thread
        clearpass = False
        while not clearpass: #wait for all threads to check in before returning
            clearpass = True
            for name in self.ready:
                if not self.ready[name]:
                    clearpass = False
    
    def tkthread(self):
        self.root = tk.Tk() #create tkinter window
        
        class styling: #consistent styling tools
            @classmethod
            def get(self, font_size = 'medium', object_type = tk.Label, relief = 'default'):
                'Get styling for a specific type of widget'
                output = {}
                if object_type == tk.Button:
                    output['overrelief'] = self.reliefs[relief]['overrelief']
                output['relief'] = self.reliefs[relief]['relief']
                if not object_type in [tk.Canvas]:
                    output['font'] = self.fonts[font_size]
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
                
            fonts = {'small': ('', 10),
                     'medium': ('', 15),
                     'large': ('', 25)} #default fonts
            reliefs = {'default': {'relief': tk.FLAT,
                                   'overrelief': tk.GROOVE}} #default reliefs
        self.styling = styling        
        
        class main: #store data to do with ui
            title = ''
            geometry = None
            current = None
            page_frame = tk.Frame(self.root)
            page_frame.pack(fill = tk.BOTH, expand = True)
        
        class uiobjects:
            class menu: #menu ui
                config = {'name': 'Menu'}
                
                @classmethod
                def on_load(self):
                    self.frame.pack(fill = tk.BOTH, expand = True)
                    with open(os.path.join(sys.path[0], 'user', 'config.json'), 'r') as file:
                        settingsdict = json.load(file)
                        
                    pilrender_msg = settingsdict['graphics']['PILrender']
                    if not pilrender_msg:
                        pilrender_msg = 'False (WARNING! - disables sprite rotation)'
                        
                    text_ = 'Name: {}, PIL rendering: {} \nInstall PIL/Pillow through "get_packages.bat"'.format(settingsdict['user']['name'], pilrender_msg)
                    self.label_userdata.config(text = text_)
                
                @classmethod
                def on_close(self):
                    self.frame.pack_forget()
                
                def load_settings(ui_object):
                    ui_object.load(ui_object.uiobjects.settings)
                
                def load_host_server(ui_object):
                    ui_object.load(ui_object.uiobjects.game)
                
                def load_connect_server(ui_object):
                    ui_object.load(ui_object.uiobjects.connect_server)
                
                def load_editor(ui_object):
                    ui_object.load(ui_object.uiobjects.editor_choose_file)
                    
                frame = tk.Frame(main.page_frame)
                label_title = tk.Label(frame, text = 'Hydrophobes', **self.styling.get(font_size = 'large', object_type = tk.Label))
                button_editor = tk.Button(frame, text = 'Map editor', command = functools.partial(load_editor, self), **self.styling.get(font_size = 'medium', object_type = tk.Button))
                button_connect = tk.Button(frame, text = 'Connect to a server', command = functools.partial(load_connect_server, self), **self.styling.get(font_size = 'medium', object_type = tk.Button))
                button_host = tk.Button(frame, text = 'Host a server', command = functools.partial(load_host_server, self), **self.styling.get(font_size = 'medium', object_type = tk.Button))
                button_settings = tk.Button(frame, text = 'Change settings', command = functools.partial(load_settings, self), **self.styling.get(font_size = 'medium', object_type = tk.Button))
                label_userdata = tk.Label(frame, text = 'Loading...', **self.styling.get(font_size = 'small', object_type = tk.Label))
                
                label_title.grid(row = 0, column = 0, sticky = 'NESW')
                button_editor.grid(row = 1, column = 0, sticky = 'NESW')
                button_connect.grid(row = 2, column = 0, sticky = 'NESW')
                button_host.grid(row = 3, column = 0, sticky = 'NESW')
                button_settings.grid(row = 4, column = 0, sticky = 'NESW')
                label_userdata.grid(row = 5, column = 0, sticky = 'NESW')
                self.styling.set_weight(frame, 1, 6)
                
            class settings:
                config = {'name': 'Settings'}
                
                @classmethod
                def on_load(self):
                    self.button_close.config(command = self.choose_accept) #can't use functools with classmethods inside of classes that haven't been created yet
                    self.button_cancel.config(command = self.choose_cancel)
                    
                    self.frame.pack(fill = tk.BOTH, expand = True)
                    
                    with open(os.path.join(sys.path[0], 'user', 'config.json'), 'r') as file:
                        settingsdict = json.load(file)
                    if settingsdict['graphics']['PILrender']:
                        self.pilrender_flipswitch.on_option_press(0, run_binds = False)
                    else:
                        self.pilrender_flipswitch.on_option_press(1, run_binds = False)
                    self.mdlquality_flipswitch.on_option_press(settingsdict['graphics']['stacked model quality'], run_binds = False)
                    self.chatalign_flipswitch.on_option_press(settingsdict['hud']['chat']['position'], run_binds = False)
                    self.chatcol_var.set(settingsdict['hud']['chat']['colour'])
                
                @classmethod
                def on_close(self):
                    self.frame.pack_forget()
                
                @classmethod
                def choose_cancel(self):
                    self.config['methods'].uiobject.load(self.config['methods'].uiobject.uiobjects.menu)
                
                @classmethod
                def choose_accept(self):
                    with open(os.path.join(sys.path[0], 'user', 'config.json'), 'r') as file:
                        settingsdict = json.load(file)
                        
                    settingsdict['graphics']['PILrender'] = [True, False][self.pilrender_flipswitch.state]
                    settingsdict['graphics']['stacked model quality'] = self.mdlquality_flipswitch.state
                    settingsdict['hud']['chat']['position'] = self.chatalign_flipswitch.state
                    settingsdict['hud']['chat']['colour'] = self.chatcol_var.get()
                    
                    with open(os.path.join(sys.path[0], 'user', 'config.json'), 'w') as file:
                       json.dump(settingsdict, file, sort_keys=True, indent=4)
                       
                    self.config['methods'].uiobject.load(self.config['methods'].uiobject.uiobjects.menu)
                
                frame = tk.Frame(main.page_frame)
                
                '''username_label
                username_entry'''
                cat_graphics_label = tk.Label(frame, text = 'Graphics', **self.styling.get(font_size = 'medium', object_type = tk.Label))
                pilrender_label = tk.Label(frame, text = 'PIL rendering', **self.styling.get(font_size = 'medium', object_type = tk.Label))
                pilrender_flipswitch = TkFlipSwitch(frame, options = [{'text': 'On', 'command': print},
                                                                      {'text': 'Off', 'command': print}], **self.styling.get(font_size = 'medium', object_type = tk.Button))
                mdlquality_label = tk.Label(frame, text = 'Model quality', **self.styling.get(font_size = 'medium', object_type = tk.Label))
                mdlquality_flipswitch = TkFlipSwitch(frame, options = [{'text': 'Low', 'command': print},
                                                                       {'text': 'Medium', 'command': print},
                                                                       {'text': 'High', 'command': print},
                                                                       {'text': 'Full', 'command': print}], **self.styling.get(font_size = 'medium', object_type = tk.Button))
                
                cat_hud_label = tk.Label(frame, text = 'HUD', **self.styling.get(font_size = 'medium', object_type = tk.Label))
                chatalign_label = tk.Label(frame, text = 'Chat alignment', **self.styling.get(font_size = 'medium', object_type = tk.Label))
                chatalign_flipswitch = TkFlipSwitch(frame, options = [{'text': 'Top left', 'command': print},
                                                                                              {'text': 'Top right', 'command': print},
                                                                                              {'text': 'Bottom left', 'command': print},
                                                                                              {'text': 'Bottom right', 'command': print}], **self.styling.get(font_size = 'medium', object_type = tk.Button))
                chatcol_label = tk.Label(frame, text = 'Chat colour', **self.styling.get(font_size = 'medium', object_type = tk.Label))
                chatcol_var = tk.StringVar()
                chatcol_entry = tk.Entry(frame, textvariable = chatcol_var, **self.styling.get(font_size = 'medium', object_type = tk.Entry))
                
                button_close = tk.Button(frame, text = 'Accept', **self.styling.get(font_size = 'medium', object_type = tk.Button))
                button_cancel = tk.Button(frame, text = 'Cancel', **self.styling.get(font_size = 'medium', object_type = tk.Button))
                
                cat_graphics_label.grid(row = 0, column = 0, columnspan = 2, sticky = 'NESW')
                pilrender_label.grid(row = 1, column = 0, sticky = 'NESW')
                pilrender_flipswitch.grid(row = 1, column = 1, sticky = 'NESW')
                mdlquality_label.grid(row = 2, column = 0, sticky = 'NESW')
                mdlquality_flipswitch.grid(row = 2, column = 1, sticky = 'NESW')
                
                cat_hud_label.grid(row = 3, column = 0, columnspan = 2, sticky = 'NESW')
                chatalign_label.grid(row = 4, column = 0, sticky = 'NESW')
                chatalign_flipswitch.grid(row = 4, column = 1, sticky = 'NESW')
                chatcol_label.grid(row = 5, column = 0, sticky = 'NESW')
                chatcol_entry.grid(row = 5, column = 1, sticky = 'NESW')
                
                button_close.grid(row = 6, column = 0, sticky = 'NESW')
                button_cancel.grid(row = 6, column = 1, sticky = 'NESW')
                
                self.styling.set_weight(frame, 2, 6, dorows = False)
            
            class connect_server:
                config = {'name': 'Connect'}
                
                @classmethod
                def on_load(self):
                    self.frame.pack(fill = tk.BOTH, expand = True)
                    self.populate_server_list()
                    
                    self.serverlist_list.bind('<Return>', self.choose_server)
                    
                    self.button_back.config(command = self.return_to_menu)
                    self.button_connect.config(command = self.choose_server)
                
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
                
                frame = tk.Frame(main.page_frame)
                
                serverlist_frame = tk.Frame(frame)
                serverlist_list = tk.Listbox(serverlist_frame, **self.styling.get(font_size = 'small', object_type = tk.Listbox))
                serverlist_bar = tk.Scrollbar(serverlist_frame, command = serverlist_list.yview)
                serverlist_list.config(yscrollcommand = serverlist_bar.set)
                
                button_connect = tk.Button(frame, text = 'Connect', **self.styling.get(font_size = 'medium', object_type = tk.Button))
                button_back = tk.Button(frame, text = 'Return to menu', **self.styling.get(font_size = 'medium', object_type = tk.Button))
                
                serverlist_bar.pack(side = tk.RIGHT, fill = tk.Y)
                serverlist_list.pack(side = tk.LEFT, fill = tk.BOTH, expand = True)
                
                serverlist_frame.grid(row = 0, column = 0, columnspan = 2, sticky = 'NESW')
                button_back.grid(row = 1, column = 0, sticky = 'NESW')
                button_connect.grid(row = 1, column = 1, sticky = 'NESW')
                
                self.styling.set_weight(frame, 2, 2)
                frame.rowconfigure(1, weight = 0)
                
            class game:
                config = {'name': 'Game'}
                
                @classmethod
                def on_load(self):
                    self.frame.pack(fill = tk.BOTH, expand = True)
                    self.config['methods'].uiobject.call_trigger('create game object', [self.canvas])
                    self.button_exit.config(command = self.return_to_menu)
                
                @classmethod
                def on_close(self):
                    self.frame.pack_forget()
                    self.config['methods'].uiobject.call_trigger('close game')
                
                @classmethod
                def return_to_menu(self):
                    self.config['methods'].uiobject.load(self.config['methods'].uiobject.uiobjects.menu)
                
                frame = tk.Frame(main.page_frame)
                
                canvas = tk.Canvas(frame, **self.styling.get(font_size = 'medium', object_type = tk.Canvas))
                button_exit = tk.Button(frame, text = 'Exit', **self.styling.get(font_size = 'medium', object_type = tk.Button))
                
                canvas.grid(row = 0, column = 0, sticky = 'NESW')
                button_exit.grid(row = 1, column = 0, sticky = 'NESW')
                
                self.styling.set_weight(frame, 1, 2)
                frame.rowconfigure(1, weight = 0)
            
            class editor_choose_file:
                config = {'name': 'Editor'}
                
                @classmethod
                def on_load(self):
                    for name in os.listdir(os.path.join(sys.path[0], 'server', 'maps')):
                        self.listbox_box.insert(tk.END, name)
                    
                    self.button_choose.config(command = self.open_map)
                    self.button_go_back.config(command = self.return_to_menu)
                    
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
        if (not self.uiobjects.main.current == None) and 'on_close' in dir(self.uiobjects.main.current):
            self.uiobjects.main.current.on_close() #close current page if one exists
        self.uiobjects.main.current = page #set loading page as current page
        if 'on_load' in dir(page):
            page.on_load(*pageargs, **pagekwargs) #run the load function for the page
        page.config['methods'].set_title(page.config["name"]) #set correct window title
    
    def set_title(self, title):
        self.uiobjects.main.title = title
        if self.uiobjects.main.current == None:
            self.uiobjects.root.title(self.uiobjects.main.title)
        elif self.uiobjects.main.current.config['methods'].current_title == None:
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
                if args == None:
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
        if not title == None:
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
        
        if run_binds:
            self.internal_args['options'][index]['command']()