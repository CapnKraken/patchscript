import pygame

pygame.init()
pygame.mixer.init()

class Rect:
    rect: pygame.Rect

    def __init__(self, arg1, arg2=None):
        if not arg2:
            self.rect = pygame.Rect(arg1)
        else:
            self.rect = pygame.Rect(arg1, arg2)

    def set_center(self, coordinates):
        self.rect.center = coordinates

    def collide_rect(self, rect):
        return self.rect.colliderect(rect)

    def get_x(self):
        return self.rect.x
    
    def get_y(self):
        return self.rect.y

class Font:
    font: pygame.font.Font

    def __init__(self, filename, size):
        self.font = pygame.font.Font(filename, size)

class Surface:
    surf: pygame.Surface = None

    def __init__(self, arg=None):
        if type(arg) is str:
            self.surf = pygame.image.load(arg)
        elif type(arg) is pygame.Surface:
            self.surf = arg

        try:
            self.surf = self.surf.convert_alpha()
        except:
            pass

    def scale(self, size):
        return Surface(pygame.transform.scale(self.surf, size))

    def rotate(self, angle):
        return Surface(pygame.transform.rotate(self.surf, angle))

    def flip(self, fliph, flipv):
        return Surface(pygame.transform.flip(self.surf, fliph, flipv))

    def color_shift(self, color_shift):
        assert len(color_shift) == 4
        if color_shift[0:3] == [0,0,0] and color_shift[3] != 0:
            self.surf.set_alpha(self.surf.get_alpha() + color_shift[3])
        elif color_shift != [0,0,0,0]:

            pixarr = pygame.PixelArray(self.surf)
            for i, row in enumerate(pixarr):
                for j, item in enumerate(row):
                    new_color = color_shift.copy()
                    mapped = self.surf.unmap_rgb(item)
                    if mapped.a != 0:

                        new_color[0] += mapped.r
                        new_color[1] += mapped.g
                        new_color[2] += mapped.b
                        new_color[3] += mapped.a

                        for k in range(len(new_color)):
                            if new_color[k] > 255:
                                new_color[k] = 255
                            if new_color[k] < 0:
                                new_color[k] = 0

                        pixarr[i,j] = tuple(new_color)
            self.surf = pixarr.make_surface()
            pixarr.close()

    def get_size(self):
        return self.surf.get_size()

class Canvas:
    surf: pygame.Surface = None

    def __init__(self, dimensions=None):
        self.surf = pygame.Surface(dimensions).convert_alpha()

    def fill(self, color):
        self.surf.fill(color)

    def render_item(self, surf, coordinates):
        render_item = surf.surf
        self.surf.blit(render_item, coordinates)

    def get_size(self):
        return self.surf.get_size()

    def save_to_file(self, filename, subrect=None):
        surface_to_save = self.surf
        if subrect:
            surface_to_save = self.surf.subsurface(pygame.Rect(subrect))
        pygame.image.save(surface_to_save, filename)

    def copy(self):
        return Surface(self.surf.copy())

    def draw_rect(self, color, rect, stroke, antialiased=False, border_radius=-1, c1=-1, c2=-1, c3=-1, c4=-1):
        pygame.draw.rect(self.surf, color, rect.rect, stroke, border_radius, c1, c2, c3, c4)

    def draw_ellipse(self, color, rect, stroke, antialiased=False):
        pygame.draw.ellipse(self.surf, color, rect.rect, stroke)

    def draw_polygon(self, color, points, stroke, antialiased=False):
        return Rect(pygame.draw.polygon(self.surf, color, points, stroke))

    def draw_line(self, color, point1, point2, stroke, antialiased=False):
        if antialiased:
            pygame.draw.aaline(self.surf, color, point1, point2, stroke)
        else:
            pygame.draw.line(self.surf, color, point1, point2, stroke)

sprite_atlas: dict = {}

def sprite_load(data, dimensions):
    if type(data) is Surface or type(data) is Canvas:
        # load from canvas
        loaded = data.surf
    else:
        # load from file
        filename: str = data
        loaded:pygame.Surface | None = sprite_atlas.get(filename)
        if not loaded:
            sprite_atlas[filename] = pygame.image.load(filename).convert_alpha()
            loaded = sprite_atlas[filename]

    if dimensions[0] == -1:
        return Surface(loaded)
    else:
        return Surface(loaded.subsurface(dimensions))

# Get a surface containing only a rectangle with the defined params.
def get_rect_surface(color, size, stroke, antialiased=False):
    surf = pygame.surface.Surface(size)
    rect = [0, 0, size[0], size[1]]
    pygame.draw.rect(surf, color, rect, stroke)
    return Surface(surf)

