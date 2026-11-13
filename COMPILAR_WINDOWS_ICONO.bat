@echo off
setlocal
cd /d "%~dp0"

set "ASSETS_DIR=%~dp0assets"
set "ICON_FILE=%ASSETS_DIR%\forjagym.ico"

 echo ================================================
 echo      FORJAGYM - COMPILACION CON ICONO OFICIAL
 echo ================================================
 echo.
echo IMPORTANTE: cierre ADMIN y FICHAJE antes de continuar.
echo Los dos EXE utilizaran exactamente el mismo icono.
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python no esta instalado o no esta agregado al PATH.
    pause
    exit /b 1
)

if not exist "%ASSETS_DIR%\logo_forjagym.png" (
    echo ERROR: No se encuentra "%ASSETS_DIR%\logo_forjagym.png"
    pause
    exit /b 1
)

if not exist "%ICON_FILE%" (
    echo ERROR: No se encuentra "%ICON_FILE%"
    pause
    exit /b 1
)

python -m pip install --upgrade pyinstaller customtkinter Pillow openpyxl reportlab
if errorlevel 1 goto error

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
mkdir dist

echo.
echo [1/2] Compilando ADMIN.exe con icono oficial...
python -m PyInstaller --noconfirm --clean --onefile --windowed --name ADMIN --distpath dist --workpath build\admin --specpath build --icon "%ICON_FILE%" --add-data "%ASSETS_DIR%;assets" --collect-all customtkinter --hidden-import PIL._tkinter_finder main.py
if errorlevel 1 goto error

echo.
echo [2/2] Compilando FICHAJE.exe con el mismo icono oficial...
python -m PyInstaller --noconfirm --clean --onefile --windowed --name FICHAJE --distpath dist --workpath build\fichaje --specpath build --icon "%ICON_FILE%" --add-data "%ASSETS_DIR%;assets" --collect-all customtkinter --hidden-import PIL._tkinter_finder fichaje_main.py
if errorlevel 1 goto error

if exist datos (
    echo.
    echo Copiando base de datos y carpeta datos a dist...
    xcopy datos dist\datos\ /E /I /Y >nul
) else (
    mkdir dist\datos
    echo AVISO: No existia carpeta datos. Se creara una base nueva al iniciar.
)

(echo FORJAGYM - VERSION PORTABLE^&echo.^&echo Ejecutar ADMIN.exe para administracion.^&echo Ejecutar FICHAJE.exe para control de acceso.^&echo Ambos programas comparten la base de datos ubicada en datos\forjagym.db.^&echo Ambos ejecutables utilizan el mismo icono oficial.^&echo Mantener los dos EXE y la carpeta datos juntos.) > dist\INSTRUCCIONES.txt

echo.
echo ================================================
echo COMPILACION COMPLETADA
echo Archivos generados en: %CD%\dist
echo ================================================
echo.
echo IMPORTANTE: Mantenga ADMIN.exe, FICHAJE.exe y datos\ en la misma carpeta.
pause
exit /b 0

:error
echo.
echo ERROR DURANTE LA COMPILACION. Revise el mensaje anterior.
pause
exit /b 1
