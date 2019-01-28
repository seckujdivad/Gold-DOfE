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
            
            
            decrease = 0
            blocked = False
            
            if self.shadows:
                for passthrough in passthroughs:
                    if self.materials[passthrough[1]['material']]['light']['block'] == 1:
                        blocked = True
                    decrease += self.materials[passthrough[1]['material']]['light']['block'] * passthrough[0] * self.map_data['lighting']['dist mult'] * self.map_data['lighting']['dist mult']
            
            if dist == 0:
                light_level = self.map_data['lighting']['dynamic range']
            elif blocked:
                pass
            else:
                light_level += (1 / pow(dist, 2)) * self.materials[source['material']]['light']['emit'] - decrease
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
                
                '''if not ((last_x - pan_x == 0) or (x0 - x1 == 0)):
                    grad_1 = (last_y - pan_y) / (last_x - pan_x)
                    grad_2 = (y0 - y1) / (x0 - x1)
                    
                    if not grad_1 == grad_2:
                        c_1 = pan_y - (grad_1 * pan_x)
                        c_2 = y1 - (grad_2 * x1)
                        
                        x_intersection = (c_1 - c_2) / (grad_2 - grad_1)
                        
                        if (x0 < x_intersection < x1) or (x1 < x_intersection < x0):
                            intersections.append([x_intersection, (grad_1 * x_intersection) + c_1])
                
                if ((last_x - pan_x == 0) and (x0 - x1 == 0)) and x0 == last_x and (y0 < last_y < y1 or y1 < last_y < y0):
                    intersections.append([x0, y0])
                    intersections.append([x1, y1])'''
                
                result = modules.lineintersection.wrap_np_seg_intersect([[last_x, last_y], [pan_x, pan_y]], [[x0, y0], [x1, y1]], considerCollinearOverlapAsIntersect = True)
                if not (type(result) == bool or result is None):
                    intersections.append([result[0], result[1]])
                
                if result == True: #co linear overlap
                    intersections.append([0, 0])
            
            last_x = pan_x
            last_y = pan_y
        
        if intersections == []:
            return False
        else:
            if len(intersections) == 1:
                intersections.append([x0, y0])
            return math.hypot(intersections[0][0] - intersections[1][0], intersections[1][1] - intersections[0][1])
        