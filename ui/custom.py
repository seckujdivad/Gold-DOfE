from tkinter import messagebox
import tkinter as tk
import multiprocessing as mp
import os
import sys
import math
import threading
import json
import time

import modules.colops
import modules.editor
import modules.bettercanvas
import modules.toolhelp

class EditorLayout(modules.editor.EditorSnapin):
    """
    Edit the basic layout of the map
    """
    
    name = 'Layout'
    
    def __init__(self, frame, editorobj, tabobj):
        super().__init__(frame, editorobj, tabobj)
        
        self.ui_styling = self.editorobj.uiobjs.ui_styling
        
        self.tabobj.set_title('opening...')
        
        self.screen_data = []
        self.selection = None
        self.all_scripts = []
        self._follow_pointer = False
        
        self.canvas = tk.Canvas(self.frame, **self.ui_styling.get(font_size = 'medium', object_type = tk.Canvas))
        
        #frame containing the bottom row of UI objects
        self.frame_info = tk.Frame(self.frame)
        
        #label showing the position of the mouse
        self.label_mousecoords = tk.Label(self.frame_info, text = 'Mouse - X: 0000 Y: 0000\nPress F1 for help', **self.ui_styling.get(font_size = 'small', object_type = tk.Label))
        
        #add object coordinate setting UI
        self.polyvar_x = tk.StringVar()
        self.polyvar_y = tk.StringVar()
        
        self.label_polyx = tk.Label(self.frame_info, text = 'X:', **self.ui_styling.get(font_size = 'small', object_type = tk.Label))
        self.label_polyy = tk.Label(self.frame_info, text = 'Y:', **self.ui_styling.get(font_size = 'small', object_type = tk.Label))
        
        self.spinbox_polyx = tk.Spinbox(self.frame_info, textvariable = self.polyvar_x, from_ = -10000, to = 10000, command = self.push_coordinates, **self.ui_styling.get(font_size = 'small', object_type = tk.Spinbox))
        self.spinbox_polyy = tk.Spinbox(self.frame_info, textvariable = self.polyvar_y, from_ = -10000, to = 10000, command = self.push_coordinates, **self.ui_styling.get(font_size = 'small', object_type = tk.Spinbox))
        
        self.push_coordinates()
        
        #some more buttons
        self.button_add = tk.Button(self.frame_info, text = 'Add/Modify', command = self.open_object_selection, **self.ui_styling.get(font_size = 'small', object_type = tk.Button))
        self.button_remove = tk.Button(self.frame_info, text = 'Remove', command = self.remove_object, **self.ui_styling.get(font_size = 'small', object_type = tk.Button))
        self.button_save = tk.Button(self.frame_info, text = 'Save', command = self.save, **self.ui_styling.get(font_size = 'small', object_type = tk.Button))
        self.button_refresh = tk.Button(self.frame_info, text = 'Reload', command = self.reload, **self.ui_styling.get(font_size = 'small', object_type = tk.Button))
        
        #right side frame
        self.frame_rightside = tk.Frame(self.frame)
        
        #list of materials to set which one is used for the selected geometry
        self.polylist_frame = tk.Frame(self.frame_rightside)
        self.polylist_list = tk.Listbox(self.polylist_frame, **self.ui_styling.get(font_size = 'small', object_type = tk.Listbox))
        self.polylist_bar = tk.Scrollbar(self.polylist_frame, command = self.polylist_list.yview)
        self.polylist_list.config(yscrollcommand = self.polylist_bar.set)
        
        self.script_frame = tk.Frame(self.frame_rightside)
        self.script_list = tk.Listbox(self.script_frame, selectmode = tk.MULTIPLE, **self.ui_styling.get(font_size = 'small', object_type = tk.Listbox))
        self.script_bar = tk.Scrollbar(self.script_frame, command = self.script_list.yview)
        self.script_list.config(yscrollcommand = self.script_bar.set)
        self.script_button = tk.Button(self.script_frame, text = 'Assign script to selection', **self.ui_styling.get(font_size = 'small', object_type = tk.Button))
        
        #specify layout
        self.polylist_bar.pack(side = tk.RIGHT, fill = tk.Y)
        self.polylist_list.pack(side = tk.LEFT, fill = tk.BOTH, expand = True)
        
        self.script_button.pack(side = tk.BOTTOM, fill = tk.X)
        self.script_bar.pack(side = tk.RIGHT, fill = tk.Y)
        self.script_list.pack(side = tk.LEFT, fill = tk.BOTH, expand = True)
        
        self.polylist_frame.grid(row = 0, column = 0, sticky = 'NESW')
        self.script_frame.grid(row = 1, column = 0, sticky = 'NESW')
        
        self.canvas.grid(column = 0, row = 0, sticky = 'NESW')
        self.frame_info.grid(column = 0, row = 1, sticky = 'NESW')
        self.frame_rightside.grid(column = 1, row = 0, rowspan = 2, sticky = 'NESW')
        self.frame.rowconfigure(0, weight = 2)
        self.frame.columnconfigure(0, weight = 2)
        
        self.label_mousecoords.grid(column = 0, row = 0, rowspan = 2, sticky = 'NESW')
        self.label_polyx.grid(column = 1, row = 0, sticky = 'NESW')
        self.spinbox_polyx.grid(column = 2, row = 0, sticky = 'NESW')
        self.label_polyy.grid(column = 1, row = 1, sticky = 'NESW')
        self.spinbox_polyy.grid(column = 2, row = 1, sticky = 'NESW')
        self.button_add.grid(column = 3, row = 0, sticky = 'NESW')
        self.button_remove.grid(column = 3, row = 1, sticky = 'NESW')
        self.button_save.grid(column = 4, row = 0, sticky = 'NESW')
        self.button_refresh.grid(column = 4, row = 1, sticky = 'NESW')
        self.ui_styling.set_weight(self.frame_info, 5, 2)
        self.ui_styling.set_weight(self.frame_rightside, 1, 2)
        self.frame_info.columnconfigure(1, weight = 0)
        
        self.load_map_data()
        
        #set the canvas to get focus when moused over and lose it when the mouse pointer goes away
        #this means that it will receive key inputs (like ctrl+s) when the mouse is over it
        self.canvas.bind('<Enter>', lambda event: self.canvas.focus_set())
        self.canvas.bind('<Leave>', lambda event: self.canvas.nametowidget('.').focus_set())
        
        #set up keybinds
        self.canvas.bind('<Motion>', self.mouse_coordinates)
        self.canvas.bind('<Button>', self.select_item)
        self.spinbox_polyx.bind('<Return>', self.push_coordinates)
        self.spinbox_polyy.bind('<Return>', self.push_coordinates)
        self.polylist_list.bind('<Button>', self.on_material_select)
        self.polylist_list.bind('<Up>', self.on_material_select)
        self.polylist_list.bind('<Down>', self.on_material_select)
        self.canvas.bind('<Control-s>', self.save)
        self.canvas.bind('<Control-r>', self.reload)
        self.canvas.bind('<Delete>', self.remove_object)
        self.polylist_list.bind('<Delete>', self.remove_object)
        self.canvas.bind('<BackSpace>', self.remove_object)
        self.polylist_list.bind('<BackSpace>', self.remove_object)
        self.script_list.bind('<Button>', self.set_scripts)
        self.script_list.bind('<space>', self.set_scripts)
        self.canvas.bind('<m>', self._toggle_follow_pointer)
        self.canvas.bind('<F1>', self.help_window)
        
        self.tabobj.set_title('editing...')
    
    def load_map_data(self):
        #open map data file
        self.map_data = self.editorobj.map.get_json('layout.json')
        
        #send map geometry to screen
        self.clear_screen()
        for item in self.map_data['geometry']:
            item = item.copy()
            self.add_object(item)
            
        self.repopulate_poly_list()
        self.repopulate_script_list()
    
    def clear_screen(self):
        for item in self.screen_data:
            self.canvas.delete(item['canvobj'])
        self.screen_data = []
    
    def unpack_coordinates(self, coordinates, modifier):
        output = []
        for x, y in coordinates:
            output.append(x + modifier[0])
            output.append(y + modifier[1])
        return output
    
    def mouse_coordinates(self, event):
        x = '{:>4}'.format(event.x)
        y = '{:>4}'.format(event.y)
        self.label_mousecoords.config(text = 'Mouse - X: {} Y: {}\nPress F1 for help'.format(x.replace(' ', '0'), y.replace(' ', '0')))

        if self._follow_pointer:
            if self.selection == None:
                self._follow_pointer = False
            
            else:
                self.polyvar_x.set(event.x)
                self.polyvar_y.set(event.y)

                self.push_coordinates()
    
    def select_item(self, event):
        canvobj = self.canvas.find_closest(event.x, event.y)
        if not canvobj == ():
            if canvobj[0] in self.canvas.find_overlapping(event.x, event.y, event.x, event.y):
                canvobj = canvobj[0]
                
                item = None
                #find the canvas object in screen_data
                for scan_item in self.screen_data:
                    if scan_item['canvobj'] == canvobj:
                        item = scan_item
                
                if item is not None:
                    self.select_index(self.screen_data.index(item))
                
    def select_index(self, index):
        item = self.screen_data[index]
        
        #remove formatting from previous selection (if there was one)
        if self.selection is not None:
            current = self.screen_data[self.selection]
            self.canvas.itemconfigure(current['canvobj'], fill = current['material data']['editor colour'], outline = current['material data']['editor colour'])
        
        #apply formatting to current selection
        self.canvas.itemconfigure(item['canvobj'], fill = modules.colops.increase(item['material data']['editor colour'], [20, 20, 20]), outline = '#000000')
        
        #update the index of the current selection to match the object selected
        self.selection = index
        
        #select the correct item in the polygon list
        self.polylist_list.selection_clear(0, tk.END)
        self.polylist_list.selection_set(self.selection)
        
        #change the coordinate text
        self.update_polycoord_display(*item['coordinates'])
        
        #highlight the scripts that the panel has in the script pane
        self.highlight_scripts()
     
    def update_polycoord_display(self, x, y):
        self.polyvar_x.set(x)
        self.polyvar_y.set(y)
    
    def push_coordinates(self, event = None):
        if self.selection == None:
            self.update_polycoord_display('----', '----')
        else:
            item = self.screen_data[self.selection]
            item['coordinates'] = [int(self.polyvar_x.get()), int(self.polyvar_y.get())]
            self.canvas.coords(item['canvobj'], *self.unpack_coordinates(item['material data']['hitbox'], item['coordinates']))
            
            self.polylist_list.delete(self.selection)
            self.polylist_list.insert(self.selection, '{} at {}, {}'.format(item['material data']['display name'], item['coordinates'][0], item['coordinates'][1]))
            
    def on_material_select(self, event = None):
        threading.Thread(target = self._on_material_select).start() #start in a separate thread
    
    def _on_material_select(self):
        '''
        This function must be called in a separate thread because it is bound to click. This means that the selection in the listbox hasn't yet been updated. So that it uses the correct selection (instead of the old one), this function is called in a separate thread. This allows the tk mainloop thread to continue and update the selection ready for this thread
        '''
        time.sleep(0.05)
        selection = self.polylist_list.curselection()
        if not selection == ():
            self.select_index(selection[0])
    
    def open_object_selection(self):
        'Open the object selection window to add a new object to the screen'
        AddObject(self)
    
    def add_object(self, dict, layer = 'highest'):
        'Add an object to the screen using a dictionary containing the coordinates and the material path'
        if not layer in ['highest', 'lowest']:
            raise ValueError('"layer" must be either "highest" or "lowest", not "{}"'.format(layer))
        dict['material data'] = self.editorobj.map.get_json(os.path.join('materials', dict['material']))
        dict['canvobj'] = self.canvas.create_polygon(*self.unpack_coordinates(dict['material data']['hitbox'], dict['coordinates']), fill = dict['material data']['editor colour'], outline = dict['material data']['editor colour'])
        if layer == 'highest':
            self.screen_data.append(dict)
            self.polylist_list.insert(tk.END, '{} at {}, {}'.format(dict['material data']['display name'], dict['coordinates'][0], dict['coordinates'][1]))
        else:
            self.screen_data.insert(0, dict)
            self.polylist_list.insert(0, '{} at {}, {}'.format(dict['material data']['display name'], dict['coordinates'][0], dict['coordinates'][1]))
    
    def remove_object(self, event = None):
        if self.selection is not None:
            item = self.screen_data[self.selection]
            
            index = self.selection
            self.select_none()
            
            self.canvas.delete(item['canvobj'])
            self.screen_data.pop(index)
            
            self.repopulate_poly_list()
    
    def select_none(self):
        if self.selection is not None:
            item = self.screen_data[self.selection]
            self.canvas.itemconfigure(item['canvobj'], fill = item['material data']['editor colour'], outline = item['material data']['editor colour'])
            self.update_polycoord_display('----', '----')
            self.selection = None
            self.repopulate_poly_list()
    
    def repopulate_poly_list(self):
        self.polylist_list.delete(0, tk.END)
        
        for item in self.screen_data:
            self.polylist_list.insert(tk.END, '{} at {}, {}'.format(item['material data']['display name'], item['coordinates'][0], item['coordinates'][1]))
    
    def save(self, event = None):
        self.tabobj.set_title('saving...')

        messagebox.showinfo('Reminder', 'When you save changes to the layout, the light maps aren\'t automatically remade.\nIf you have made changes to the lighting, remake the lightmaps in the lightmap generator\nHit OK to continue saving')

        data = self.editorobj.map.get_json('layout.json')
        
        geomdata = []
        for item in self.screen_data:
            item_geometry_data = {'coordinates': item['coordinates'],
                                  'material': item['material']}
            if 'scripts' in item:
                item_geometry_data['scripts'] = item['scripts']
            geomdata.append(item_geometry_data)
        data['geometry'] = geomdata
        
        self.editorobj.map.write_json('layout.json', data)
        
        self.tabobj.set_title('editing...')
    
    def reload(self, event = None):
        self.tabobj.set_title('reloading...')
        
        self.clear_screen()
        self.load_map_data()
        
        self.tabobj.set_title('editing...')
    
    def set_selection_material(self, material_path):
        if not self.selection == None:
            self.screen_data[self.selection]['material'] = material_path
            self.screen_data[self.selection]['material data'] = self.editorobj.map.get_json(os.path.join('materials', self.screen_data[self.selection]['material']))
            
            self.select_index(self.selection)
    
    def repopulate_script_list(self):
        self.script_list.delete(0, tk.END)
        self.all_scripts = []
        
        for item in os.listdir(os.path.join(self.editorobj.map.path, 'scripts')):
            if not (item.startswith('.') or item.startswith('_')):
                self.all_scripts.append(item)
        for item in self.all_scripts:
            self.script_list.insert(tk.END, item)
    
    def highlight_scripts(self):
        layout_obj = self.screen_data[self.selection]
        self.script_list.selection_clear(0, tk.END)
        if 'scripts' in layout_obj:
            for script in layout_obj['scripts']:
                try:
                    self.script_list.selection_set(self.all_scripts.index(script))
                except ValueError:
                    pass
    
    def set_scripts(self, event = None): #set the script in another thread so that the selection can update
        if self.selection is not None:
            threading.Thread(target = self._set_scripts).start()
    
    def _set_scripts(self):
        time.sleep(0.05)
        layout_obj = self.screen_data[self.selection]
        
        #remove scripts that are in the pane from save file. scripts that can't be selected are ignored
        for script in self.all_scripts:
            if 'scripts' in layout_obj:
                while script in layout_obj['scripts']:
                    layout_obj['scripts'].remove(script)
        print(self.script_list.curselection())
        for index in self.script_list.curselection():
            if not 'scripts' in layout_obj:
                layout_obj['scripts'] = []
            layout_obj['scripts'].append(self.all_scripts[index])
        
        if layout_obj['scripts'] == []:
            layout_obj.pop('scripts')
        
        self.screen_data[self.selection] = layout_obj
        print(layout_obj)
    
    def _toggle_follow_pointer(self, event):
        if self.selection is None:
            self._follow_pointer = False
        
        else:
            self._follow_pointer = not self._follow_pointer
    
    def help_window(self, event = None):
        modules.toolhelp.Help('editor_layout.json')

