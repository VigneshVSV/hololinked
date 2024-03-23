@ECHO OFF

pushd %~dp0

REM Command file for Sphinx documentation

if "%SPHINXBUILD%" == "" (
	set SPHINXBUILD=sphinx-build
)
set SOURCEDIR=source
set BUILDDIR=build
set DOC_ADDRESS=http://localhost:8000

%SPHINXBUILD% >NUL 2>NUL
if errorlevel 9009 (
	echo.
	echo.The 'sphinx-build' command was not found. Make sure you have Sphinx
	echo.installed, then set the SPHINXBUILD environment variable to point
	echo.to the full path of the 'sphinx-build' executable. Alternatively you
	echo.may add the Sphinx directory to PATH.
	echo.
	echo.If you don't have Sphinx installed, grab it from
	echo.https://www.sphinx-doc.org/
	exit /b 1
)

if "%1" == "" goto help

if "%1" == "server" goto server

if "%1" == "open-in-chrome" goto open-in-chrome

if "%1" == "host-doc" goto host-doc

%SPHINXBUILD% -M %1 %SOURCEDIR% %BUILDDIR% %SPHINXOPTS% %O%
goto end

:help
%SPHINXBUILD% -M help %SOURCEDIR% %BUILDDIR% %SPHINXOPTS% %O%
goto end

:server
echo server is hosted at %DOC_ADDRESS%, change port directory in make file if necessary
python -m http.server --directory build\html
goto end 

:open-doc-in-browser
start explorer %DOC_ADDRESS%
goto end

:host-doc 
echo server is hosted at %DOC_ADDRESS%, change port directory in make file if necessary
start explorer %DOC_ADDRESS%
python -m http.server --directory build\html
goto end

:end
popd
