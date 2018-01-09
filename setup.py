import sys
from cx_Freeze import setup, Executable

setup(
    name = 'TongjiCE',
    version = '1.2',
    description = 'Automatically course selection for Tongji University',
    options = {
        'build_exe': {
            'packages': ['encodings', 'asyncio', '_jsonnet', 'idna'],
            'optimize': 2
        },
    },
    executables = [
        Executable('main.py', base=None, targetName='TongjiCE')
    ]
)