class AddObject:
    '''
    A window that allows you to add another material to the layout
    '''
    def __init__(self, parent):
        self.parent = parent
        
        self.ui_styling = self.parent.ui_styling
        self.map = self.parent.editorobj.map
        
        self.paths = []
        
        threading.Thread(target = self.ui, name = 'Add object to editor UI thread').start() #don't hold the main thread
    
    def ui(self):
        self.root = tk.Tk() #make a new window
        self.root.title('Editor - add/modify object')
        
        #header label
        self.label_header = tk.Label(self.root, text = 'Choose a material', **self.ui_styling.get(font_size = 'medium', object_type = tk.Label))
        
        #material list
        self.list_frame = tk.Frame(self.root)
        self.list_list = tk.Listbox(self.list_frame, height = 20, width = 50, **self.ui_styling.get(font_size = 'small', object_type = tk.Listbox))
        self.list_bar = tk.Scrollbar(self.list_frame, command = self.list_list.yview)
        self.list_list.config(yscrollcommand = self.list_bar.set)
        
        self.list_bar.pack(side = tk.RIGHT, fill = tk.Y)
        self.list_list.pack(side = tk.LEFT, fill = tk.BOTH, expand = True)
        
        self.populate_list() #add all materials to the list
        
        #buttons
        self.button_choose = tk.Button(self.root, text = 'Add', command = self.add_selection, **self.ui_styling.get(font_size = 'small', object_type = tk.Button))
        self.button_tile = tk.Button(self.root, text = 'Tile', command = self.tile_background, **self.ui_styling.get(font_size = 'small', object_type = tk.Button))
        self.button_refresh = tk.Button(self.root, text = 'Refresh', command = self.populate_list, **self.ui_styling.get(font_size = 'small', object_type = tk.Button))
        self.button_set = tk.Button(self.root, text = 'Set selection', command = self.set_selection, **self.ui_styling.get(font_size = 'small', object_type = tk.Button))
        
        #format all
        self.label_header.grid(column = 0, row = 0, columnspan = 4, sticky = 'NESW')
        self.list_frame.grid(column = 0, row = 1, columnspan = 4, sticky = 'NESW')
        self.button_choose.grid(column = 0, row = 2, sticky = 'NESW')
        self.button_tile.grid(column = 1, row = 2, sticky = 'NESW')
        self.button_refresh.grid(column = 2, row = 2, sticky = 'NESW')
        self.button_set.grid(column = 3, row = 2, sticky = 'NESW')
        self.ui_styling.set_weight(self.root, 4, 2)
        self.root.rowconfigure(0, weight = 0)
        
        self.parent.canvas.bind('<e>', self.set_selection)
        
        self.root.mainloop() #mainloop for new UI window (so that button presses and keybinds are handled properly
    
    def populate_list(self):
        #clear data (if there is any)
        self.list_list.delete(0, tk.END)
        self.paths = []
        
        #iterate through default material directory
        for material in os.listdir(os.path.join(self.map.path, 'materials')):
            data = self.map.get_json(os.path.join(self.map.path, 'materials', material)) #get the material file
            self.list_list.insert(tk.END, data['display name']) #use the material display name instead of the path in the list
            self.paths.append(material) #add the path to the list of paths so that it can be easily found when chosen
    
    def add_selection(self):
        selection = self.list_list.curselection()
        if not selection == (): #make sure that something has been selected
            self.parent.add_object({"coordinates": [0, 0], "material": self.paths[selection[0]]}) #tell the layout editor to add in the material at 0, 0
    
    def tile_background(self):
        selection = self.list_list.curselection()
        if not selection == (): #make sure that something has been selected
            for x in range(32, 864, 64):
                for y in range(32, 664, 64):
                    self.parent.add_object({"coordinates": [x, y], "material": self.paths[selection[0]]}, layer = 'lowest') #tell the layout editor to add in the material at 0, 0
    
    def set_selection(self, event = None):
        selection = self.list_list.curselection()
        if not selection == (): #make sure that something has been selected
            self.parent.set_selection_material(self.paths[selection[0]])


