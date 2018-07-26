import tkinter as tk
import os
import sys
import functools
import json
import time
import threading

import modules.engine

class Map:
    def __init__(self, name):
        self.name = name
        
        self.path = os.path.join(sys.path[0], 'server', 'maps', self.name)
        
    def get_text(self, path):
        'Gets text from a file in the map folder'
        with open(os.path.join(self.path, path), 'r') as file:
            text = file.read()
        return text
    
    def write_text(self, path, text):
        'Writes text to a file in the map folder'
        with open(os.path.join(self.path, path), 'w') as file:
            file.write(text)
    
    def get_json(self, path):
        'Gets data from a json file in the map folder and reads it'
        with open(os.path.join(self.path, path), 'r') as file:
            data = json.load(file)
        return data
    
    def write_json(self, path, data):
        'Writes data to a json file in the map folder'
        with open(os.path.join(self.path, path), 'w') as file:
            json.dump(data, file, sort_keys=True, indent='\t')

class Editor:
    def __init__(self, frame, pagemethods):
        self.frame = frame
        self.pagemethods = pagemethods
        
        self.ui_styling = self.pagemethods.uiobject.styling
        
        class editors:
            class _Template:
                """
                A template for making editors
                """
                def __init__(self, frame, editorobj, tabobj):
                    self.frame = frame
                    self.editorobj = editorobj
                    self.tabobj = tabobj
                    
                    self.ui_styling = self.editorobj.uiobjs.ui_styling
                    
            class Text:
                '''
                Edit a text file in the map directory
                '''
                def __init__(self, frame, editorobj, tabobj):
                    self.frame = frame
                    self.editorobj = editorobj
                    self.tabobj = tabobj
                    
                    self.ui_styling = self.editorobj.uiobjs.ui_styling
                    
                    self.toprow = tk.Frame(self.frame)
                    self.path = tk.Entry(self.toprow, **self.ui_styling.get(font_size = 'small', object_type = tk.Entry))
                    self.save = tk.Button(self.toprow, text = 'Save', command = self.save_text, **self.ui_styling.get(font_size = 'small', object_type = tk.Button))
                    self.reload = tk.Button(self.toprow, text = 'Reload', command = self.reload_text, **self.ui_styling.get(font_size = 'small', object_type = tk.Button))
                    
                    self.path.pack(side = tk.LEFT, fill = tk.BOTH, expand = True)
                    self.save.pack(side = tk.RIGHT, fill = tk.Y)
                    self.reload.pack(side = tk.RIGHT, fill = tk.Y)
                    
                    self.textentry = tk.Text(self.frame, **self.ui_styling.get(font_size = 'small', object_type = tk.Text))
                    
                    self.toprow.grid(row = 0, column = 0, sticky = 'NESW')
                    self.textentry.grid(row = 1, column = 0, sticky = 'NESW')
                    
                    self.frame.rowconfigure(1, weight = 1)
                    self.frame.columnconfigure(0, weight = 1)
                
                def reload_text(self):
                    path = self.path.get()
                    self.textentry.delete(0.0, tk.END)
                    self.textentry.insert(tk.END, self.editorobj.map.get_text(self.path.get()))
                    
                    self.tabobj.set_title(path)
                
                def save_text(self):
                    try:
                        text = self.textentry.get(0.0, tk.END)
                    except tk.TclError:
                        text = ''
                    path = self.path.get()
                    self.editorobj.map.write_text(path, text)
                    self.tabobj.set_title(path)
            
            class Tree:
                '''
                View the entire map directory, copy file paths
                '''
                def __init__(self, frame, editorobj, tabobj):
                    self.frame = frame
                    self.editorobj = editorobj
                    self.tabobj = tabobj
                    
                    self.ui_styling = self.editorobj.uiobjs.ui_styling
                    
                    self.all_paths = []
                    
                    self.list_frame = tk.Frame(self.frame)
                    self.list_list = tk.Listbox(self.list_frame, font = ('Courier New', 9))
                    self.list_bar = tk.Scrollbar(self.list_frame, command = self.list_list.yview)
                    self.list_list.config(yscrollcommand = self.list_bar.set)
                    
                    self.button_copy = tk.Button(self.frame, text = 'Copy', command = self.copy_selection_to_clipboard, **self.ui_styling.get(font_size = 'medium', object_type = tk.Button))
                    self.button_open = tk.Button(self.frame, text = 'Open with system', command = self.open_selection_with_system, **self.ui_styling.get(font_size = 'medium', object_type = tk.Button))
                    
                    self.list_bar.pack(side = tk.RIGHT, fill = tk.Y)
                    self.list_list.pack(side = tk.LEFT, fill = tk.BOTH, expand = True)
                    
                    self.list_frame.grid(row = 0, column = 0, columnspan = 2, sticky = 'NESW')
                    self.button_copy.grid(row = 1, column = 0, sticky = 'NESW')
                    self.button_open.grid(row = 1, column = 1, sticky = 'NESW')
                    self.ui_styling.set_weight(self.frame, 2, 2)
                    self.frame.rowconfigure(1, weight = 0)
                    
                    self.frame.bind('<Control-C>', self.threaded_copy_selection_to_clipboard) #doesn't work yet; may fix (button is an alright workaround)
                    
                    self.tabobj.set_title(self.editorobj.map.name)
                    
                    self.populate_list()
                    
                def populate_list(self):
                    cfg = self.editorobj.map.get_json('editorcfg.json')
                        
                    all_items, self.all_paths = self.index_dir('', 0, cfg['ignore'])
                    
                    for item in all_items:
                        self.list_list.insert(tk.END, item)
                
                def index_dir(self, path, depth, ignore):
                    map_path = self.editorobj.map.path
                    output = []
                    prefix = '    ' * depth
                    paths = []
                    for item in os.listdir(os.path.join(map_path, path)):
                        if os.path.isdir(os.path.join(map_path, path, item)):
                            paths.append(os.path.join(path, item))
                            output.append('+{}{}'.format(prefix, item))
                            if not os.path.join(path, item) in ignore:
                                noutput, npaths = self.index_dir(os.path.join(path, item), depth + 1, ignore)
                                output += noutput
                                paths += npaths
                        else:
                            paths.append(os.path.join(path, item))
                            if depth == 0:
                                output.append(' {}{}'.format(prefix, item))
                            else:
                                output.append('|{}{}'.format(prefix, item))
                        #paths.append(os.path.join(path, item))
                    return output, paths
                
                def copy_selection_to_clipboard(self, event = None):
                    selection = self.list_list.curselection()
                    if not selection == ():
                        text = self.all_paths[selection[0]]
                        self.set_clipboard(text)
                
                def threaded_copy_selection_to_clipboard(self, event = None):
                    threading.Thread(target = self.copy_selection_to_clipboard, name = 'Threaded copy selection to clipboard').start()
                
                def open_selection_with_system(self, event = None):
                    selection = self.list_list.curselection()
                    if not selection == ():
                        text = self.all_paths[selection[0]]
                        os.system('start "" "{}"'.format(os.path.join(self.editorobj.map.path, text)))
                
                def set_clipboard(self, text):
                    self.editorobj.uiobjs.pagemethods.uiobject.root.clipboard_clear()
                    self.editorobj.uiobjs.pagemethods.uiobject.root.clipboard_append(text)
            
            class Layout:
                """
                Edit the basic layout of the map
                """
                def __init__(self, frame, editorobj, tabobj):
                    self.frame = frame
                    self.editorobj = editorobj
                    self.tabobj = tabobj
                    
                    self.ui_styling = self.editorobj.uiobjs.ui_styling
                    
                    self.tabobj.set_title('opening...')
                    
                    self.screen_data = []
                    self.selection = None
                    
                    self.canvas = tk.Canvas(self.frame, **self.ui_styling.get(font_size = 'medium', object_type = tk.Canvas))
                    
                    #frame containing the bottom row of UI objects
                    self.frame_info = tk.Frame(self.frame)
                    
                    #label showing the position of the mouse
                    self.label_mousecoords = tk.Label(self.frame_info, text = 'Mouse - X: 0000 Y: 0000', **self.ui_styling.get(font_size = 'small', object_type = tk.Label))
                    
                    #add object coordinate setting UI
                    self.polyvar_x = tk.StringVar()
                    self.polyvar_y = tk.StringVar()
                    
                    self.label_polyx = tk.Label(self.frame_info, text = 'X:', **self.ui_styling.get(font_size = 'small', object_type = tk.Label))
                    self.label_polyy = tk.Label(self.frame_info, text = 'Y:', **self.ui_styling.get(font_size = 'small', object_type = tk.Label))
                    
                    self.spinbox_polyx = tk.Spinbox(self.frame_info, textvariable = self.polyvar_x, from_ = -10000, to = 10000, command = self.push_coordinates, **self.ui_styling.get(font_size = 'small', object_type = tk.Spinbox))
                    self.spinbox_polyy = tk.Spinbox(self.frame_info, textvariable = self.polyvar_y, from_ = -10000, to = 10000, command = self.push_coordinates, **self.ui_styling.get(font_size = 'small', object_type = tk.Spinbox))
                    
                    self.push_coordinates()
                    
                    #some more buttons
                    self.button_add = tk.Button(self.frame_info, text = 'Add', command = self.open_object_selection, **self.ui_styling.get(font_size = 'small', object_type = tk.Button))
                    self.button_remove = tk.Button(self.frame_info, text = 'Remove', command = self.remove_object, **self.ui_styling.get(font_size = 'small', object_type = tk.Button))
                    self.button_save = tk.Button(self.frame_info, text = 'Save', command = self.save, **self.ui_styling.get(font_size = 'small', object_type = tk.Button))
                    self.button_refresh = tk.Button(self.frame_info, text = 'Reload', command = self.reload, **self.ui_styling.get(font_size = 'small', object_type = tk.Button))
                    
                    #list of materials to set which one is used for the selected geometry
                    self.polylist_frame = tk.Frame(self.frame)
                    self.polylist_list = tk.Listbox(self.polylist_frame, **self.ui_styling.get(font_size = 'small', object_type = tk.Listbox))
                    self.polylist_bar = tk.Scrollbar(self.polylist_frame, command = self.polylist_list.yview)
                    self.polylist_list.config(yscrollcommand = self.polylist_bar.set)
                    
                    self.polylist_bar.pack(side = tk.RIGHT, fill = tk.Y)
                    self.polylist_list.pack(side = tk.LEFT, fill = tk.BOTH, expand = True)
                    
                    self.canvas.grid(column = 0, row = 0, sticky = 'NESW')
                    self.frame_info.grid(column = 0, row = 1, sticky = 'NESW')
                    self.polylist_frame.grid(column = 1, row = 0, rowspan = 2, sticky = 'NESW')
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
                    self.frame_info.columnconfigure(1, weight = 0)
                    
                    self.load_map_data()
                    
                    self.canvas.bind('<Motion>', self.mouse_coordinates)
                    self.canvas.bind('<Button>', self.select_item)
                    self.spinbox_polyx.bind('<Return>', self.push_coordinates)
                    self.spinbox_polyy.bind('<Return>', self.push_coordinates)
                    self.polylist_list.bind('<Button>', self.on_material_select)
                    self.polylist_list.bind('<Up>', self.on_material_select)
                    self.polylist_list.bind('<Down>', self.on_material_select)
                    self.canvas.bind('<Control-S>', self.save) #doesn't work yet
                    
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
                    self.label_mousecoords.config(text = 'Mouse - X: {} Y: {}'.format(x.replace(' ', '0'), y.replace(' ', '0')))
                
                def select_item(self, event):
                    canvobj = self.canvas.find_closest(event.x, event.y)
                    if not canvobj == ():
                        if canvobj[0] in self.canvas.find_overlapping(event.x, event.y, event.x, event.y):
                            canvobj = canvobj[0]
                            
                            #find the canvas object in screen_data
                            for scan_item in self.screen_data:
                                if scan_item['canvobj'] == canvobj:
                                    item = scan_item
                            
                            self.select_index(self.screen_data.index(item))
                                    
                def select_index(self, index):
                    item = self.screen_data[index]
                    
                    if not self.selection == index: #if the current selection is the same as the one being switched to, don't bother
                        #remove formatting from previous selection (if there was one)
                        if not self.selection == None:
                            current = self.screen_data[self.selection]
                            self.canvas.itemconfigure(current['canvobj'], fill = current['material data']['texture']['editor colour'], outline = current['material data']['texture']['editor colour'])
                        
                        #apply formatting to current selection
                        self.canvas.itemconfigure(item['canvobj'], fill = modules.engine.colour.increase(item['material data']['texture']['editor colour'], [20, 20, 20]), outline = '#000000')
                        
                        #update the index of the current selection to match the object selected
                        self.selection = index
                        
                        #select the correct item in the polygon list
                        self.polylist_list.selection_clear(0, tk.END)
                        self.polylist_list.selection_set(self.selection)
                        
                        #change the coordinate text
                        self.update_polycoord_display(*item['coordinates'])
                 
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
                
                def add_object(self, dict):
                    'Add an object to the screen using a dictionary containing the coordinates and the material path'
                    dict['material data'] = self.editorobj.map.get_json(dict['material'])
                    dict['canvobj'] = self.canvas.create_polygon(*self.unpack_coordinates(dict['material data']['hitbox'], dict['coordinates']), fill = dict['material data']['texture']['editor colour'], outline = dict['material data']['texture']['editor colour'])
                    self.screen_data.append(dict)
                    
                    #add item to object list
                    self.polylist_list.insert(tk.END, '{} at {}, {}'.format(dict['material data']['display name'], dict['coordinates'][0], dict['coordinates'][1]))
                
                def remove_object(self):
                    if not self.selection == None:
                        item = self.screen_data[self.selection]
                        
                        index = self.selection
                        self.select_none()
                        
                        self.canvas.delete(item['canvobj'])
                        self.screen_data.pop(index)
                        
                        self.repopulate_poly_list()
                
                def select_none(self):
                    if not self.selection == None:
                        item = self.screen_data[self.selection]
                        self.canvas.itemconfigure(item['canvobj'], fill = item['material data']['texture']['editor colour'], outline = item['material data']['texture']['editor colour'])
                        self.update_polycoord_display('----', '----')
                        self.selection = None
                        self.repopulate_poly_list()
                
                def repopulate_poly_list(self):
                    self.polylist_list.delete(0, tk.END)
                    
                    for item in self.screen_data:
                        self.polylist_list.insert(tk.END, '{} at {}, {}'.format(item['material data']['display name'], item['coordinates'][0], item['coordinates'][1]))
                
                def save(self):
                    self.tabobj.set_title('saving...')
                    data = self.editorobj.map.get_json('layout.json')
                    
                    geomdata = []
                    for item in self.screen_data:
                        geomdata.append({'coordinates': item['coordinates'],
                                         'material': item['material']})
                    data['geometry'] = geomdata
                    
                    self.editorobj.map.write_json('layout.json', data)
                    
                    self.tabobj.set_title('editing...')
                
                def reload(self):
                    self.tabobj.set_title('reloading...')
                    
                    self.clear_screen()
                    self.load_map_data()
                    
                    self.tabobj.set_title('editing...')
            
            class MaterialEditor:
                """
                Edit materials and their properties
                """
                def __init__(self, frame, editorobj, tabobj):
                    self.frame = frame
                    self.editorobj = editorobj
                    self.tabobj = tabobj
                    
                    self.ui_styling = self.editorobj.uiobjs.ui_styling
                    
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
                    
                    #choose the correct rendering method
                    with open(os.path.join(sys.path[0], 'user', 'config.json')) as file:
                        data = json.load(file)
                    
                    if data['graphics']['PILrender']:
                        self.rendermethod = __import__('PIL.ImageTk').ImageTk.PhotoImage
                    else:
                        self.rendermethod = tk.PhotoImage
                    
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
                    self.button_nentname = tk.Button(self.frame, text = 'Create', **self.ui_styling.get(font_size = 'small', object_type = tk.Button))
                    
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
                    self.label_tex = tk.Label(self.frame, text = 'Texture: ----', **self.ui_styling.get(font_size = 'small', object_type = tk.Label))
                    self.canvas_tex = tk.Canvas(self.frame, width = 128, height = 64)
                    
                    #choose a colour for the editor
                    self.label_colour = tk.Label(self.frame, text = 'Editor colour', **self.ui_styling.get(font_size = 'small', object_type = tk.Label))
                    self.entry_colour = tk.Entry(self.frame, textvariable = self.vars.editor_colour, **self.ui_styling.get(font_size = 'small', object_type = tk.Entry))
                    
                    #save the material
                    self.button_save = tk.Button(self.frame, text = 'Save all changes', **self.ui_styling.get(font_size = 'small', object_type = tk.Button))
                    
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
                    self.canvas_tex.grid(column = 5, row = 2, columnspan = 2, sticky = 'NESW')
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
                    for item in os.listdir(os.path.join(self.editorobj.map.path, 'textures')):
                        if item.endswith('.png'): #only pngs are currently supported
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
                        
                        self.update_tex_display(selected_material_data['texture']['address'], selected_material_data['texture']['editor colour'])
                        
                        self.vars.damage.set('----')
                        self.vars.accel.set('0')
                        self.vars.decel.set('0')
                        self.vars.velcap.set('0')
                
                def choose_entity(self, event = None):
                    threading.Thread(target = self._choose_entity).start()
                
                def _choose_entity(self):
                    time.sleep(0.05)
                    
                    selection = self.ent_list.curselection()
                    if not selection == ():
                        selected_material_data = self.material_dicts[self.lists.materials[self.material_selection]]
                        
                        if not self.vars.damage.get() == '----':
                            entity_name = self.lists.entities[self.entity_selection]
                            
                            selected_material_data['entities'][entity_name]['damage'] = float(self.vars.damage.get())
                            selected_material_data['entities'][entity_name]['accelerate'] = float(self.vars.accel.get())
                            selected_material_data['entities'][entity_name]['decelerate'] = float(self.vars.decel.get())
                            selected_material_data['entities'][entity_name]['velcap'] = float(self.vars.velcap.get())
                        
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
                        selected_material_data['texture']['address'] = self.lists.textures[self.texture_selection]
                        
                        self.update_tex_display(selected_material_data['texture']['address'], selected_material_data['texture']['editor colour'])
                
                def choose_colour(self, event = None):
                    colour = self.vars.editor_colour.get()
                    
                    selected_material_data = self.material_dicts[self.lists.materials[self.material_selection]]
                    selected_material_data['texture']['editor colour'] = colour
                    
                    self.update_tex_display(selected_material_data['texture']['address'], selected_material_data['texture']['editor colour'])
                
                def update_tex_display(self, address, colour):
                    #delete old objects from the canvas
                    if not self.editorcol_object == None:
                        self.canvas_tex.delete(self.editorcol_object)
                    if not self.canvtexture_object == None:
                        self.canvas_tex.delete(self.canvtexture_object)
                    
                    self.editorcol_object = self.canvas_tex.create_rectangle(64, 0, 128, 64, fill = colour, outline = colour)
                    
                    if address == None:
                        self.label_tex.config(text = 'Texture: <none>')
                    else:
                        self.texture_object = self.rendermethod(file = os.path.join(self.editorobj.map.path, 'textures', address))
                        self.canvtexture_object = self.canvas_tex.create_image(32, 32, image = self.texture_object)
                        
                        self.label_tex.config(text = 'Texture: {}'.format(address))
                    
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
                    
            library = {'Text': Text,
                       'Tree': Tree,
                       'Layout': Layout,
                       'Material Editor': MaterialEditor} #all the types of tab
            
            @classmethod
            def create_new(self, name):
                'Make a new pane/tab'
                new_pane = EditorTab(name, self, len(self.uiobjs.tabs))
                new_pane.show()
                self.uiobjs.tabs.append(new_pane)
            
            uiobjs = None
        self.editors = editors
        
        class uiobjs:
            editor_pane_frame = tk.Frame(self.frame)
            editor_panes = []
            for name in self.editors.library: #make buttons to open new types of tab
                editor_panes.append(tk.Button(editor_pane_frame, text = name, command = functools.partial(self.editors.create_new, name), **self.ui_styling.get(font_size = 'small', object_type = tk.Button)))
            
            tabs_frame = tk.Frame(self.frame)
            tabs_current_frame = tk.Frame(self.frame)
            tabs = []
            tabs_current = None
            ui_styling = None
        self.uiobjs = uiobjs
        self.uiobjs.frame = self.frame
        self.uiobjs.pagemethods = self.pagemethods
        self.editors.uiobjs = uiobjs
        self.uiobjs.ui_styling = self.ui_styling
        
        #pack all items
        i = 0
        for button in self.uiobjs.editor_panes:
            button.grid(row = 0, column = i, sticky = 'NESW')
            i += 1
        self.ui_styling.set_weight(self.uiobjs.editor_pane_frame, len(self.uiobjs.editor_panes) - 1, 0)
        
        #specify the positions of the UI elements
        self.uiobjs.editor_pane_frame.grid(row = 0, column = 0, sticky = 'NESW')
        self.uiobjs.tabs_frame.grid(row = 1, column = 0, sticky = 'NESW')
        self.uiobjs.tabs_current_frame.grid(row = 2, column = 0, sticky = 'NESW')
        
        self.frame.rowconfigure(2, weight = 1)
        self.frame.columnconfigure(0, weight = 1)
    
    def load(self, map_name):
        'Specify the map file to be used. Must be called before the editor is interacted with'
        self.map = Map(map_name) #this handles most of the interactions with the map files
        self.editors.map = self.map

