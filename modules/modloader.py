from importlib import util
import os

class ModLoader:
    def __init__(self, path):
        self.path = path
    
    def load(self, prefix):
        output = []
        for pages_name in os.listdir(self.path):
            if (not (pages_name.startswith('.') or pages_name.startswith('_'))) and os.path.isfile(os.path.join(self.path, pages_name)):
                spec = util.spec_from_file_location('pagelib', os.path.join(self.path, pages_name))
                script_module = util.module_from_spec(spec)
                spec.loader.exec_module(script_module)
                
                for page_name in dir(script_module):
                    if page_name.startswith(prefix):
                        output.append(getattr(script_module, page_name))
        
        return output