def get_ellipse_surface(color, size, stroke, antialiased=False):
    surf = pygame.surface.Surface(size)
    rect = [0, 0, size[0], size[1]]
    pygame.draw.ellipse(surf, color, rect, stroke)
    return Surface(surf)

def get_text_surface(color, text, font, size, antialiased=False):
    text_obj = pygame.font.Font(font, size)
    text_surf = text_obj.render(text, antialiased, color)
    if len(color) == 4:
        text_surf.set_alpha(color[3])
    return Surface(text_surf)

class CollisionMask:
    mask: pygame.Mask 

    def __init__(self, source_surface:Surface):
        self.mask = pygame.mask.from_surface(source_surface.surf)

    def overlap(self, other, offset):
        return self.mask.overlap(other.mask, offset)

class Clock:
    clock: pygame.time.Clock
    target_fps: int

    def __init__(self):
        self.clock = pygame.time.Clock()

    def fps_get(self):
        return self.clock.get_fps()

    def tick(self):
        self.clock.tick_busy_loop(self.target_fps)

display_surface = None
render_surface = None
window_size = (0, 0)
screen_resolution = (0, 0)
screen_rotation = 0
render_list = []
clock = Clock()

def keys_get_pressed():
    return pygame.key.get_pressed()

def mouse_get_position():
    global screen_resolution, window_size

    adjusted_pos = list(pygame.mouse.get_pos())

    scale_x = screen_resolution[0] / window_size[0]
    scale_y = screen_resolution[1] / window_size[1]

    adjusted_pos[0] *= scale_x
    adjusted_pos[1] *= scale_y

    return adjusted_pos

def mouse_get_pressed():
    return pygame.mouse.get_pressed()

def mouse_set_visible(is_visible:bool):
    pygame.mouse.set_visible(is_visible)

def check_should_quit():
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            return True
    return False

def start_frame():
    global render_surface
    render_surface.fill([0,0,0])

def end_frame():
    global render_surface, window_size, screen_rotation
    scaled = pygame.transform.scale(render_surface, window_size)
    if screen_rotation != 0:
        scaled = pygame.transform.rotate(scaled, screen_rotation)

    display_surface.blit(scaled, (0,0))
    pygame.display.flip()
    clock.tick()

def display_refresh():
    pygame.display.quit()
    pygame.display.init()

def display_init(dimensions, rotation, flags):
    global display_surface, window_size, screen_rotation
    if rotation % 2 == 0:
        display_surface = pygame.display.set_mode(dimensions, flags)
    else:
        display_surface = pygame.display.set_mode((dimensions[1], dimensions[0]), flags)
    window_size = dimensions
    screen_rotation = rotation

def render_init(dimensions):
    global render_surface, screen_resolution
    render_surface = pygame.surface.Surface(dimensions).convert_alpha()
    screen_resolution = dimensions

def add_render_object(item):
    global render_list
    render_list.append((item[0].surf, item[1].rect))

def render_objects():
    global render_surface, render_list
    render_surface.blits(render_list)
    render_list.clear()

def display_set_caption(caption:str):
    pygame.display.set_caption(caption)

def display_set_icon(icon:Surface):
    pygame.display.set_icon(icon.surf)
    

class Music:
    def set_volume(volume):
        pygame.mixer.music.set_volume(volume)

    def is_playing():
        return pygame.mixer.music.get_busy()

    def play_new(filename):
        pygame.mixer.music.load(filename)
        pygame.mixer.music.play()

    def play(start_millis:int):
        pygame.mixer.music.play(start=start_millis / 1000.0)

    def fade_out(millis):
        pygame.mixer.music.fadeout(millis)

    def get_position():
        return pygame.mixer.music.get_pos()

    def set_position(pos_millis):
        pygame.mixer.music.set_pos(pos_millis / 1000)

    def stop():
        pygame.mixer.music.stop()

    

class Sound:
    duration:int
    sound:pygame.mixer.Sound

    def __init__(self, filename:str, duration:int=0):
        self.sound = pygame.mixer.Sound(filename)
        if duration > 0:
            self.duration = duration
        else:
            self.duration = int(self.sound.get_length() * 1000)

    def set_volume(self, volume):
        self.sound.set_volume(volume)

    def play(self):
        self.sound.play(maxtime=self.duration)

def sound_pause():
    pygame.mixer.pause()

def sound_resume():
    pygame.mixer.unpause()