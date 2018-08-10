import datetime
import os

class Log:
    def __init__(self, address, clear = True):
        self.address = address
        
        if clear:
            self.clear()
    
    def _write(self, text, newline = True):
        with open(self.address, 'w') as file:
            if newline:
                file.write('\n{}'.format(text))
            else:
                file.write(text)
    
    def _append(self, text, newline = True):
        with open(self.address, 'a') as file:
            if newline:
                file.write('\n{}'.format(text))
            else:
                file.write(text)
    
    def clear(self):
        self._write('Log {}:'.format(os.path.basename(self.address)), newline = False)
    
    def add(self, category, message):
        self._append('[{:^19}] [{:^20}]: {}'.format(self._getdatetime(), category, message))
    
    def _getdatetime(self):
        now = datetime.datetime.now()
        return '{}:{}:{} {}/{}/{}'.format(now.hour, now.minute, now.second, now.day, now.month, now.year)