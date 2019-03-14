import multiprocessing as mp
import winsound
import time
import math
import threading
import os
import sys
import json

class Sound:
    '''
    Highest level sound interface for winsound
    
    Unfortunately, winsound always adds a small gap between the beeps. I'm leaving this code in case I need it in the future, but right now it's redundant.
    '''
    def __init__(self):
        self.path = None
        
        self.sounds = {}
        
        self.interface = Interface()
    
    def load_library(self, path):
        self.path = path
        
        if os.path.isdir(path):
            for filename in os.listdir(path):
                if filename.startswith('snd_') and filename.endswith('.json'):
                    with open(os.path.join(path, filename), 'r') as file:
                        data = json.load(file)
                    self.sounds[data['name']] = data
    
    def load_map(self, map_name):
        self.load_library(os.path.join(sys.path[0], 'server', 'maps', map_name, 'sounds'))
    
    def play(self, name):
        sound = self.sounds[name]
        
        for timing, freq in sound['form']:
            if timing[0] == 0:
                self.interface.play(freq, timing[1])
            else:
                self.interface.schedule(time.time() + timing[0], freq, timing[1])

class Interface:
    def __init__(self):
        self.pipe, pipe = mp.Pipe()
        
        self.controller_process = threading.Thread(target = Controller, args = [pipe], name = 'Sound controller').start()
    
    def play(self, freq, dura):
        self.pipe.send(['play', [freq, dura]])
    
    def schedule(self, delay, freq, dura):
        self.pipe.send(['schedule', [freq, dura], delay + time.time()])
    
    def stop(self):
        self.pipe.send(['stop'])

class Controller:
    def __init__(self, pipe, resolution = 0.1, subdivisions = 10, overlap = 0.1):
        self.pipe = pipe
        self.resolution = resolution
        self.subdivisions = math.ceil(subdivisions)
        self.overlap = overlap
        
        self.cont = True
        self.sound_queue = {}
        self.sound_queue_locked = False #flag to lock sound queue
        
        threading.Thread(target = self.handler, name = 'Interface handler').start()
        threading.Thread(target = self.player, name = 'Sound splitter').start()
    
    def handler(self):
        while self.cont:
            data = self.pipe.recv()
            
            if data[0] == 'stop':
                self.cont = False
                
            elif data[0] == 'play':
                self.insert_at(self.get_stamp(time.time(), bias = 1), data[1])
                    
            elif data[0] == 'schedule':
                stamp = self.get_stamp(data[2], bias = 1)
                data.pop(2)
                
                if stamp < time.time():
                    self.insert_at(self.get_stamp(time.time(), bias = 1), data[1])
                else:
                    self.insert_at(stamp, data[1])
    
    def insert_at(self, pos, sound):
        num_insertions = math.ceil(sound[1] / self.resolution)
        
        for i in range(num_insertions):
            self._insert_direct(math.ceil((pos + (i * self.resolution)) / self.resolution) * self.resolution, sound[0])
    
    def _insert_direct(self, key, sound):
        self.reserve_queue()
        
        if not sound in self.sound_queue:
            self.sound_queue[key] = [sound]
        else:
            self.sound_queue[key].append(sound)
        
        self.release_queue()
    
    def player(self):
        while self.cont:
            start_time = time.time()
            
            self.reserve_queue()
            
            cull_keys = []
            to_play = []
            loop_stamp = self.get_stamp(time.time(), bias = 0)
            
            for key in list(self.sound_queue):
                if loop_stamp < time.time():
                    to_play = self.sound_queue[key]
                    cull_keys.append(key)
            
            
            if loop_stamp in self.sound_queue:
                to_play += self.sound_queue[loop_stamp].copy()
                self.sound_queue.pop(loop_stamp)
            
            now_key = self.get_stamp(time.time())
            if now_key in list(self.sound_queue):
                for sound in self.sound_queue[now_key]:
                    to_play.append(sound)
                cull_keys.append(now_key)
            
            for key in cull_keys:
                if key in self.sound_queue:
                    self.sound_queue.pop(key)
            
            self.release_queue()
            
            if not to_play == []:
                slot_allocations = self.subdivisions / len(to_play) #slots allocated per sound
                snd_queue = []
                
                total_allocated = 0
                for sound in to_play:
                    for i in range(int(total_allocated - int(total_allocated) + int(slot_allocations))):
                        snd_queue.append(sound)
                    total_allocated += slot_allocations
                
                if snd_queue is not []:
                    print(snd_queue)
                    self.play_snippet(snd_queue.copy())
            
            time.sleep(max([0, self.resolution - time.time() + start_time]))
    
    def get_stamp(self, timestamp, bias = 0):
        'Bias of 0 means low, 1 means high'
        if bias == 0:
            return math.floor(timestamp / self.resolution) * self.resolution
        return math.ceil(timestamp / self.resolution) * self.resolution
    
    def play_snippet(self, sounds):
        threading.Thread(target = self._play_snippet, args = [sounds], name = 'Sound snippet player').start()
    
    def _play_snippet(self, sounds):
        print('sounds', sounds)
        division_size = self.resolution / self.subdivisions
        for sound in sounds:
            threading.Thread(target = self._beep, args = [sound, division_size + self.overlap], name = 'Beep').start()
            time.sleep(division_size)
    
    def _beep(self, freq, dura):
        winsound.Beep(int(freq), int(dura * 1000))
    
    def reserve_queue(self):
        while self.sound_queue_locked:
            time.sleep(0.01)
        self.sound_queue_locked = True
    
    def release_queue(self):
        self.sound_queue_locked = False