from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs
from PyInstaller.utils.hooks.qt import pyside6_library_info

def hook(hook_api):
    # 1. Collect core Qt binaries
    binaries = collect_dynamic_libs('PySide6')
    
    # 2. Add essential Qt plugins (adjust as needed)
    required_plugins = [
        'platforms',
        'styles',
        'imageformats',
        'tls'  # Only if using HTTPS
    ]
    
    for plugin in required_plugins:
        binaries += pyside6_library_info.collect_qt_plugins(plugin)
    
    # 3. Add hidden imports
    hiddenimports = [
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        # Add these if used:
        # 'PySide6.QtNetwork',
        # 'PySide6.QtMultimedia'
    ]
    
    # 4. Ignore deploy_lib warning
    excludedimports = ['PySide6.scripts.deploy_lib']
    
    hook_api.add_binaries(binaries)
    hook_api.add_imports(*hiddenimports)
    hook_api.add_excludedimports(excludedimports)
