import sys
import os
import shutil

import pygame
from pygame.locals import *
from gamemodule import *

import cProfile

# Set the default icon for the project.
try:
    #                       pyinstaller thing 
    img_path = os.path.join(sys._MEIPASS, "Patch_icon.png")
except:
    img_path = "icon/Patch_icon.png"
gobj.sprites['_icon'] = pygame.image.load(img_path)

root_path = 'scripts/_root.patch'

#region Command line args
# Allow you to specify a project from the command line or create a new project.
if len(sys.argv) > 1:
    if sys.argv[1].lower() == 'new':
        current_directory = os.getcwd()

        # Now we want to make a new project.
        project_name = "untitled"
        if len(sys.argv) > 2:
            project_name = sys.argv[2]
        
        # Make sure you're not overwriting anything
        counter = 0
        orig_name = project_name
        while os.path.isdir(project_name):
            counter += 1

            # Sets the project name to {given name}1, 2, 3, etc.
            project_name = f"{orig_name}{counter}"

        # Allow specification of project to copy over to new.
        source_proj = "_default"
        if len(sys.argv) > 3 and os.path.isdir(sys.argv[3]):
            source_proj = sys.argv[3]
        
        try:
            shutil.copytree(current_directory + "/"+source_proj, current_directory+"/"+project_name)
        except FileNotFoundError:
            # If there's no _default project in the root directory, create an empty skeleton project folder.
            dirs = ['scripts', 'audio', 'visuals', 'fonts', 'data']

            for item in dirs:
                os.makedirs(f"{current_directory}/{project_name}/{item}")

            with open(f"{current_directory}/{project_name}/scripts/_root.patch", "w") as file:
                file.write("# Empty Project.")
        except OSError as e:
            print(f"Improper file path.\n{e}")
        except Exception as e:
            print(f"Oh no! Something went wrong!\n{e}")
        
        sys.exit()
    else:
        # Switch to the specified project.
        os.chdir(sys.argv[1])
#endregion

#region Project selection dialog
has_root = False
while not has_root:
    try:
        root_file = open(root_path, mode='r')
        root_file.close()
        has_root = True
    except(FileNotFoundError):
        # For finding a project folder if root not found immediately
        import tkinter
        from tkinter import filedialog

        # Get rid of tkinter baggage.
        tkroot = tkinter.Tk()
        tkroot.withdraw()

        # See if there's a project folder, otherwise look at the root folder.
        if os.path.isdir(os.getcwd() + "/projects"):
            directory_path = filedialog.askdirectory(initialdir=os.getcwd()+"/projects")
        else:
            directory_path = filedialog.askdirectory(initialdir=os.getcwd())

        try:
            os.chdir(directory_path)
        except:
            sys.exit()
#endregion

def do_game_loop(root:gobj, main_screen:pygame.Surface):
    main_screen.fill(color=[0,0,0])

    # update all objects, respond to messages, and render
    root.obj_tick()
    root.respond()
    root.render()

    main_screen.blits(gobj.renderlist)
    gobj.renderlist.clear()
    gobj.messages.clear()

    for obj in gobj.dead_objects:
        gobj.delobj(obj)
    gobj.dead_objects.clear()
    
    runmusic()

def main():

    pygame.init()
    pygame.mixer.init()

    # Create an output file for code.
    outfile = open("Output.txt", mode='w')
    outfile.close()

    info = apply_sysvars()
    display_screen = info[0]
    main_screen = info[1]
    target_framerate = info[2]
    win_size = info[3]
    screen_res = info[4]
    busy_wait = info[5]

    clock = pygame.time.Clock()

    # Create the root object
    root = gobj(root_path, {'name':'_root', 'position':[0,0]}, -1, True)

    frame:int = 0
    running = True
    while running:

        updatekeystates(pygame.key.get_pressed())
        gobj.globs['_mouse_position'] = adjust_mouse_pos(list(pygame.mouse.get_pos()), win_size, screen_res)
        gobj.globs['_real_fps'] = clock.get_fps()

        if pygame.event.get(QUIT):
            running = False

        do_game_loop(root, main_screen)

        if gobj._FINISHED:
            running = False

        scaled = pygame.transform.scale(main_screen, win_size)
        display_screen.blit(scaled, (0,0))

        pygame.display.flip()
        # For some reason I was getting freezes when using busy loop. No clue why.
        if busy_wait:
            clock.tick_busy_loop(target_framerate) 
        else:
            clock.tick(target_framerate)

        if gobj.apply_sysvars_flag:
            # apply the system variables (fullscreen, resolution, etc)
            gobj.apply_sysvars_flag = False

            if gobj.apply_fullscreen_change_flag:
                pygame.display.quit()
                pygame.display.init()
                gobj.apply_fullscreen_change_flag = False

            info = apply_sysvars()

            display_screen = info[0]
            main_screen = info[1]
            target_framerate = info[2]
            win_size = info[3]
            screen_res = info[4]
            busy_wait = info[5]

# adjusts the mouse position based on screen scale
def adjust_mouse_pos(m_pos, win_size, screen_res):
    adjusted_pos = m_pos
    scale_x = screen_res[0] / win_size[0]
    scale_y = screen_res[1] / win_size[1]
    adjusted_pos[0] *= scale_x
    adjusted_pos[1] *= scale_y
    return adjusted_pos

import pstats

do_profiling = False

if do_profiling:
    with cProfile.Profile() as pr:
        main()
        with open( 'profile_output.txt', 'w' ) as f:
            pstats.Stats(pr, stream=f).strip_dirs().sort_stats("cumtime").print_stats()
else:
    main()

