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

    def collide_all(self, rect_list):
        collision_items = [item.rect for item in rect_list]
        return self.rect.collidelistall(collision_items)

    def collide_rect(self, rect):
        return self.rect.colliderect(rect)

    def collide_line(self, line_coords):
        clipped = self.rect.clipline(line_coords)
        if clipped:
            return True
        else:
            return False

    def collide_point(self, point):
        return self.rect.collidepoint(point)

    def set_width(self, width):
        self.rect.w = width

    def set_height(self, height):
        self.rect.h = height

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

    def __init__(self, arg=None, is_display=False):
        if type(arg) is str:
            self.surf = pygame.image.load(arg)
        elif type(arg) is list or type(arg) is tuple:
            self.surf = pygame.Surface(arg)
        elif type(arg) is pygame.Surface:
            self.surf = arg
            is_display = True

        if not is_display:
            self.surf = self.surf.convert_alpha()

    def fill(self, color):
        self.surf.fill(color)

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

    def render_list(self, item_tuples):
        render_items = [(item[0].surf, item[1].rect) for item in item_tuples]
        self.surf.blits(render_items)

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

def get_text_surface(color, text, font, size, antialiased=False):
    text_obj = pygame.font.Font(font, size)
    text_surf = text_obj.render(text, antialiased, color)
    if len(color) == 4:
        text_surf.set_alpha(color[3])
    return Surface(text_surf)

sprite_atlas: dict = {}

def sprite_load(data, dimensions):
    if type(data) is Surface:
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

def keys_get_pressed():
    return pygame.key.get_pressed()

def mouse_get_position():
    return pygame.mouse.get_pos()

def mouse_get_pressed():
    return pygame.mouse.get_pressed()

def mouse_set_visible(is_visible:bool):
    pygame.mouse.set_visible(is_visible)

def check_should_quit():
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            return True
    return False

display_surface = Surface(is_display=True)
clock = Clock()

def start_frame(render_surface):
    render_surface.fill([0,0,0])

def end_frame():
    pygame.display.flip()
    clock.tick()

def display_refresh():
    pygame.display.quit()
    pygame.display.init()

def display_init(dimensions, flags) -> Surface:
    display_surface.surf = pygame.display.set_mode(dimensions, flags)
    return display_surface

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