class EditorMaterials(modules.editor.EditorSnapin):
    """
    Edit materials and their properties
    """
    
    name = 'Materials'
    
    def __init__(self, frame, editorobj, tabobj):
        super().__init__(frame, editorobj, tabobj)
        
        class vars:
            damage = tk.StringVar()
            accel = tk.StringVar()
            decel = tk.StringVar()
            velcap = tk.StringVar()
            new_file_name = tk.StringVar()
            new_display_name = tk.StringVar()
            editor_colour = tk.StringVar()
            new_entity_name = tk.StringVar()
        self.vars = vars
        
        ## make ui elements
        # material chooser
        self.choose_frame = tk.Frame(self.frame)
        self.choose_list = tk.Listbox(self.choose_frame, **self.ui_styling.get(font_size = 'small', object_type = tk.Listbox))
        self.choose_bar = tk.Scrollbar(self.choose_frame, command = self.choose_list.yview)
        self.choose_list.config(yscrollcommand = self.choose_bar.set)
        
        self.choose_bar.pack(side = tk.RIGHT, fill = tk.Y)
        self.choose_list.pack(side = tk.LEFT, fill = tk.BOTH, expand = True)
        
        #input name for new material
        self.frame_nmatname = tk.Frame(self.frame)
        self.entry_nmatname = tk.Entry(self.frame_nmatname, textvariable = self.vars.new_file_name, **self.ui_styling.get(font_size = 'small', object_type = tk.Entry))
        self.entry_nmatdispname = tk.Entry(self.frame_nmatname, textvariable = self.vars.new_display_name, **self.ui_styling.get(font_size = 'small', object_type = tk.Entry))
        
        self.entry_nmatdispname.pack(side = tk.BOTTOM, fill = tk.BOTH, expand = True)
        self.entry_nmatname.pack(side = tk.BOTTOM, fill = tk.BOTH, expand = True)
        
        self.button_nmatname = tk.Button(self.frame, text = 'Create', command = self.create_new_material, **self.ui_styling.get(font_size = 'small', object_type = tk.Button))
        
        #refresh material list
        self.button_nmatrefresh = tk.Button(self.frame, text = 'Refresh', command = self.refresh, **self.ui_styling.get(font_size = 'small', object_type = tk.Button))
        
        #choose an entity to set damage for
        self.ent_frame = tk.Frame(self.frame)
        self.ent_list = tk.Listbox(self.ent_frame, **self.ui_styling.get(font_size = 'small', object_type = tk.Listbox))
        self.ent_bar = tk.Scrollbar(self.ent_frame, command = self.ent_list.yview)
        self.ent_list.config(yscrollcommand = self.ent_bar.set)
        
        self.ent_bar.pack(side = tk.RIGHT, fill = tk.Y)
        self.ent_list.pack(side = tk.LEFT, fill = tk.BOTH, expand = True)
        
        #add a new entity name to the list
        self.entry_nentname = tk.Entry(self.frame, textvariable = self.vars.new_entity_name, **self.ui_styling.get(font_size = 'small', object_type = tk.Entry))
        self.button_nentname = tk.Button(self.frame, text = 'Create', command = self.create_new_entity, **self.ui_styling.get(font_size = 'small', object_type = tk.Button))
        
        #specify the effect that the material has on entities on it
        self.frame_entprops = tk.Frame(self.frame)
        
        self.label_dmg = tk.Label(self.frame_entprops, text = 'Damage/s', **self.ui_styling.get(font_size = 'small', object_type = tk.Label))
        self.spinbox_dmg = tk.Spinbox(self.frame_entprops, textvariable = self.vars.damage, from_ = -10000, to = 10000, **self.ui_styling.get(font_size = 'small', object_type = tk.Spinbox))
        self.label_accel = tk.Label(self.frame_entprops, text = 'Acceleration', **self.ui_styling.get(font_size = 'small', object_type = tk.Label))
        self.spinbox_accel = tk.Spinbox(self.frame_entprops, textvariable = self.vars.accel, from_ = -10000, to = 10000, **self.ui_styling.get(font_size = 'small', object_type = tk.Spinbox))
        self.label_decel = tk.Label(self.frame_entprops, text = 'Deceleration', **self.ui_styling.get(font_size = 'small', object_type = tk.Label))
        self.spinbox_decel = tk.Spinbox(self.frame_entprops, textvariable = self.vars.decel, from_ = -10000, to = 10000, **self.ui_styling.get(font_size = 'small', object_type = tk.Spinbox))
        self.label_cap = tk.Label(self.frame_entprops, text = 'Max speed', **self.ui_styling.get(font_size = 'small', object_type = tk.Label))
        self.spinbox_cap = tk.Spinbox(self.frame_entprops, textvariable = self.vars.velcap, from_ = 0, to = 10000, **self.ui_styling.get(font_size = 'small', object_type = tk.Spinbox))
        
        self.label_dmg.grid(column = 0, row = 0, sticky = 'NSW')
        self.spinbox_dmg.grid(column = 1, row = 0, sticky = 'NESW')
        self.label_accel.grid(column = 0, row = 1, sticky = 'NSW')
        self.spinbox_accel.grid(column = 1, row = 1, sticky = 'NESW')
        self.label_decel.grid(column = 0, row = 2, sticky = 'NSW')
        self.spinbox_decel.grid(column = 1, row = 2, sticky = 'NESW')
        self.label_cap.grid(column = 0, row = 3, sticky = 'NSW')
        self.spinbox_cap.grid(column = 1, row = 3, sticky = 'NESW')
        self.frame_entprops.columnconfigure(0, weight = 1)
        self.frame_entprops.columnconfigure(1, weight = 1)
        
        #choose a texture from the library
        self.tex_frame = tk.Frame(self.frame)
        self.tex_list = tk.Listbox(self.tex_frame, **self.ui_styling.get(font_size = 'small', object_type = tk.Listbox))
        self.tex_bar = tk.Scrollbar(self.tex_frame, command = self.tex_list.yview)
        self.tex_list.config(yscrollcommand = self.tex_bar.set)
        
        self.tex_bar.pack(side = tk.RIGHT, fill = tk.Y)
        self.tex_list.pack(side = tk.LEFT, fill = tk.BOTH, expand = True)
        
        #show the user the texture that they have selected
        self.label_tex = tk.Label(self.frame, text = 'Model: ----', **self.ui_styling.get(font_size = 'small', object_type = tk.Label))
        self.base_canvas_tex = tk.Canvas(self.frame, width = 128, height = 64)
        self.canvas_tex = modules.bettercanvas.CanvasController(self.base_canvas_tex, get_pil = True)
        
        #choose a colour for the editor
        self.label_colour = tk.Label(self.frame, text = 'Editor colour', **self.ui_styling.get(font_size = 'small', object_type = tk.Label))
        self.entry_colour = tk.Entry(self.frame, textvariable = self.vars.editor_colour, **self.ui_styling.get(font_size = 'small', object_type = tk.Entry))
        
        #save the material
        self.button_save = tk.Button(self.frame, text = 'Save all changes', command = self.save_all, **self.ui_styling.get(font_size = 'small', object_type = tk.Button))
        
        ## pack ui elements
        #first column
        self.choose_frame.grid(column = 0, row = 0, columnspan = 2, rowspan = 2, sticky = 'NESW')
        self.frame_nmatname.grid(column = 0, row = 2, columnspan = 2, sticky = 'NESW')
        self.button_nmatname.grid(column = 0, row = 3, columnspan = 2, sticky = 'NESW')
        self.button_nmatrefresh.grid(column = 0, row = 4, columnspan = 2, sticky = 'NESW')
        
        #second column
        self.ent_frame.grid(column = 2, row = 0, rowspan = 5, sticky = 'NESW')
        
        #third column
        self.frame_entprops.grid(column = 3, row = 0, columnspan = 2, rowspan = 4, sticky = 'NESW')
        self.entry_nentname.grid(column = 3, row = 4, sticky = 'NESW')
        self.button_nentname.grid(column = 4, row = 4, sticky = 'NESW')
        
        #fourth column
        self.tex_frame.grid(column = 5, row = 0, columnspan = 2, rowspan = 2, sticky = 'NESW')
        self.base_canvas_tex.grid(column = 5, row = 2, columnspan = 2, sticky = 'NESW')
        self.label_tex.grid(column = 5, row = 3, columnspan = 2, sticky = 'NSW')
        self.label_colour.grid(column = 5, row = 4, sticky = 'NESW')
        self.entry_colour.grid(column = 6, row = 4, sticky = 'NESW')
        
        #bottom row
        self.button_save.grid(column = 0, columnspan = 7, row = 5, sticky = 'NESW')
        
        for i in range(8):
            self.frame.columnconfigure(i, weight = 1)
        self.frame.rowconfigure(0, weight = 1)
        
        self.choose_list.bind('<Button>', self.choose_material)
        self.ent_list.bind('<Button>', self.choose_entity)
        self.tex_list.bind('<Button>', self.choose_texture)
        self.entry_colour.bind('<Return>', self.choose_colour)
        self.entry_nmatname.bind('<Return>', self.create_new_material)
        self.entry_nmatdispname.bind('<Return>', self.create_new_material)
        self.entry_nentname.bind('<Return>', self.create_new_entity)
        
        self.refresh()
    
    def refresh(self):
        class lists:
            materials = []
            textures = []
            entities = []
        self.lists = lists
    
        self.choose_list.delete(0, tk.END)
        for item in os.listdir(os.path.join(self.editorobj.map.path, 'materials')):
            self.choose_list.insert(tk.END, item)
            self.lists.materials.append(item)
            
        self.tex_list.delete(0, tk.END)
        for item in os.listdir(os.path.join(self.editorobj.map.path, 'models', 'materials')):
            self.tex_list.insert(tk.END, item)
            self.lists.textures.append(item)
        
        self.ent_list.delete(0, tk.END)
        
        self.material_selection = None
        self.entity_selection = None
        self.texture_selection = None
        self.texture_object = None
        self.canvtexture_object = None
        self.editorcol_object = None
        self.vars.damage.set('----')
        self.vars.accel.set('0')
        self.vars.decel.set('0')
        self.vars.velcap.set('0')
        self.vars.editor_colour.set('#FFFFFF')
        
        self.material_dicts = {}
    
    def choose_material(self, event = None):
        threading.Thread(target = self._choose_material).start()
    
    def _choose_material(self):
        time.sleep(0.05)
        
        selection = self.choose_list.curselection()
        if not selection == ():
            self.material_selection = selection[0]
            if not self.lists.materials[self.material_selection] in self.material_dicts:
                self.material_dicts[self.lists.materials[self.material_selection]] = self.editorobj.map.get_json(os.path.join('materials', self.lists.materials[self.material_selection]))
            selected_material_data = self.material_dicts[self.lists.materials[self.material_selection]]
            
            self.ent_list.delete(0, tk.END)
            for key in selected_material_data['entities']:
                self.ent_list.insert(tk.END, key)
                self.lists.entities.append(key)
            
            self.update_tex_display(selected_material_data['model'], selected_material_data['editor colour'])
            
            self.vars.damage.set('----')
            self.vars.accel.set('0')
            self.vars.decel.set('0')
            self.vars.velcap.set('0')
            
            self.tabobj.set_title(self.lists.materials[self.material_selection])
    
    def choose_entity(self, event = None):
        threading.Thread(target = self._choose_entity).start()
    
    def _choose_entity(self):
        time.sleep(0.05)
        
        selection = self.ent_list.curselection()
        
        selected_material_data = self.material_dicts[self.lists.materials[self.material_selection]]
            
        if not self.vars.damage.get() == '----':
            entity_name = self.lists.entities[self.entity_selection]
            
            selected_material_data['entities'][entity_name]['damage'] = float(self.vars.damage.get())
            selected_material_data['entities'][entity_name]['accelerate'] = float(self.vars.accel.get())
            selected_material_data['entities'][entity_name]['decelerate'] = float(self.vars.decel.get())
            selected_material_data['entities'][entity_name]['velcap'] = float(self.vars.velcap.get())
        
        if not selection == ():
            self.entity_selection = selection[0]
        
        entity_name = self.lists.entities[self.entity_selection]
        
        selected_material_data = self.material_dicts[self.lists.materials[self.material_selection]]
        
        self.vars.damage.set(str(selected_material_data['entities'][entity_name]['damage']))
        self.vars.accel.set(str(selected_material_data['entities'][entity_name]['accelerate']))
        self.vars.decel.set(str(selected_material_data['entities'][entity_name]['decelerate']))
        self.vars.velcap.set(str(selected_material_data['entities'][entity_name]['velcap']))
    
    def choose_texture(self, event = None):
        threading.Thread(target = self._choose_texture).start()
    
    def _choose_texture(self):
        time.sleep(0.05)
        
        selection = self.tex_list.curselection()
        if not selection == ():
            self.texture_selection = selection[0]
            
            selected_material_data = self.material_dicts[self.lists.materials[self.material_selection]]
            selected_material_data['model'] = 'materials/{}'.format(self.lists.textures[self.texture_selection])
            
            self.update_tex_display(selected_material_data['model'], selected_material_data['editor colour'])
    
    def choose_colour(self, event = None):
        colour = self.vars.editor_colour.get()
        
        selected_material_data = self.material_dicts[self.lists.materials[self.material_selection]]
        selected_material_data['texture']['editor colour'] = colour
        
        self.update_tex_display(selected_material_data['model'], selected_material_data['editor colour'])
    
    def update_tex_display(self, name, colour):
        #delete old objects from the canvas
        if self.editorcol_object is not None:
            self.canvas_tex.delete(self.editorcol_object)
        
        self.editorcol_object = self.canvas_tex.create_rectangle(64, 0, 128, 64, fill = colour, outline = colour)
        
        if name is None:
            self.label_tex.config(text = 'Model: <none>')
        else:
            self.canvtexture_object = modules.bettercanvas.Model(self.canvas_tex, name, self.editorobj.map.path, 0)
            self.canvtexture_object.setpos(32, 32)
            
            self.label_tex.config(text = 'Model: {}'.format(name))
        
        self.vars.editor_colour.set(colour)
    
    def create_new_material(self, event = None):
        mat_name = self.vars.new_file_name.get()
        mat_dispname = self.vars.new_display_name.get()
        
        if mat_name != '' and mat_dispname != '':
            with open(os.path.join(sys.path[0], 'server', 'default_material.json'), 'r') as file:
                data = json.load(file)
            data['display name'] = mat_dispname
            
            self.editorobj.map.write_json(os.path.join('materials', mat_name), data)
            
            self.refresh()
            
            self.vars.new_file_name.set('')
            self.vars.new_display_name.set('')
    
    def create_new_entity(self, event = None):
        entity_name = self.vars.new_entity_name.get()
        
        if entity_name != '' and self.material_selection != None:
            selected_material_data = self.material_dicts[self.lists.materials[self.material_selection]]
            
            with open(os.path.join(sys.path[0], 'server', 'default_movement.json'), 'r') as file:
                data = json.load(file)
            selected_material_data['entities'][entity_name] = data
            
            self.lists.entities.append(entity_name)
            self.ent_list.insert(tk.END, entity_name)
    
    def save_all(self, event = None):
        self._choose_entity()
    
        for name in self.material_dicts:
            self.editorobj.map.write_json(os.path.join('materials', name), self.material_dicts[name])
    
