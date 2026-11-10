@echo off
REM ==========================================================================
REM  Civil RMUTI Rc Design - build the Windows installer
REM  Double-click this file (or run it from Command Prompt) on Windows 10/11.
REM
REM  Needs: Python 3.12+ (python.org, "Add Python to PATH" ticked) and
REM         Inno Setup 6 (https://jrsoftware.org/isinfo.php)
REM         or: winget install JRSoftware.InnoSetup
REM  Result: dist_installer\CivilRMUTIRcDesign_Setup_<version>.exe
REM ==========================================================================
setlocal
cd /d "%~dp0\.."
set "ROOT=%CD%"
set "VENV=%ROOT%\.venv-build"
set "PY=%VENV%\Scripts\python.exe"

echo.
echo [1/6] Preparing build environment...
if not exist "%PY%" (
    py -3 -m venv "%VENV%" 2>nul || python -m venv "%VENV%"
    if errorlevel 1 goto :no_python
)
"%PY%" -m pip install --upgrade pip >nul
"%PY%" -m pip install -r requirements.txt pyinstaller pillow
if errorlevel 1 goto :fail

echo.
echo [2/6] Running tests...
"%PY%" -m pytest -q
if errorlevel 1 (
    echo Tests failed. Fix the errors before building an installer.
    goto :fail
)

echo.
echo [3/6] Creating the program icon...
"%PY%" packaging\make_icon.py
if errorlevel 1 goto :fail

"%PY%" -c "from app.core.constants import APP_VERSION; print(APP_VERSION)" > packaging\build\version.txt
set /p APPVER=<packaging\build\version.txt
echo Version: %APPVER%

echo.
echo [4/6] Building the program with PyInstaller (takes a few minutes)...
"%PY%" -m PyInstaller packaging\civil_rmuti_rc_design.spec --noconfirm --clean --distpath dist --workpath packaging\build\pyinstaller
if errorlevel 1 goto :fail

echo.
echo [5/6] Checking that the built program starts...
"%PY%" -c "import pathlib,sys; p=pathlib.Path('dist/CivilRMUTIRcDesign/CivilRMUTIRcDesign.exe'); sys.exit(0 if p.exists() else 1)"
if errorlevel 1 goto :fail

echo.
echo [6/6] Creating the installer with Inno Setup...
set "ISCC="
for %%p in ("%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" "%ProgramFiles%\Inno Setup 6\ISCC.exe" "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe") do (
    if exist %%p set "ISCC=%%~p"
)
if not defined ISCC (
    where iscc >nul 2>nul && set "ISCC=iscc"
)
if not defined ISCC (
    echo.
    echo Inno Setup 6 was not found, so no Setup.exe was made.
    echo The program itself is ready in:  dist\CivilRMUTIRcDesign\CivilRMUTIRcDesign.exe
    echo Install Inno Setup ^(winget install JRSoftware.InnoSetup^) and run this file again.
    goto :done
)
"%ISCC%" /DAppVersion=%APPVER% packaging\installer.iss
if errorlevel 1 goto :fail

echo.
echo ==========================================================================
echo  Installer ready:  dist_installer\CivilRMUTIRcDesign_Setup_%APPVER%.exe
echo ==========================================================================
start "" "%ROOT%\dist_installer"
goto :done

:no_python
echo Python was not found. Install Python 3.12+ from https://www.python.org
echo and tick "Add Python to PATH" during installation.
goto :fail

:fail
echo.
echo BUILD FAILED - see the messages above.
pause
exit /b 1

:done
pause
exit /b 0
