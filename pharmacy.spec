# -*- mode: python ; coding: utf-8 -*-
# pharmacy.spec - PyInstaller 6.x compatible
# Run: python -m PyInstaller pharmacy.spec --noconfirm --clean

import os, sys

block_cipher = None
BASE = os.path.dirname(os.path.abspath(SPEC))

icon_path = os.path.join(BASE, 'assets', 'icon.ico')

hidden_imports = [
    # tkinter
    'tkinter', 'tkinter.ttk', 'tkinter.font',
    'tkinter.colorchooser', 'tkinter.filedialog', 'tkinter.messagebox',
    # screens
    'screens', 'screens.login', 'screens.dashboard', 'screens.pos',
    'screens.cashier', 'screens.medicines', 'screens.sales',
    'screens.purchases', 'screens.inventory', 'screens.customers',
    'screens.suppliers', 'screens.returns', 'screens.treasury',
    'screens.reports', 'screens.users', 'screens.audit_logs',
    'screens.settings', 'screens.theme_designer', 'screens.db_setup',
    # models
    'models', 'models.medicine', 'models.sale', 'models.purchase',
    'models.returns', 'models.customer', 'models.supplier',
    'models.user', 'models.treasury',
    # utils
    'utils', 'utils.auth', 'utils.helpers', 'utils.printing',
    'utils.audit', 'utils.theme_manager',
    # database
    'database', 'database.connection', 'database.schema',
    'database.db_config',
    # Arabic PDF
    'arabic_reshaper', 'bidi', 'bidi.algorithm',
    # PDF
    'fpdf', 'fpdf.enums', 'fpdf.fonts',
    # image
    'PIL', 'PIL.Image', 'PIL.ImageTk',
    # Excel
    'openpyxl',
    # MySQL (optional)
    'mysql', 'mysql.connector', 'mysql.connector.pooling',
    # stdlib
    'sqlite3', 'json', 'pathlib', 'shutil', 'hashlib',
    'bcrypt', 'cryptography', 'cryptography.fernet',
    'utils.crypto',
    'datetime', 'copy', 're', 'threading', 'contextlib',
]

added_datas = [
    (os.path.join(BASE, 'assets'),   'assets'),
    (os.path.join(BASE, 'database'), 'database'),
    (os.path.join(BASE, 'screens'),  'screens'),
    (os.path.join(BASE, 'models'),   'models'),
    (os.path.join(BASE, 'utils'),    'utils'),
    (os.path.join(BASE, 'hooks'),    'hooks'),
]

a = Analysis(
    [os.path.join(BASE, 'main.py')],
    pathex=[BASE],
    binaries=[],
    datas=added_datas,
    hiddenimports=hidden_imports,
    hookspath=[os.path.join(BASE, 'hooks')],
    hooksconfig={},
    runtime_hooks=[os.path.join(BASE, 'hooks', 'pyi_rth_pharmacy.py')],
    excludes=[
        'matplotlib', 'numpy', 'scipy', 'pandas',
        'IPython', 'jupyter', 'pytest',
        'PyQt5', 'PyQt6', 'PySide2', 'PySide6', 'wx',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='pharmacy',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path if os.path.exists(icon_path) else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='pharmacy',
)
