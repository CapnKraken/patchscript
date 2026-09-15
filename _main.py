import sys
import os
import shutil

import pygame_backend as backend
from gamemodule import *

import cProfile

# Set the default icon for the project.
try:
    #                       pyinstaller thing 
    img_path = os.path.join(sys._MEIPASS, "Patch_icon.png")
except:
    img_path = "icon/Patch_icon.png"
gobj.sprites['_icon'] = backend.Surface(img_path)

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

def main():

    # Create an output file for code.
    outfile = open("Output.txt", mode='w')
    outfile.close()

    apply_sysvars()

    # Create the root object
    root = gobj(root_path, {'name':'_root', 'position':[0,0]}, -1, True)

    while not (backend.check_should_quit() or gobj._FINISHED):

        updatekeystates(backend.keys_get_pressed())
        gobj.globs['_mouse_position'] = backend.mouse_get_position()
        gobj.globs['_real_fps'] = backend.clock.fps_get()

        backend.start_frame()
        
        # update all objects, respond to messages, and prepare for rendering
        root.obj_tick()
        for obj in gobj.dead_objects:
            gobj.delobj(obj)
        gobj.dead_objects.clear()

        root.respond()
        gobj.messages.clear()

        # render
        root.render()
        backend.render_objects(gobj.renderlist)
        gobj.renderlist.clear()
        
        runmusic()
        backend.end_frame()

        if gobj.apply_sysvars_flag:
            # apply the system variables (fullscreen, resolution, etc)
            gobj.apply_sysvars_flag = False

            if gobj.apply_fullscreen_change_flag:
                backend.display_refresh()
                gobj.apply_fullscreen_change_flag = False

            apply_sysvars()


import pstats

do_profiling = False

if do_profiling:
    with cProfile.Profile() as pr:
        main()
        with open( 'profile_output.txt', 'w' ) as f:
            pstats.Stats(pr, stream=f).strip_dirs().sort_stats("cumtime").print_stats()
else:
    main()

