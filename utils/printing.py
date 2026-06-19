"""
utils/printing.py
-----------------
توليد فواتير PDF بدعم كامل للعربية.
يستخدم خط Amiri (مضمّن في مجلد assets/) مع arabic_reshaper + python-bidi.
"""
import os
import sys
from datetime import datetime

from fpdf import FPDF
from fpdf.enums import XPos, YPos
from utils.helpers import get_setting


# ─────────────────────────────────────────
# مسار خط Amiri
# ─────────────────────────────────────────
def _amiri_font_path() -> str | None:
    """يبحث عن خط Amiri في assets/ أو خطوط النظام."""
    import sys
    # PyInstaller frozen: ملفات البيانات في sys._MEIPASS
    if getattr(sys, 'frozen', False):
        meipass = sys._MEIPASS
        exe_dir = os.path.dirname(sys.executable)
        bases = [meipass, exe_dir]
    else:
        bases = [os.path.dirname(os.path.dirname(os.path.abspath(__file__)))]
    candidates = []
    for base in bases:
        candidates += [
            os.path.join(base, "assets", "Amiri-Regular.ttf"),
            os.path.join(base, "assets", "arabic_font.ttf"),
        ]
    if sys.platform == "win32":
        win_fonts = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts")
        candidates += [
            os.path.join(win_fonts, "Amiri-Regular.ttf"),
            os.path.join(win_fonts, "arial.ttf"),     # fallback
            os.path.join(win_fonts, "Tahoma.ttf"),
        ]
    else:
        candidates += [
            "/usr/share/fonts/truetype/amiri/Amiri-Regular.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
    for p in candidates:
        if p and os.path.isfile(p):
            return p
    return None


# ─────────────────────────────────────────
# معالجة النص العربي
# ─────────────────────────────────────────
def _contains_arabic(text: str) -> bool:
    return any("\u0600" <= ch <= "\u06FF" for ch in text)


def _reshape(text) -> str:
    """يُشكّل النص العربي ويعكسه لعرض صحيح في PDF."""
    text = str(text) if text is not None else ""
    if not text or not _contains_arabic(text):
        return text
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        return get_display(arabic_reshaper.reshape(text))
    except Exception:
        return text


def _r(text) -> str:
    """اختصار لـ _reshape."""
    return _reshape(text)


# ─────────────────────────────────────────
# مجلد الفواتير
# ─────────────────────────────────────────
def _receipt_folder() -> str:
    import sys
    if getattr(sys, 'frozen', False):
        root = os.environ.get("PHARMACY_DATA_DIR",
                              os.path.dirname(sys.executable))
    else:
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(root, "receipts")
    os.makedirs(path, exist_ok=True)
    return path


def _build_filename(invoice_number: str) -> str:
    cleaned = "".join(ch for ch in str(invoice_number) if ch not in '\\/: *?"<>|')
    if not cleaned:
        cleaned = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"فاتورة-{cleaned}.pdf"


# ─────────────────────────────────────────
# PDF Class
# ─────────────────────────────────────────
class ReceiptPDF(FPDF):
    """فاتورة بعرض 80mm — مناسبة لطابعات الإيصالات الحرارية."""

    def __init__(self, font_path: str | None = None):
        super().__init__(unit="mm", format=(80, 297))
        self.set_margins(4, 4, 4)
        self.set_auto_page_break(auto=True, margin=5)
        self._main_font = "Helvetica"
        if font_path:
            try:
                self.add_font("Amiri", style="", fname=font_path)
                self._main_font = "Amiri"
            except Exception:
                pass

    # ── اختصارات داخلية ──
    def _font(self, size: float, bold: bool = False):
        style = "B" if bold and self._main_font != "Amiri" else ""
        self.set_font(self._main_font, style=style, size=size)

    def _hline(self):
        self.line(4, self.get_y(), 76, self.get_y())
        self.ln(1)

    def _row2(self, left: str, right: str, h: float = 5.5, size: float = 8):
        """سطر من عمودين: يسار وراست."""
        self._font(size)
        # عرض الورقة - الهوامش = 72mm، نقسمها نصفين
        self.cell(36, h, left,  align="L",
                  new_x=XPos.RIGHT, new_y=YPos.TOP)
        self.cell(36, h, right, align="R",
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def _rtl_line(self, text: str, h: float = 5.5, size: float = 8, bold: bool = False):
        """سطر عربي كامل محاذاة يمين."""
        self._font(size, bold)
        self.cell(72, h, _r(text), align="R",
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def _center_line(self, text: str, h: float = 6, size: float = 9):
        self._font(size)
        self.cell(72, h, _r(text), align="C",
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def _amount_row(self, label: str, amount: str, size: float = 8, bold: bool = False):
        """صف مبلغ: الليبل يميناً، الرقم شمالاً (عكس لأن PDF RTL)."""
        self._font(size, bold)
        self.cell(36, 5.5, amount, align="L",
                  new_x=XPos.RIGHT, new_y=YPos.TOP)
        self.cell(36, 5.5, _r(label), align="R",
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)


# ─────────────────────────────────────────
# الدالة الرئيسية
# ─────────────────────────────────────────
def generate_receipt_pdf(sale: dict, items: list, save_path: str = None) -> str:
    font_path = _amiri_font_path()
    pdf = ReceiptPDF(font_path=font_path)
    pdf.add_page()

    pharmacy_name    = get_setting("pharmacy_name",    "صيدلية الأمل")
    pharmacy_address = get_setting("pharmacy_address", "")
    pharmacy_phone   = get_setting("pharmacy_phone",   "")
    footer_msg       = get_setting("receipt_footer",   "شكراً لزيارتكم - نتمنى لكم الشفاء العاجل")
    currency         = get_setting("currency",         "ج.م")

    # ── رأس الفاتورة ──
    pdf._center_line(pharmacy_name, h=8, size=13)
    if pharmacy_address:
        pdf._center_line(pharmacy_address, h=5, size=8)
    if pharmacy_phone:
        pdf._center_line(f"هاتف: {pharmacy_phone}", h=5, size=8)
    pdf._hline()

    # ── بيانات الفاتورة ──
    invoice_num = sale.get("invoice_number", "")
    sale_date   = sale.get("sale_date", "")[:16]
    cashier     = sale.get("cashier_name", "")
    customer    = sale.get("customer_name") or "عميل نقدي"

    pdf._row2(_r(f"فاتورة: {invoice_num}"), _r(f"التاريخ: {sale_date}"))
    pdf._row2(_r(f"الكاشير: {cashier}"),    _r(f"العميل: {customer}"))
    pdf._hline()

    # ── رأس جدول الأصناف ──
    pdf._font(7.5, bold=True)
    pdf.cell(30, 5.5, _r("الدواء"),    align="R",
             new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.cell(10, 5.5, _r("الكمية"),   align="C",
             new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.cell(16, 5.5, _r("السعر"),    align="C",
             new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.cell(16, 5.5, _r("الإجمالي"), align="C",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf._hline()

    # ── الأصناف ──
    pdf._font(7.5)
    for item in items:
        name = str(item.get("medicine_name", ""))
        if len(name) > 22:
            name = name[:22]
        pdf.cell(30, 5.5, _r(name), align="R",
                 new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.cell(10, 5.5, str(item.get("quantity", 0)), align="C",
                 new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.cell(16, 5.5, f"{item.get('unit_price', 0):.2f}", align="C",
                 new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.cell(16, 5.5, f"{item.get('total', 0):.2f}", align="C",
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf._hline()
    pdf.ln(1)

    # ── المبالغ ──
    pdf._amount_row("المجموع الفرعي:", f"{sale.get('subtotal', 0):.2f} {currency}")
    if sale.get("discount", 0) > 0:
        pdf._amount_row("الخصم:", f"-{sale.get('discount', 0):.2f} {currency}")
    if sale.get("tax", 0) > 0:
        pdf._amount_row("الضريبة:", f"{sale.get('tax', 0):.2f} {currency}")

    pdf._font(10, bold=True)
    pdf.cell(36, 6.5,
             f"{sale.get('total', 0):.2f} {currency}", align="L",
             new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.cell(36, 6.5,
             _r("الإجمالي:"), align="R",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf._amount_row("المدفوع:",       f"{sale.get('paid_amount', 0):.2f} {currency}")
    pdf._amount_row("الباقي:",        f"{sale.get('change_amount', 0):.2f} {currency}")
    pdf._amount_row("طريقة الدفع:",   str(sale.get("payment_method", "cash")))

    pdf._hline()
    pdf.ln(1)

    # ── ذيل الفاتورة ──
    pdf._font(7.5)
    # multi_cell بدعم RTL
    for line in footer_msg.split("\n"):
        if line.strip():
            pdf.multi_cell(72, 5, _r(line), align="C",
                           new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(4)

    # ── حفظ الملف ──
    if save_path is None:
        folder = _receipt_folder()
        filename = _build_filename(invoice_num)
        save_path = os.path.join(folder, filename)
        if os.path.exists(save_path):
            base, ext = os.path.splitext(save_path)
            save_path = f"{base}-{datetime.now().strftime('%H%M%S')}{ext}"

    pdf.output(save_path)
    return save_path


def print_receipt(sale: dict, items: list) -> str:
    path = generate_receipt_pdf(sale, items)
    try:
        if sys.platform == "win32":
            import ctypes
            ctypes.windll.shell32.ShellExecuteW(None, "print", path, None, None, 0)
        else:
            import subprocess
            subprocess.run(["lp", path], check=True)
    except Exception as e:
        print(f"Print error: {e}")
    return path
