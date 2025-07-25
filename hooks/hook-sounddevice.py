from PyInstaller.utils.hooks import collect_all

def hook(hook_api):
    datas, binaries, hiddenimports = collect_all('sounddevice')
    hook_api.add_datas(datas)
    hook_api.add_binaries(binaries)
    hook_api.add_imports(*hiddenimports + [
        'sounddevice._sounddevice'
    ])
