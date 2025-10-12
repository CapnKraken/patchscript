:: Just a batch file to help update the executables when the python files are updated.

del *.exe

pyinstaller --clean --onefile --noconsole --name=patchscript --icon Icon\Patch_icon.ico --add-data "Icon/Patch_icon.png;." _main.py
move dist\patchscript.exe .

pyinstaller --clean --onefile --name=ps_console --icon=Icon\Patch_icon.ico --add-data "Icon/Patch_icon.png;." _main.py
move dist\ps_console.exe .

del *.spec
rmdir /s /q build
rmdir /s /q dist