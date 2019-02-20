import modules.lineintersection
import math

class CalcSegment:
    def __init__(self, x0, x1, pipe, map_data, materials, light_sources, blocking_panels, shadows = True):
        self.pipe = pipe
        self.map_data = map_data
        self.materials = materials
        self.light_sources = light_sources
        self.blocking_panels = blocking_panels
        self.shadows = shadows
        
        for x in range(x0, x1, 1):
            self.pipe.send(['message', '{}-{} at {}'.format(x0, x1, x)])
            for y in range(1, 600, 1):
                self.pipe.send([[x, y], self.calc_light(x, y)])
        self.pipe.send('done')
    
    def calc_light(self, x, y):
        light_level = self.map_data['lighting']['background']
        for source in self.light_sources:
            if self.shadows:
                passthroughs = []
                for panel in self.blocking_panels:
                    result = self.line_passes_through(x, y, *source['coordinates'], panel)
                    if not result == False:
                        passthroughs.append([result, panel])
        
            dist = math.hypot(x - source['coordinates'][0], y - source['coordinates'][1]) * self.map_data['lighting']['dist mult']
            
            if dist == 0:
                source_light = self.materials[source['material']]['light']['emit']
            else:
                source_light = (1 / pow(dist * self.map_data['lighting']['dist mult'], 2)) * self.materials[source['material']]['light']['emit']
                if self.shadows:
                    for distance, panel in passthroughs:
                        if self.materials[panel['material']]['light']['block'] == 1: #don't bother doing the light calcuation if one of the panels will block all light
                            source_light = 0
                        else:
                            source_light -= distance * self.materials[panel['material']]['light']['block'] * self.map_data['lighting']['dist mult']
            
            light_level += source_light
                
        return int((min(light_level, self.map_data['lighting']['dynamic range']) / self.map_data['lighting']['dynamic range']) * 255)

    def line_passes_through(self, x0, y0, x1, y1, panel):
        'Get light sources with a line of sight on coordinates'
        last_x = None
        last_y = None
        i = 0
        intersections = []
        for pan_x, pan_y in self.materials[panel['material']]['hitbox']:
            pan_x += panel['coordinates'][0]
            pan_y += panel['coordinates'][1]
            
            i += 1
            if not last_x == None:
                if i == len(self.materials[panel['material']]['hitbox']):
                    last_x = self.materials[panel['material']]['hitbox'][0][0] + panel['coordinates'][0]
                    last_y = self.materials[panel['material']]['hitbox'][0][1] + panel['coordinates'][1]
                
                result = modules.lineintersection.wrap_np_seg_intersect([[last_x, last_y], [pan_x, pan_y]], [[x0, y0], [x1, y1]], considerCollinearOverlapAsIntersect = True)
                if not (type(result) == bool or result is None):
                    intersections.append([result[0], result[1]])
                
                elif result == True: #co linear overlap
                    intersections.append([0, 0])
            
            last_x = pan_x
            last_y = pan_y
        
        if intersections == []:
            return False
        else:
            if len(intersections) == 1:
                intersections.append([x0, y0])
            return math.hypot(intersections[0][0] - intersections[1][0], intersections[1][1] - intersections[0][1])