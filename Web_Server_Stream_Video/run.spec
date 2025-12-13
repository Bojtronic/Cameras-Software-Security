from PyInstaller.utils.hooks import collect_submodules, collect_data_files
import os

project_dir = os.path.abspath(".")

hiddenimports = []
hiddenimports += collect_submodules("fastapi")
hiddenimports += collect_submodules("starlette")
hiddenimports += collect_submodules("uvicorn")
hiddenimports += collect_submodules("pydantic")
hiddenimports += collect_submodules("mediapipe")

hiddenimports += collect_submodules("onvif")
hiddenimports += collect_submodules("zeep")
hiddenimports += collect_submodules("zeep.transports")
hiddenimports += collect_submodules("zeep.wsse")
hiddenimports += collect_submodules("zeep.xsd")

datas = [
    (os.path.join(project_dir, "app"), "app"),
    (os.path.join(project_dir, "core"), "core"),
    (os.path.join(project_dir, "services"), "services"),
    (os.path.join(project_dir, "detectors"), "detectors"),

    (os.path.join(project_dir, "services", "wsdl"), "services/wsdl"),
]

datas += collect_data_files("mediapipe")

a = Analysis(
    ['run_ui.py'],
    pathex=[project_dir],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Monitoreo_IA',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Cambia a False si no quieres consola
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='logo.ico',
)
