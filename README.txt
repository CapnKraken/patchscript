Patchscript is a minimalist game engine I created to be 'Scratch-like' in some of its functionality but much more open.
Projects are made up of objects defined in .patch files and made up of scripts. Scripts run concurrently (but always in the same order) and perform independent behavior. Scripts can be paused using the 'wait' command and communicate with other objects via events.

See Docs/CheatSheet.txt for a list of all script commands.
Take a look inside any of the sample projects to get a sense for how things work in the engine.

Usage:
-Click one of the executables, then select a project folder. Patch will run the program defined in the folder.
-ps_console.exe is the same as patchscript.exe, it just shows the console, allowing you to see the output of 'log' as well as error messages.
-If you're not on Windows, the python source code is provided. You'll need the pygame library installed.

Command line:
-Navigate to the directory with the executables (or python scripts if you're using those)

>patchscript                                    | same as clicking the exe, pulls up a dialog to select a project.
>patchscript Projects/_default	                | run a specific project.
>patchscript new project_name	                | create a new project in the Projects folder, as a copy of _default.
>patchscript new project_name project_source    | same as new, but you specify the project data to copy over.

-These commands can also be used with 'ps_console' instead of 'patchscript'
-If you're running the python source directly, the command line arguments still work.

Editing:
-I would recommend using Notepad++ to edit your scripts, as I've made a code highlighter for that editor.
-In Notepad++:
	select 'Language' from the top bar, then 'User Defined Language' -> 'Define Your Language'
	click 'Import', and find the file 'Patchscript_NPP.xml'
	Reload Notepad++. Now 'Patchscript' should appear under 'Language'.
-What I do for editing is have Notepad++ and the command line open side-by side, so I can use commands to easily run the project I'm building.


-When you run a project, a file called 'Output.txt' will be created in the project root folder.
-This file contains the 'true code' of all scripts loaded during execution. Essentially it's what the scripts become once loaded in.
-For example, 'If' statements are converted to conditional jumps (same with loops).
-When error messages give you line numbers, they're referring to the line numbers as displayed in this file, so it's invaluable for debugging.
	
	
