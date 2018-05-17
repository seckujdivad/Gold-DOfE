import tkinter as tk
import threading

import modules.ui

class ServerCommandLineUI:
    def __init__(self, command_handler, default_title = 'Server Command Line'):
        self.default_title = default_title
        self.command_handler = command_handler
    
        threading.Thread(target = self.main_thread, name = 'Server command line UI').start()
    
    def main_thread(self):
        self.root = tk.Tk()
        
        self.listbox_frame = tk.Frame(self.root)
        self.listbox_box = tk.Listbox(self.listbox_frame, font = self.styling.fonts.small)
        self.listbox_bar = tk.Scrollbar(self.listbox_frame, command = self.listbox_box.yview)
        self.listbox_box.config(yscrollcommand = self.listbox_bar.set)
        
        self.command_field = tk.Entry(self.root, font = self.styling.fonts.small)
        self.command_button = tk.Button(self.root, text = 'Submit', command = self.process_command, font = self.styling.fonts.small, relief = self.styling.relief, overrelief = self.styling.overrelief)
        
        self.listbox_bar.pack(side = tk.RIGHT, fill = tk.Y)
        self.listbox_box.pack(side = tk.LEFT, fill = tk.BOTH, expand = True)
        self.listbox_frame.grid(row = 0, column = 0, columnspan = 2, sticky = 'NESW')
        
        self.command_field.grid(row = 1, column = 0, sticky = 'NESW')
        self.command_button.grid(row = 1, column = 1, sticky = 'NESW')
        
        self.root.rowconfigure(0, weight = 1)
        self.root.columnconfigure(0, weight = 1)
        
        self.root.geometry('400x300')
        self.set_title_status()
        self.root.bind('<Return>', self.process_command)
        
        self.root.mainloop()
    
    def process_command(self, event = None):
        data = self.command_field.get()
        self.command_field.delete(0, tk.END)
        self.listbox_box.insert(tk.END, '] {}'.format(data))
        self.listbox_box.see(tk.END)
        
        data_out = self.command_handler(data)
        for line in data_out.split('\n'):
            self.listbox_box.insert(tk.END, line)
        self.listbox_box.see(tk.END)
    
    def set_title_status(self, status = ''):
        if status == '':
            self.root.title(self.default_title)
        else:
            self.root.title('{} - {}'.format(self.default_title, status))
    
    class styling:
        class fonts:
            typeface = 'Courier New'
            small = (typeface, 10)
            medium = (typeface, 15)
            large = (typeface, 25)
        relief = tk.FLAT
        overrelief = tk.GROOVE