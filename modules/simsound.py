import multiprocessing as mp
import winsound
import time
import math

class Interface:
    def __init__(self):
        self.pipe, pipe = mp.Pipe()
        
        self.controller_process = mp.Process(target = Controller, args = [pipe], name = 'Sound controller').start()
    
    def play(self, freq, dura):
        self.pipe.send(['play', [freq dura]])
    
    def schedule(self, timestamp, freq, dura):
        self.pipe.send(['schedule', [freq, dura], timestamp)
    
    def stop(self):
        self.pipe.send(['stop'])

class Controller:
    def __init__(self, pipe, resolution = 10, subdivisions = 10):
        self.pipe = pipe
        self.resolution = math.ceil(resolution)
        self.subdivisions = math.ceil(subdivisions)
        
        self.cont = True
        self.sound_queue = {}
    
    def handler(self):
        while self.cont:
            if data == None:
                data = self.pipe.recv()
            
            if data[0] == 'stop':
                self.cont = False
            elif data[0] == 'play':
                if not 'next' in self.sound_queue:
                    self.sound_queue['next'] = [data[1]]
                else:
                    self.sound_queue['next'].append(data[1])
                data = None
            elif data[0] == 'schedule':
                if data[2] < time.time():
                    data[0] = 'play'
                    data.pop(2)
                else:
                    
                    data = None
    
    def player(self):
        while self.cont:
            pass
    
    def get_stamp(self, timestamp, bias = 0):
        'Bias of 0 means low, 1 means high'
        timestamp = timestamp / self.resolution
        if bias == 0:
            timestamp = math.floor(timestamp)
        else:
            timestamp = math.ceil(timestamp)
        return timestamp * self.resolution