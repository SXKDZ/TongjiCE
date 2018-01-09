import sys
from cx_Freeze import setup, Executable

# GUI applications require a different base on Windows (the default is for a
# console application).
base = None
if sys.platform == 'win32':
    base = 'Win32GUI'

setup(
    name = 'TongjiCE',
    version = '1.2',
    description = 'Automatically course selection for Tongji University',
    options = {
        'build_exe': {
            'packages': ['encodings', 'asyncio', 'idna'],
            'optimize': 2,
            'include_files': ['phantomjs']
        },
    },
    executables = [
        Executable('main.py', base=base, targetName='TongjiCE')
    ]
)