class EditorTab:
    '''
    A tab for the editor
    '''
    def __init__(self, name, editorobj, index):
        self.name = name
        self.editorobj = editorobj
        self.index = index
        self.active = True #when a new tab is made, it is shown by default
        
        self.ui_styling = self.editorobj.uiobjs.ui_styling
        
        self.colour_idle = 'SystemButtonFace'
        self.colour_active = 'snow3'
        self.colour_close = 'red'
        self.colour_close_text = 'black'
        
        #construct UI
        self.header_frame = tk.Frame(self.editorobj.uiobjs.tabs_frame) #idk, the thing you click on to switch tabs
        self.header_button = tk.Button(self.header_frame, text = '####', command = self.show, **self.ui_styling.get(font_size = 'small', object_type = tk.Button))
        self.header_close = tk.Button(self.header_frame, text = 'X', command = self.destroy, **self.ui_styling.get(font_size = 'small', object_type = tk.Button))
        
        self.set_title('######') #set a blank title for the tab (ready for the editor to specify one)
        
        self.header_button.pack(side = tk.LEFT)
        self.header_close.pack(side = tk.LEFT)
        self.header_frame.pack(side = tk.LEFT)
        
        self.frame = tk.Frame(self.editorobj.uiobjs.tabs_current_frame)
        
        self.editor = self.editorobj.library[self.name](self.frame, self.editorobj, self)
    
    def show(self):
        'Show the tab'
        if not self.editorobj.uiobjs.tabs_current == None: #hide the current tab if there is one
            self.editorobj.uiobjs.tabs[self.editorobj.uiobjs.tabs_current].hide()
        self.frame.pack(fill = tk.BOTH, expand = True) #show the frame that contains all the tab objects
        self.editorobj.uiobjs.tabs_current = self.index #set the current tab to this one
        
        self.header_frame.config(bg = self.colour_active)
        self.header_button.config(bg = self.colour_active)
        self.header_close.config(bg = self.colour_close, fg = self.colour_close_text)
        
        self.active = True #change mode
    
    def hide(self):
        'Hide the tab'
        self.frame.pack_forget() #hide the frame that contains all the objects that make up the tab
        
        self.header_frame.config(bg = self.colour_idle)
        self.header_button.config(bg = self.colour_idle)
        self.header_close.config(bg = self.colour_close, fg = self.colour_close_text)
        
        self.active = False #change mode
    
    def destroy(self):
        'Completely destroy the tab (close it)'
        self.hide() #remove pane containing editor
        self.header_frame.pack_forget() #remove tab from the list of tabs on the screen
        self.editorobj.uiobjs.tabs[self.index] = None #remove this tab from the list of tabs in memory
        
        #set the focus to none if there are no availabble tabs
        update_current = True
        self.editorobj.uiobjs.tabs_current = None
        for item in self.editorobj.uiobjs.tabs:
            if not item == None:
                item.show()
    
    def set_title(self, text):
        'Set the title of the tab'
        self.header_button.config(text = '{}: {}'.format(self.name, text))

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
        self.root.title('Editor - add object')
        
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
        self.button_refresh = tk.Button(self.root, text = 'Refresh', command = self.populate_list, **self.ui_styling.get(font_size = 'small', object_type = tk.Button))
        
        #format all
        self.label_header.grid(column = 0, row = 0, columnspan = 2, sticky = 'NESW')
        self.list_frame.grid(column = 0, row = 1, columnspan = 2, sticky = 'NESW')
        self.button_choose.grid(column = 0, row = 2, sticky = 'NESW')
        self.button_refresh.grid(column = 1, row = 2, sticky = 'NESW')
        self.ui_styling.set_weight(self.root, 2, 2)
        self.root.rowconfigure(0, weight = 0)
        
        self.root.mainloop() #mainloop for new UI window (so that button presses and keybinds are handled properly
    
    def populate_list(self):
        #clear data (if there is any)
        self.list_list.delete(0, tk.END)
        self.paths = []
        
        #iterate through default material directory
        for material in os.listdir(os.path.join(self.map.path, 'materials')):
            data = self.map.get_json(os.path.join(self.map.path, 'materials', material)) #get the material file
            self.list_list.insert(tk.END, data['display name']) #use the material display name instead of the path in the list
            self.paths.append(os.path.join('materials', material)) #add the path to the list of paths so that it can be easily found when chosen
    
    def add_selection(self):
        selection = self.list_list.curselection()
        if not selection == (): #make sure that something has been selected
            self.parent.add_object({"coordinates": [0, 0], "material": self.paths[selection[0]]}) #tell the layout editor to add in the material at 0, 0