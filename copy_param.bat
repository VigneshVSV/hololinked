@REM git submodule does not somehow allow flat heirarchy, so we copy the changes from param to commit it there. 
robocopy .\\hololinked\\param ..\\param\\param package.json README.md LICENSE * /E
