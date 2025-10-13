## Overview

Patchscript is a minimalist game engine I created to be 'Scratch-like' in some of its functionality but much more open.  
Projects are made up of objects defined in .patch files and made up of scripts. Scripts run concurrently (but always in the same order) and perform independent behavior. Scripts can be paused using the 'wait' command and communicate with other objects via events.  

See Docs/CheatSheet.txt for a list of all script commands and more information about how things are connected.  
Take a look inside any of the sample projects to get a sense for how things work practically.  

## Usage

-Click one of the executables, then select a project folder. Patch will run the program defined in the folder.  
-ps_console.exe is the same as patchscript.exe; it just shows the console, allowing you to see the output of 'log' as well as error messages.  
-If you're not on Windows (or prefer not to use the executables), the python source code is provided. You'll need the pygame library installed.  

## Command line

-Navigate to the directory with the executables (or python scripts if you're using those)  

| Command | Function |
| ------- | -------- |
| \>patchscript | same as clicking the exe, pulls up a dialog to select a project. |
| \>patchscript projects/_default | run a specific project. |
| \>patchscript new project_name | create a new project in the root directory, as a copy of _default. |
| \>patchscript new project_name project_source | same as new, but you specify the project data to copy over. |

-These commands can also be used with 'ps_console' instead of 'patchscript' if you want console output.  
-If you're running the python source directly, the command line arguments still work, for example: python _main.py new new_proj_name   

## Editing

-I would recommend using Notepad++ to edit your scripts, as I've made a code highlighter for that editor.  
-In Notepad++:  

1. select 'Language' from the top bar, then 'User Defined Language' -> 'Define Your Language'  
2. click 'Import', and find the file 'Patchscript_NPP.xml'  
3. Reload Notepad++. Now 'Patchscript' should appear under 'Language'.  

-What I do for editing is have Notepad++ and the command line open side-by side, so I can use commands to easily test the project I'm building.  


-When you run a project, a file called 'Output.txt' will be created in the project root folder.  
-This file contains the 'true code' of all scripts loaded during execution. Essentially it's what the scripts become once loaded in.  
-For example, 'If' statements are converted to conditional jumps (same with loops).  
-When error messages give you line numbers, they're referring to the line numbers as displayed in this file, so it's invaluable for debugging.  
	
## Contents

| Item | Description |
| ----- | ----- |
| _default | Default project. Creating a new project from the command line will copy whatever's in this folder. If it's missing, you'll just get a blank new project. |
| docs | Contains a cheatsheet for all scripting commands, as well as some more in-depth documentation that isn't finished yet. |
| icon | Patchscript's window/taskbar icon. If you want to use the batch file to build the executables yourself, this folder needs to be here. |
| projects | The default directory for where Patch looks for projects when you run it with no arguments. If this folder isn't there, it'll use the root directory. |
| _main.py | The main game loop for Patch resides here. This is the file to run if you're using the Python files. |
| gamemodule.py | Contains most of Patch's functionality (everything but setup and the main loop). |
| autopackage.bat | Script to automate the packaging of the python scripts into the executables. You need pyinstaller if you're going to use this. |
| License.txt | Zlib license. |
| Patchscript_NPP.xml | Custom code highlighting for Notepad++ |
| *.exe | Windows executables, made using pyinstaller. They're the same, except ps_console will give you debug output. |
| README.md | I hope you know, having read this far... |