class EditorConfig(modules.editor.EditorSnapin):
    """
    An editor for editing the map config files
    """
    
    name = 'Config'
    
    def __init__(self, frame, editorobj, tabobj):
        super().__init__(frame, editorobj, tabobj)
        
        self.tabobj.set_title('constructing...')
        
        #toolbar options
        self.toolbar_frame = tk.Frame(self.frame)
        self.toolbar_save = tk.Button(self.toolbar_frame, text = 'Save', command = self.save, **self.ui_styling.get(font_size = 'medium', object_type = tk.Button))
        self.toolbar_reload = tk.Button(self.toolbar_frame, text = 'Reload', command = self.reload, **self.ui_styling.get(font_size = 'medium', object_type = tk.Button))
        
        self.toolbar_save.grid(row = 0, column = 0, sticky = 'NESW')
        self.toolbar_reload.grid(row = 0, column = 1, sticky = 'NESW')
        self.ui_styling.set_weight(self.toolbar_frame, 2, 1)
        
        self.options_frame = tk.Frame(self.frame)
        
        #tk vars
        class vars:
            basetex = tk.StringVar()
            overlaytex = tk.StringVar()
            scatternum = tk.StringVar()
        self.vars = vars
        
        #column frames
        self.col0_frame = tk.Frame(self.options_frame)
        self.col1_frame = tk.Frame(self.options_frame)
        self.col2_frame = tk.Frame(self.options_frame)
        self.col3_frame = tk.Frame(self.options_frame)
        
        ## column 0
        #base texture
        self.basetex_label = tk.Label(self.col0_frame, text = 'Base texture', **self.ui_styling.get(font_size = 'small', object_type = tk.Label))
        self.basetex_entry = tk.Entry(self.col0_frame, textvariable = self.vars.basetex, **self.ui_styling.get(font_size = 'small', object_type = tk.Entry))
        
        #overlay texture
        self.overlaytex_label = tk.Label(self.col0_frame, text = 'Overlay texture', **self.ui_styling.get(font_size = 'small', object_type = tk.Label))
        self.overlaytex_entry = tk.Entry(self.col0_frame, textvariable = self.vars.overlaytex, **self.ui_styling.get(font_size = 'small', object_type = tk.Entry))
        
        #scatters chooser
        self.scatter_label = tk.Label(self.col0_frame, text = 'Types of object to be used as scatters', **self.ui_styling.get(font_size = 'small', object_type = tk.Label))
        self.scatter_frame = tk.Frame(self.col0_frame)
        self.scatter_list = tk.Listbox(self.scatter_frame, selectmode = tk.MULTIPLE, **self.ui_styling.get(font_size = 'small', object_type = tk.Listbox))
        self.scatter_scrollbar = tk.Scrollbar(self.scatter_frame, command = self.scatter_list.yview, **self.ui_styling.get(font_size = 'small', object_type = tk.Scrollbar))
        self.scatter_list.config(yscrollcommand = self.scatter_scrollbar.set)
        
        self.scatter_scrollbar.pack(side = tk.RIGHT, fill = tk.Y)
        self.scatter_list.pack(side = tk.LEFT, fill = tk.BOTH, expand = True)
        
        #scatter number
        self.scatternum_label = tk.Label(self.col0_frame, text = 'Number of scatters', **self.ui_styling.get(font_size = 'small', object_type = tk.Label))
        self.scatternum_spinbox = tk.Spinbox(self.col0_frame, from_ = 0, to = 65535, textvariable = self.vars.scatternum, **self.ui_styling.get(font_size = 'small', object_type = tk.Spinbox))
        
        #pack all
        self.basetex_label.grid(row = 0, column = 0, sticky = 'NESW')
        self.basetex_entry.grid(row = 0, column = 1, sticky = 'NESW')
        self.overlaytex_label.grid(row = 1, column = 0, sticky = 'NESW')
        self.overlaytex_entry.grid(row = 1, column = 1, sticky = 'NESW')
        self.scatter_label.grid(row = 2, column = 0, columnspan = 2, sticky = 'NESW')
        self.scatter_frame.grid(row = 3, column = 0, columnspan = 2, sticky = 'NESW')
        self.scatternum_label.grid(row = 4, column = 0, sticky = 'NESW')
        self.scatternum_spinbox.grid(row = 4, column = 1, sticky = 'NESW')
        
        self.ui_styling.set_weight(self.col0_frame, 2, 5, dorows = False)
        
        ## column 1
        #choose starting items for players
        self.startitems_label = tk.Label(self.col1_frame, text = 'Starting items', **self.ui_styling.get(font_size = 'small', object_type = tk.Scrollbar))
        self.startitems_frame = tk.Frame(self.col1_frame)
        self.startitems_list = tk.Listbox(self.startitems_frame, selectmode = tk.MULTIPLE, **self.ui_styling.get(font_size = 'small', object_type = tk.Listbox))
        self.startitems_scrollbar = tk.Scrollbar(self.startitems_frame, command = self.startitems_list.yview, **self.ui_styling.get(font_size = 'small', object_type = tk.Scrollbar))
        self.startitems_list.config(yscrollcommand = self.startitems_scrollbar.set)
        
        self.startitems_scrollbar.pack(side = tk.RIGHT, fill = tk.Y)
        self.startitems_list.pack(side = tk.LEFT, fill = tk.BOTH, expand = True)
        
        #pack all
        self.startitems_label.grid(row = 0, column = 2, columnspan = 2, sticky = 'NESW')
        self.startitems_frame.grid(row = 1, column = 2, columnspan = 2, sticky = 'NESW')
        
        self.ui_styling.set_weight(self.col1_frame, 2, 2, dorows = False)
        
        ## column 2
        ## column 3
        
        self.col0_frame.grid(row = 0, column = 0, sticky = 'NESW')
        self.col1_frame.grid(row = 0, column = 1, sticky = 'NESW')
        self.col2_frame.grid(row = 0, column = 2, sticky = 'NESW')
        self.col3_frame.grid(row = 0, column = 3, sticky = 'NESW')
        
        self.ui_styling.set_weight(self.options_frame, 4, 1, dorows = False)
        
        self.options_frame.grid(row = 0, column = 0, sticky = 'NESW')
        self.toolbar_frame.grid(row = 1, column = 0, sticky = 'NESW')
        self.ui_styling.set_weight(self.frame, 1, 2)
        self.frame.rowconfigure(1, weight = 0)
        
        self.reload()
    
    def reload(self):
        self.tabobj.set_title('populating...')
        
        with open(os.path.join(self.editorobj.map.path, 'list.json'), 'r') as file:
            data = json.load(file)
        
        #populate lists
        self.populate_scatters()
        self.populate_items()
        
        #set vars
        self.vars.basetex.set(data['background']['base'])
        self.vars.overlaytex.set(data['background']['overlay'])
        self.vars.scatternum.set(data['background']['scatternum'])
        
        self.tabobj.set_title('editing...')
    
    def populate_scatters(self):
        self.scatter_list.delete(0, tk.END)
        for file in os.listdir(os.path.join(self.editorobj.map.path, 'models')):
            self.scatter_list.insert(tk.END, file)
    
    def populate_items(self):
        self.startitems_list.delete(0, tk.END)
        for file in os.listdir(os.path.join(self.editorobj.map.path, 'items')):
            self.startitems_list.insert(tk.END, file)
    
    def save(self):
        pass

