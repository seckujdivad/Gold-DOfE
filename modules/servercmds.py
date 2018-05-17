import tkinter as tk
import threading

class ServerCommandLineUI:
    def __init__(self, command_handler, default_title = 'Server Command Line'):
        self.default_title = default_title
        self.command_handler = command_handler
    
        threading.Thread(target = self.main_thread, name = 'Server command line UI')
    
    def main_thread(self):
        self.root = tk.Tk()
        
        self.listbox_frame = tk.Frame(self.frame)
    
    def process_command(self):
        self.listbox.see(tk.END)
    
    def set_title_status(self, status):
        if status == '':
            self.root.title(self.default_title)
        else:
            self.root.title('{} - {}'.format(self.default_title, status))