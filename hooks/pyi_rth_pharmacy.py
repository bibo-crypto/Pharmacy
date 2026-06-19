"""
Runtime hook for PyInstaller — يُنفَّذ قبل main.py
يضيف _MEIPASS لـ sys.path حتى تعمل imports طبيعياً
"""
import sys
import os

if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    meipass = sys._MEIPASS
    exe_dir = os.path.dirname(sys.executable)
    
    # أضف مسارات المشروع للـ path
    for p in [meipass, exe_dir]:
        if p not in sys.path:
            sys.path.insert(0, p)
    
    # عيّن مجلد البيانات القابل للكتابة
    os.environ.setdefault('PHARMACY_DATA_DIR', exe_dir)
    
    # تأكد من وجود مجلد assets في مجلد الـ EXE
    assets_src = os.path.join(meipass, 'assets')
    assets_dst = os.path.join(exe_dir, 'assets')
    if os.path.isdir(assets_src) and not os.path.isdir(assets_dst):
        import shutil
        try:
            shutil.copytree(assets_src, assets_dst)
        except Exception:
            pass