class EditorLightMap(modules.editor.EditorSnapin):
    """
    Generate a light map for the level
    """
    
    name = 'Lightmaps'
    
    def __init__(self, frame, editorobj, tabobj):
        super().__init__(frame, editorobj, tabobj)
        
        self.lightcalc = None
        
        self.tabobj.set_title('loading...')
        
        with open(os.path.join(sys.path[0], 'user', 'config.json'), 'r') as file:
            self.user_config = json.load(file)
        
        self.label_warning = tk.Label(self.frame, text = 'loading..', **self.ui_styling.get(font_size = 'medium', object_type = tk.Label))
        self.button_generate = tk.Button(self.frame, text = 'Generate', command = self.generate, **self.ui_styling.get(font_size = 'large', object_type = tk.Button))
        
        self.log_frame = tk.Frame(self.frame)
        self.log_list = tk.Listbox(self.log_frame, **self.ui_styling.get(font_size = 'small', object_type = tk.Listbox))
        self.log_scrollbar = tk.Scrollbar(self.log_frame, command = self.log_list.yview, **self.ui_styling.get(font_size = 'small', object_type = tk.Scrollbar))
        self.log_list.config(yscrollcommand = self.log_scrollbar.set)
        
        self.log_scrollbar.pack(side = tk.RIGHT, fill = tk.Y)
        self.log_list.pack(side = tk.LEFT, fill = tk.BOTH, expand = True)
        
        self.label_warning.grid(row = 0, column = 0, sticky = 'NESW')
        self.button_generate.grid(row = 1, column = 0, sticky = 'NESW')
        self.log_frame.grid(row = 2, column = 0, sticky = 'NESW')
        
        self.ui_styling.set_weight(self.frame, 1, 3, dorows = False)
        self.frame.rowconfigure(2, weight = 1)
        
        if self.user_config['graphics']['PILrender']:
            self.label_warning.config(text = 'PIL is enabled\nReady to generate light map')
        else:
            self.label_warning.config(text = 'PIL is not enabled\nInstall it and turn it on in settings')
            self.button_generate.config(state = tk.DISABLED)
            
        self.tabobj.set_title('ready')
    
    def generate(self, event = None):
        threading.Thread(target = self._generate, name = 'Lightmap generator').start()
    
    def _generate(self):
        self.button_generate.config(state = tk.DISABLED)
    
        self.tabobj.set_title('generating...')
        self.log_list.delete(0, tk.END)
        self.log_list.insert(tk.END, 'Initialising...')
        
        if self.user_config['editor']['lightmap']['render shadows']:
            self.log_list.insert(tk.END, 'Shadows are turned ON')
            self.log_list.insert(tk.END, 'This will result in a better image at the cost of a long render time')
        else:
            self.log_list.insert(tk.END, 'Shadows are turned OFF')
            self.log_list.insert(tk.END, 'This will result in a shorter render time at the cost of a lower quality image')
        
        self.tabobj.set_title('Getting lightmap module...')
        import modules.lightcalc #bad practice, but needed for pickling
        self.tabobj.set_title('Done')
        
        self.log_list.insert(tk.END, 'Allocating calculation processes...')
        
        with open(os.path.join(self.editorobj.map.path, 'list.json'), 'r') as file:
            mapcfg = json.load(file)
        
        self.log_list.insert(tk.END, 'Getting PIL Image object...')
        PILImage = __import__('PIL.Image').Image
        self.log_list.insert(tk.END, 'Done')
        
        self.log_list.insert(tk.END, 'Making blank lightmap...')
        image = PILImage.new('RGBA', (mapcfg['geometry'][0], mapcfg['geometry'][1]), 'black')
        pixels = image.load()
        self.log_list.insert(tk.END, 'Done')
        
        self.log_list.insert(tk.END, 'Loading map data...')
        with open(os.path.join(self.editorobj.map.path, 'list.json'), 'r') as file:
            self.map_data = json.load(file)
        self.log_list.insert(tk.END, 'Done')
        
        self.log_list.insert(tk.END, 'Loading layout data...')
        with open(os.path.join(self.editorobj.map.path, self.map_data['layout']), 'r') as file:
            self.layout_data = json.load(file)
        self.log_list.insert(tk.END, 'Done')
        
        self.log_list.insert(tk.END, 'Loading materials...')
        self.materials = {}
        for mat in os.listdir(os.path.join(self.editorobj.map.path, 'materials')):
            with open(os.path.join(self.editorobj.map.path, 'materials', mat), 'r') as file:
                self.materials[mat] = json.load(file)
        self.log_list.insert(tk.END, 'Done')
        
        self.log_list.insert(tk.END, 'Identifying light sources...')
        self.light_sources = []
        for panel in self.layout_data['geometry']:
            if self.materials[panel['material']]['light']['emit'] > 0:
                self.light_sources.append(panel)
        self.log_list.insert(tk.END, 'Done')
        
        self.log_list.insert(tk.END, 'Identifying blocking panels...')
        self.blocking_panels = []
        for panel in self.layout_data['geometry']:
            if self.materials[panel['material']]['light']['block'] > 0:
                self.blocking_panels.append(panel)
        self.log_list.insert(tk.END, 'Done')
        
        self.log_list.insert(tk.END, 'Allocating calculation processes...')
        pipe, process_pipe = mp.Pipe()

        #generate segments
        j = 1
        segments = []
        seg_width = int(mapcfg['geometry'][0] / self.user_config['graphics']['lightcalc threads'])
        for i in range(seg_width, mapcfg['geometry'][0] + seg_width, seg_width):
            segments.append([j, i])
            j = i
        
        #allocate segments to processes
        for x0, x1 in segments:
            self.log_list.insert(tk.END, 'Allocated segment x = {}-{}'.format(x0, x1))
            mp.Process(target = modules.lightcalc.CalcSegment, args = [x0, x1, mapcfg['geometry'][1], process_pipe, self.map_data, self.materials, self.light_sources, self.blocking_panels, self.user_config['editor']['lightmap']['render shadows']]).start()
        
        self.log_list.insert(tk.END, 'Done')
        
        self.log_list.insert(tk.END, 'Generating lightmap...')
        command = None
        checked_in = 0
        while not command == 'exit':
            command = pipe.recv()
            
            if command == 'done':
                checked_in += 1
                self.log_list.insert(tk.END, 'Segments complete: {}'.format(checked_in))
                if checked_in >= 8:
                    command = 'exit'
            elif command[0] == 'message':
                self.log_list.insert(tk.END, command[1])
                self._see_bottom()
            else:
                to_write = (0, 0, 0, 255 - command[1])
                if self.map_data['grid']['apply to lightmap']:
                    for x in range(command[0][0], command[0][0] + self.map_data['grid']['mult']['x'], 1):
                        for y in range(command[0][1], command[0][1] + self.map_data['grid']['mult']['y'], 1):
                            try:
                                pixels[x, y] = to_write
                            except IndexError:
                                pass
                else:
                    pixels[command[0][0], command[0][1]] = to_write
        self.log_list.insert(tk.END, 'Done')
        
        self.map_data['lighting']['map'] = os.path.join('models', 'system', 'lightmap', 'lightmap.png')
        
        self.log_list.insert(tk.END, 'Saving lightmap...')
        image.save(os.path.join(self.editorobj.map.path, self.map_data['lighting']['map']))
        self.log_list.insert(tk.END, 'Done')
        
        self.log_list.insert(tk.END, 'Saving config...')
        with open(os.path.join(self.editorobj.map.path, 'list.json'), 'w') as file:
            json.dump(self.map_data, file, sort_keys = True, indent = '\t')
        self.log_list.insert(tk.END, 'Done')
        
        self.log_list.insert(tk.END, 'Lightmap is complete')
        
        self.tabobj.set_title('ready')
        
        self.button_generate.config(state = tk.ACTIVE)
        
        self._see_bottom()
    
    
    def _see_bottom(self, event = None):
        self.log_list.see(tk.END)
        
