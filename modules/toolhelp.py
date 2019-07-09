import tkinter as tk
import os
import sys
import threading
import json

class Help:
    def __init__(self, help_page):
        self.help_page = help_page

        threading.Thread(target = self._mainloop, daemon = True, name = 'Help window process').start()
    
    def _mainloop(self):
        self.root = tk.Tk()
        self.root.title('Help')

        self.textbox = tk.Text(self.root, font = ('', 11), height = 25, width = 65, state = tk.DISABLED)
        self.scrollbar = tk.Scrollbar(self.root, command = self.textbox.yview)
        self.textbox.config(yscrollcommand = self.scrollbar.set)

        self.scrollbar.pack(side = tk.RIGHT, fill = tk.Y)
        self.textbox.pack(side = tk.LEFT, fill = tk.BOTH, expand = True)

        self.load_page(self.help_page)

        self.root.mainloop()
    
    def load_page(self, name):
        self.textbox.config(state = tk.NORMAL)

        if type(name) == list:
            path = os.path.join(sys.path[0], 'docs', *name)
        else:
            path = os.path.join(sys.path[0], 'docs', name)

        with open(path, 'r') as file:
            self.help_contents = json.load(file)

        self.root.title('Help - {}'.format(self.help_contents['title']))

        self.textbox.delete(0.0, tk.END)
        if type(self.help_contents['contents']) == list:
            for line in self.help_contents['contents']:
                self.textbox.insert(tk.END, line + '\n')

        else:
            self.textbox.insert(0.0, self.help_contents['contents'])
        
        self.textbox.config(state = tk.DISABLED)