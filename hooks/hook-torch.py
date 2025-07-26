from PyInstaller.utils.hooks import collect_all, collect_data_files

def hook(hook_api):
    # Main torch dependencies
    datas, binaries, hiddenimports = collect_all('torch')
    
    # Add Silero-specific dependencies
    datas += collect_data_files('sentencepiece')
    datas += collect_data_files('omegaconf')
    
    hook_api.add_datas(datas)
    hook_api.add_binaries(binaries)
    hook_api.add_imports(*hiddenimports + [
        'torch._C._distributed_c10d',
        'numpy.random.common'
    ])