class EditorPanelHitbox(modules.editor.EditorSnapin):
    """
    Edit the hitboxes for the panels in the level
    """
    
    name = 'Panel hitboxes'
    
    def __init__(self, frame, editorobj, tabobj):
        super().__init__(frame, editorobj, tabobj)
        
        class editor:
            current_model = None
            current_points = []
            selected_point = None
            current_material = None
            hitbox_poly = []
            
            selection_x = tk.StringVar()
            selection_y = tk.StringVar()
            
            class centre:
                x = None
                y = None
            self.centre = centre
        self.editor = editor
        
        with open(os.path.join(sys.path[0], 'user', 'config.json'), 'r') as file:
            self.user_config = json.load(file)
        
        #create elements
        self.mat_frame = tk.Frame(self.frame)
        self.mat_list = tk.Listbox(self.mat_frame, **self.ui_styling.get(font_size = 'small', object_type = tk.Listbox))
        self.mat_scrollbar = tk.Scrollbar(self.mat_frame, command = self.mat_list.yview, **self.ui_styling.get(font_size = 'small', object_type = tk.Scrollbar))
        self.mat_list.config(yscrollcommand = self.mat_scrollbar.set)
        
        self.mat_scrollbar.pack(side = tk.RIGHT, fill = tk.Y)
        self.mat_list.pack(side = tk.LEFT, fill = tk.BOTH, expand = True)
        
        self.canvas = tk.Canvas(self.frame, bg = 'white', **self.ui_styling.get(font_size = 'small', object_type = tk.Canvas))
        self.canvcont = modules.bettercanvas.CanvasController(self.canvas, layers = ['user', 'hitboxedit_layers.json'], get_pil = True)
        
        self.coordx_label = tk.Label(self.frame, text = 'X:', **self.ui_styling.get(font_size = 'small', object_type = tk.Label))
        self.coordx_spinbox = tk.Spinbox(self.frame, textvariable = self.editor.selection_x, from_ = -999, to = 999, command = self.spinbox_updated, **self.ui_styling.get(font_size = 'small', object_type = tk.Spinbox))
        self.coordy_label = tk.Label(self.frame, text = 'Y:', **self.ui_styling.get(font_size = 'small', object_type = tk.Label))
        self.coordy_spinbox = tk.Spinbox(self.frame, textvariable = self.editor.selection_y, from_ = -999, to = 999, command = self.spinbox_updated, **self.ui_styling.get(font_size = 'small', object_type = tk.Spinbox))
        
        self.editor.selection_x.set('----')
        self.editor.selection_y.set('----')
        
        self.help_label = tk.Label(self.frame, text = 'For help, press F1', **self.ui_styling.get(font_size = 'small', object_type = tk.Label))
        self.save_button = tk.Button(self.frame, text = 'Save', command = self.save, **self.ui_styling.get(font_size = 'small', object_type = tk.Label))
        
        #display elements
        self.mat_frame.grid(row = 0, column = 0, rowspan = 3, sticky = 'NESW')
        self.canvas.grid(row = 0, column = 1, columnspan = 4, sticky = 'NESW')
        self.coordx_label.grid(row = 1, column = 1, sticky = 'NESW')
        self.coordx_spinbox.grid(row = 1, column = 2, sticky = 'NESW')
        self.coordy_label.grid(row = 1, column = 3, sticky = 'NESW')
        self.coordy_spinbox.grid(row = 1, column = 4, sticky = 'NESW')
        self.help_label.grid(row = 2, column = 2, sticky = 'NESW')
        self.save_button.grid(row = 2, column = 4, sticky = 'NESW')
        
        #set weighting
        self.ui_styling.set_weight(self.frame, 5, 3)
        self.frame.columnconfigure(0, weight = 0)
        self.frame.rowconfigure(1, weight = 0)
        self.frame.rowconfigure(2, weight = 0)
        
        #populate materials list
        self.materials = {}
        for name in os.listdir(os.path.join(self.editorobj.map.path, 'materials')):
            self.materials[name] = self.editorobj.map.get_json(os.path.join('materials', name))
            self.mat_list.insert(tk.END, name)
        
        #make keybinds
        self.mat_list.bind('<Button-1>', self.mat_selected)
        self.canvcont.bind('<Button-1>', self.canvas_clicked)
        
        self.canvcont.bind('<Up>', self.move_up)
        self.canvcont.bind('<Down>', self.move_down)
        self.canvcont.bind('<Left>', self.move_left)
        self.canvcont.bind('<Right>', self.move_right)
        self.canvcont.bind('<Tab>', self.select_next)
        self.canvcont.bind('<Shift-Tab>', self.select_prev)
        self.canvcont.bind('<m>', self.remove_selected)
        self.canvcont.bind('<s>', self.subdivide_selected)
        
        self.canvcont.bind('<F1>', self.show_help)
        
        self.coordx_spinbox.bind('<Return>', self.spinbox_updated)
        self.coordy_spinbox.bind('<Return>', self.spinbox_updated)
        
        #make canvas take focus when the mouse enters, and lose it when it leaves
        self.canvas.bind('<Enter>', lambda event: self.canvas.focus_set())
        self.canvas.bind('<Leave>', lambda event: self.canvas.nametowidget('.').focus_set())
    
    def mat_selected(self, event = None):
        threading.Thread(target = self._mat_selected, args = [event]).start()
    
    def _mat_selected(self, event):
        time.sleep(0.05)
        
        curselection = self.mat_list.curselection()
        if not curselection == ():
            material = self.mat_list.get(curselection[0])
            self.tabobj.set_title(material)
            
            material_data = self.materials[material]

            if self.editor.current_model is not None:
                self.editor.current_model.destroy()
            self.editor.current_model = modules.bettercanvas.Model(self.canvcont, material_data['model'], self.editorobj.map.path, layer = 'texture')
            
            for obj, x, y in self.editor.current_points:
                self.canvcont.delete(obj)
                
            self.editor.centre.x = int(self.canvcont.winfo_width() / 2)
            self.editor.centre.y = int(self.canvcont.winfo_height() / 2)
            
            self.editor.current_model.set(x = self.editor.centre.x, y = self.editor.centre.y)
            
            self.editor.current_material = material
            
            self.editor.current_points = []
            last_x = None
            last_y = None
            for x, y in material_data['hitbox']:
                self.editor.current_points.append([self.make_handle(x, y), x, y])
                
                if last_x is not None:
                    self.editor.hitbox_poly.append(self.make_hitbox_line(last_x, last_y, x, y))
                
                last_x = x
                last_y = y
            
            self.editor.hitbox_poly.append(self.make_hitbox_line(last_x, last_y, material_data['hitbox'][0][0], material_data['hitbox'][0][1]))
    
    def make_hitbox_line(self, x0, y0, x1, y1):
        return self.canvcont.create_line(self.editor.centre.x + x0, self.editor.centre.y + y0, self.editor.centre.x + x1, self.editor.centre.y + y1, fill = '#000000', layer = 'edges')
    
    def make_handle(self, x, y):
        return self.canvcont.create_rectangle(self.editor.centre.x + x + int(self.user_config['editor']['hitbox']['grab handles']['size'] / 2), self.editor.centre.y + y + int(self.user_config['editor']['hitbox']['grab handles']['size'] / 2), self.editor.centre.x + x - int(self.user_config['editor']['hitbox']['grab handles']['size'] / 2), self.editor.centre.y + y - int(self.user_config['editor']['hitbox']['grab handles']['size'] / 2), fill = self.user_config['editor']['hitbox']['grab handles']['normal'], outline = self.user_config['editor']['hitbox']['grab handles']['outline'], layer = 'handles')
    
    def canvas_clicked(self, event):
        overlapping = self.canvcont.find_overlapping(event.x - 1, event.y - 1, event.x + 1, event.y + 1)
        if not len(overlapping) == 0:
            item_overlapping = None
            for item in overlapping:
                if item_overlapping is None:
                    for item_b in self.editor.current_points:
                        if item == item_b[0]:
                            item_overlapping = item
            
            if item_overlapping is not None:
                overlapping = item_overlapping
                is_current_point = False
                i = 0
                index = None
                for obj, x, y in self.editor.current_points:
                    if obj == overlapping:
                        is_current_point = True
                        index = i
                    i += 1
                
                if is_current_point and index is not None:
                    self.choose_handle(index)
    
    def choose_handle(self, index):
        if self.editor.selected_point is not None:
            self.canvcont.itemconfigure(self.editor.current_points[self.editor.selected_point][0], fill = self.user_config['editor']['hitbox']['grab handles']['normal'])
            
        if index is None:
            self.editor.selection_x.set('----')
            self.editor.selection_y.set('----')
        else:
            self.canvcont.itemconfigure(self.editor.current_points[index][0], fill = self.user_config['editor']['hitbox']['grab handles']['grabbed'])
        
            if not self.editor.selection_x.get() == '----':
                self.editor.current_points[self.editor.selected_point][1] = int(self.editor.selection_x.get())
                self.editor.current_points[self.editor.selected_point][2] = int(self.editor.selection_y.get())
            
            self.editor.selection_x.set(self.editor.current_points[index][1])
            self.editor.selection_y.set(self.editor.current_points[index][2])
            
        self.editor.selected_point = index
        
    def spinbox_updated(self, event = None, use_values = True):
        if use_values:
            self.editor.current_points[self.editor.selected_point][1] = int(self.editor.selection_x.get())
            self.editor.current_points[self.editor.selected_point][2] = int(self.editor.selection_y.get())
        else:
            self.editor.selection_x.set(self.editor.current_points[self.editor.selected_point][1])
            self.editor.selection_y.set(self.editor.current_points[self.editor.selected_point][2])
        
        obj, x1, y1 = self.editor.current_points[len(self.editor.current_points) - 1]
        x1 = int(x1)
        y1 = int(y1)
        
        for i in range(len(self.editor.hitbox_poly)):
            x0, y0 = x1, y1
            obj, x1, y1 = self.editor.current_points[i]
            
            x1 = int(x1)
            y1 = int(y1)
            
            self.canvcont.coords(self.editor.hitbox_poly[i], self.editor.centre.x + x0, self.editor.centre.y + y0, self.editor.centre.x + x1, self.editor.centre.y + y1)
        
        topx = int(self.editor.selection_x.get()) + self.editor.centre.x + int(self.user_config['editor']['hitbox']['grab handles']['size'] / 2)
        bottomx = int(self.editor.selection_x.get()) + self.editor.centre.x - int(self.user_config['editor']['hitbox']['grab handles']['size'] / 2)
        topy = int(self.editor.selection_y.get()) + self.editor.centre.y + int(self.user_config['editor']['hitbox']['grab handles']['size'] / 2)
        bottomy = int(self.editor.selection_y.get()) + self.editor.centre.y - int(self.user_config['editor']['hitbox']['grab handles']['size'] / 2)
        
        self.canvcont.coords(self.editor.current_points[self.editor.selected_point][0], topx, topy, bottomx, bottomy)
    
    def move_up(self, event = None):
        if not self.editor.selection_y.get() == '----':
            self.editor.selection_y.set(int(self.editor.selection_y.get()) - 1)
            self.spinbox_updated()
    
    def move_down(self, event = None):
        if not self.editor.selection_y.get() == '----':
            self.editor.selection_y.set(int(self.editor.selection_y.get()) + 1)
            self.spinbox_updated()
    
    def move_left(self, event = None):
        if not self.editor.selection_x.get() == '----':
            self.editor.selection_x.set(int(self.editor.selection_x.get()) - 1)
            self.spinbox_updated()
    
    def move_right(self, event = None):
        if not self.editor.selection_x.get() == '----':
            self.editor.selection_x.set(int(self.editor.selection_x.get()) + 1)
            self.spinbox_updated()
    
    def select_next(self, event = None):
        if self.editor.selected_point is None:
            self.choose_handle(0)
        else:
            self.choose_handle((self.editor.selected_point + 1) % len(self.editor.current_points))
        self.canvas.focus_set()
    
    def select_prev(self, event = None):
        if self.editor.selected_point is None:
            self.choose_handle(0)
        else:
            self.choose_handle((self.editor.selected_point - 1) % len(self.editor.current_points))
        self.canvas.focus_set()
    
    def show_help(self, event = None):
        threading.Thread(target = self._show_help).start()
    
    def _show_help(self):
        root = tk.Tk()
        
        text = tk.Text(root, height = 10, width = 50, **self.ui_styling.get(font_size = 'small', object_type = tk.Text))
        
        text.insert(tk.END, """How to use:
Click on a grab handle to select it, then use the arrow keys or the spinboxes to move the vertices of the hitbox around.

M: Remove selected vertex and merge adjacent
S: Subdivide between selected and next vertex

Remember, clicking on a new hitbox to edit without saving will reset your changes""")

        text.config(state = tk.DISABLED)
        text.pack(fill = tk.BOTH, expand = True)
        
        root.title('Help')
        
        root.mainloop()
    
    def remove_selected(self, event = None):
        if self.editor.selected_point is not None:
            self.remove(self.editor.selected_point)
   
    def remove(self, index):
        if len(self.editor.current_points) > 3:
            del_point = index
            
            self.choose_handle((index - 1) % (len(self.editor.current_points) - 1))
            
            self.canvcont.delete(self.editor.current_points[del_point][0])
            self.canvcont.delete(self.editor.hitbox_poly[del_point])
            self.editor.current_points.pop(del_point)
            self.editor.hitbox_poly.pop(del_point)
            
            self.spinbox_updated(use_values = False)
    
    def subdivide_selected(self, event = None):
        if self.editor.selected_point is not None:
            self.subdivide(self.editor.selected_point, (self.editor.selected_point + 1) % len(self.editor.current_points))
    
    def subdivide(self, index0, index1):
        cpoints = self.editor.current_points
        
        x = int(cpoints[index0][1] + ((cpoints[index1][1] - cpoints[index0][1]) / 2))
        y = int(cpoints[index0][2] + ((cpoints[index1][2] - cpoints[index0][2]) / 2))
        
        self.choose_handle(None)
        
        self.editor.current_points.insert((index0 + 1) % len(self.editor.current_points), [self.make_handle(x, y), x, y])
        self.editor.hitbox_poly.append(self.make_hitbox_line(0, 0, 1, 1))
        
        self.choose_handle((index0 + 1) % len(self.editor.current_points))
        
        self.spinbox_updated(use_values = True)
    
    def save(self, event = None):
        if self.editor.current_material is not None:
            data = self.materials[self.editor.current_material]
            
            data['hitbox'] = []
            for obj, x, y in self.editor.current_points:
                data['hitbox'].append([x, y])
            
            dist = 0
            for x, y in data['hitbox']:
                dist = max(abs(math.hypot(x, y)), dist)
            
            data['hitbox maxdist'] = math.ceil(dist)
            
            self.editorobj.map.write_json(os.path.join('materials', self.editor.current_material), data)