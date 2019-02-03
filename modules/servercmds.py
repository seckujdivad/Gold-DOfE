import tkinter as tk
import multiprocessing as mp
import threading

class ServerCommandLineUI:
    def __init__(self, command_handler, pipe, frame = None, default_title = 'Server Command Line'):
        self.command_handler = command_handler
        self.pipe = pipe
        self.frame = frame
        self.default_title = default_title
        
        self.quit = False
    
        self.process_interface, process_interface = mp.Pipe()
        mp.Process(target = _UI, args = [process_interface, frame], name = 'Server command line UI process').start()
        
        threading.Thread(target = self._receiver).start()
        threading.Thread(target = self._server_receiver).start()
        
        self.process_interface.send(['set title', 'Server command line'])
    
    def _server_receiver(self):
        while not self.quit:
            input_data = self.pipe.recv()
            self.process_interface.send(['push', input_data])
    
    def _receiver(self):
        command = ''
        while (not command == 'quit') and (not self.quit):
            input_data = self.process_interface.recv()
            command = input_data[0]
            args = input_data[1:]
            
            if command == 'cmdout':
                self.process_interface.send(['push', self.command_handler(args[0])])
        self.quit = True

class _UI:
    def __init__(self, process_interface, frame):
        self.process_interface = process_interface
        
        self.quit = False
        
        if frame is None:
            self.toplevel = tk.Tk()
        else:
            self.toplevel = frame
        
        threading.Thread(target = self.receiver).start()
        
        ## make ui
        #command output box
        self.output_frame = tk.Frame(self.toplevel)
        self.output_listbox = tk.Listbox(self.output_frame, font = self.styling.fonts.small)
        self.output_bar = tk.Scrollbar(self.output_frame, command = self.output_listbox.yview)
        self.output_listbox.config(yscrollcommand = self.output_bar.set)
        self.output_bar.pack(side = tk.RIGHT, fill = tk.Y)
        self.output_listbox.pack(side = tk.LEFT, fill = tk.BOTH, expand = True)
        
        #command entry field
        self.cmd_var = tk.StringVar()
        self.cmd_field = tk.Entry(self.toplevel, textvariable = self.cmd_var, font = self.styling.fonts.small)
        self.cmd_button = tk.Button(self.toplevel, text = 'Submit', command = self.submit_command, font = self.styling.fonts.small, relief = self.styling.relief, overrelief = self.styling.overrelief)
        
        if type(self.toplevel) == tk.Tk:
            self.toplevel.bind('<Return>', self.submit_command)
        else:
            self.cmd_button.bind('<Return>', self.submit_command)
        
        #grid items
        self.output_frame.grid(column = 0, row = 0, columnspan = 2, sticky = 'NESW')
        self.cmd_field.grid(column = 0, row = 1, sticky = 'NESW')
        self.cmd_button.grid(column = 1, row = 1, sticky = 'NESW')
        
        #set grid weights
        self.toplevel.columnconfigure(0, weight = 1)
        self.toplevel.rowconfigure(0, weight = 1)
        
        ## end of make ui
        
        if self.toplevel is not None:
            self.toplevel.geometry('400x300')
            self.toplevel.mainloop()
            self.quit = True
    
    def receiver(self):
        while not self.quit:
            input_data = self.process_interface.recv()
            command = input_data[0]
            args = input_data[1:]
            
            if command == 'set title':
                if type(self.toplevel) is tk.Tk:
                    self.toplevel.title(args[0])
            elif command == 'quit':
                self.quit = True
            elif command == 'push':
                for line in args[0].split('\n'):
                    if line.startswith('$$') and line.endswith('$$') and len(line) > 4: #console output operation
                        if line[2:len(line) - 2] == 'clear':
                            self.output_listbox.delete(0, tk.END)
                        elif line[2:len(line) - 2] == 'close_window':
                            self.quit = True
                    else:
                        self.output_listbox.insert(tk.END, line)
            print(command)
                    
        if type(self.toplevel) is tk.Tk:
            self.toplevel.destroy()

        self.handle_command('sv_quit')
        self.process_interface.send(['quit'])
    
    def submit_command(self, event = None):
        self.handle_command(self.cmd_var.get())
        self.cmd_var.set('')
        
    def handle_command(self, cmd):
        self.output_listbox.insert(tk.END, '] {}'.format(cmd))
        self.process_interface.send(['cmdout', cmd])
    
    class styling:
        class fonts:
            typeface = 'Courier New'
            small = (typeface, 10)
            medium = (typeface, 15)
            large = (typeface, 25)
        relief = tk.FLAT
        overrelief = tk.GROOVE