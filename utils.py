"""
Utility Functions
"""
from datetime import datetime
from calendar import monthrange
import pytz

IST = pytz.timezone('Asia/Kolkata')

# ================== TIMEZONE UTILITIES ==================
def get_today_ist():
    """Get today's date in YYYY-MM-DD format (IST)"""
    return datetime.now(IST).strftime('%Y-%m-%d')

def get_ist_datetime():
    """Get current datetime in IST"""
    return datetime.now(IST)

def get_last_day_of_month(year, month):
    """Get the last day of a month"""
    return monthrange(year, month)[1]

# ================== RATE CHARTS ==================
BUFFALO_RATE_CHART = {      
    5.0: 40.0, 5.1: 40.8, 5.2: 41.6, 5.3: 42.4, 5.4: 43.2,
    5.5: 44.0, 5.6: 44.8, 5.7: 45.6, 5.8: 46.4, 5.9: 47.2,
    6.0: 48.0, 6.1: 48.8, 6.2: 49.6, 6.3: 50.0, 6.4: 51.0,
    6.5: 52.0, 6.6: 52.8, 6.7: 53.6, 6.8: 54.4, 6.9: 55.2,
    7.0: 56.0, 7.1: 56.8, 7.2: 57.6, 7.3: 58.4, 7.4: 59.2,
    7.5: 60.0, 7.6: 60.8, 7.7: 61.6, 7.8: 62.4, 7.9: 63.2,
    8.0: 64.0, 8.1: 64.8, 8.2: 65.6, 8.3: 66.4, 8.4: 67.2,
    8.5: 68.0, 8.6: 68.8, 8.7: 69.6, 8.8: 70.4, 8.9: 71.2,
    9.0: 72.0, 9.1: 72.8, 9.2: 73.6, 9.3: 74.4, 9.4: 75.2,
    9.5: 76.0, 9.6: 76.8, 9.7: 77.6, 9.8: 78.4, 9.9: 79.2,
    10.0: 80.0
}

COW_RATE_CHART = {
    3.0: 25.30, 3.1: 25.53, 3.2: 25.76, 3.3: 25.99, 3.4: 26.22,
    3.5: 26.45, 3.6: 26.68, 3.7: 26.91, 3.8: 27.14, 3.9: 27.37,
    4.0: 27.60, 4.1: 27.83, 4.2: 28.06, 4.3: 28.29, 4.4: 28.52,
    4.5: 28.75, 4.6: 28.98, 4.7: 29.21, 4.8: 29.44, 4.9: 29.67,
    5.0: 29.90, 5.1: 30.13, 5.2: 30.36, 5.3: 30.59, 5.4: 30.82,
    5.5: 31.05, 5.6: 31.28, 5.7: 31.51, 5.8: 31.74, 5.9: 31.97,
    6.0: 32.20
}

def find_rate(fat, milk_type='buffalo', transaction_date=None):
    """
    Find rate for the given fat and milk type using current charts.
    For `cow` use `COW_RATE_CHART`, otherwise use `BUFFALO_RATE_CHART`.
    """
    if fat is None:
        return None
    
    k = round(fat * 10) / 10.0
    
    # For cow milk, always use same chart
    if milk_type == 'cow':
        return COW_RATE_CHART.get(k)
    
    # For buffalo milk, always use current buffalo chart
    return BUFFALO_RATE_CHART.get(k)

# ================== PAYMENT CYCLES ==================
def calculate_payment_cycles(collections, year, month):
    """Calculate payment cycles for a given month"""
    month_str = f"{year}-{month:02d}"
    monthly_collections = [c for c in collections if c.date.startswith(month_str)]
    
    cycles = {
        'cycle_1': {
            'start': f"{year}-{month:02d}-01",
            'end': f"{year}-{month:02d}-15",
            'morning': {'liters': 0, 'amount': 0, 'count': 0},
            'evening': {'liters': 0, 'amount': 0, 'count': 0},
            'total_liters': 0,
            'total_amount': 0
        },
        'cycle_2': {
            'start': f"{year}-{month:02d}-16",
            'end': f"{year}-{month:02d}-{get_last_day_of_month(year, month):02d}",
            'morning': {'liters': 0, 'amount': 0, 'count': 0},
            'evening': {'liters': 0, 'amount': 0, 'count': 0},
            'total_liters': 0,
            'total_amount': 0
        }
    }
    
    for coll in monthly_collections:
        try:
            day = int(coll.date.split('-')[2])
            
            if 1 <= day <= 15:
                cycle = cycles['cycle_1']
            else:
                cycle = cycles['cycle_2']
            
            if coll.session == 'morning':
                cycle['morning']['liters'] += coll.liters
                cycle['morning']['amount'] += coll.amount
                cycle['morning']['count'] += 1
            else:
                cycle['evening']['liters'] += coll.liters
                cycle['evening']['amount'] += coll.amount
                cycle['evening']['count'] += 1
            
            cycle['total_liters'] += coll.liters
            cycle['total_amount'] += coll.amount
            
        except (ValueError, IndexError):
            continue
    
    return cycles

# ================== SORTING ==================
def sort_by_id(items, id_field='supplier_id'):
    """Sort by ID as numbers"""
    if not items:
        return []
    if isinstance(items[0], dict):
        return sorted(items, key=lambda x: int(x.get(id_field, 0)) if str(x.get(id_field, '0')).isdigit() else 999999)
    else:
        return sorted(items, key=lambda x: int(getattr(x, id_field)) if getattr(x, id_field).isdigit() else 999999)

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle

PDF_PALETTE = {
    'page_bg': colors.HexColor('#f5f7fb'),
    'header_bg': colors.HexColor('#1f3b6f'),
    'section_bg': colors.HexColor('#30508a'),
    'card_bg': colors.HexColor('#eef4fb'),
    'card_border': colors.HexColor('#c8d7ea'),
    'table_header': colors.HexColor('#1f3b6f'),
    'table_row_alt': colors.HexColor('#f3f7ff'),
    'grid_color': colors.HexColor('#d8e2ef'),
    'text': colors.HexColor('#1f2937'),
    'muted': colors.HexColor('#5f6e85'),
    'accent': colors.HexColor('#3b82f6'),
    'footer_bg': colors.HexColor('#e8eef9')
}


def pdf_paragraph_styles(stylesheet=None):
    if stylesheet is None:
        from reportlab.lib.styles import getSampleStyleSheet
        stylesheet = getSampleStyleSheet()

    return {
        'ReportTitle': ParagraphStyle(
            'ReportTitle',
            parent=stylesheet['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=18,
            leading=22,
            alignment=TA_CENTER,
            textColor=PDF_PALETTE['header_bg'],
            spaceAfter=6
        ),
        'ReportSubtitle': ParagraphStyle(
            'ReportSubtitle',
            parent=stylesheet['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=13,
            alignment=TA_CENTER,
            textColor=PDF_PALETTE['muted'],
            spaceAfter=12
        ),
        'MetaText': ParagraphStyle(
            'MetaText',
            parent=stylesheet['Normal'],
            fontName='Helvetica',
            fontSize=9,
            leading=12,
            alignment=TA_CENTER,
            textColor=PDF_PALETTE['muted']
        ),
        'SectionHeader': ParagraphStyle(
            'SectionHeader',
            parent=stylesheet['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=10,
            leading=12,
            alignment=TA_LEFT,
            textColor=colors.white,
            backColor=PDF_PALETTE['section_bg'],
            spaceAfter=8,
            leftIndent=4,
            rightIndent=4
        ),
        'FooterSmall': ParagraphStyle(
            'FooterSmall',
            parent=stylesheet['Normal'],
            fontName='Helvetica',
            fontSize=8,
            leading=10,
            alignment=TA_CENTER,
            textColor=PDF_PALETTE['muted']
        )
    }


def pdf_table_style(
    header_bg=None,
    header_text=None,
    row_bg1=None,
    row_bg2=None,
    grid_color=None,
    header_font_size=9,
    body_font_size=8,
    header_bold=True
):
    header_bg = header_bg or PDF_PALETTE['table_header']
    header_text = header_text or colors.white
    row_bg1 = row_bg1 or PDF_PALETTE['card_bg']
    row_bg2 = row_bg2 or colors.white
    grid_color = grid_color or PDF_PALETTE['grid_color']

    style = [
        ('BACKGROUND', (0, 0), (-1, 0), header_bg),
        ('TEXTCOLOR', (0, 0), (-1, 0), header_text),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold' if header_bold else 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, 0), header_font_size),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), row_bg1),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [row_bg1, row_bg2]),
        ('GRID', (0, 0), (-1, -1), 0.5, grid_color),
        ('BOX', (0, 0), (-1, -1), 0.75, grid_color),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5)
    ]
    return style


def add_pdf_footer(canvas, doc, palette=None):
    if palette is None:
        palette = PDF_PALETTE

    canvas.saveState()
    width, height = doc.pagesize
    y = doc.bottomMargin - 12
    if y < 10:
        y = 10

    canvas.setStrokeColor(palette['grid_color'])
    canvas.setLineWidth(0.5)
    canvas.line(doc.leftMargin, y + 14, width - doc.rightMargin, y + 14)

    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(palette['muted'])
    timestamp = get_ist_datetime().strftime('%Y-%m-%d %I:%M %p IST')
    canvas.drawString(doc.leftMargin, y, f"Generated on: {timestamp}  •  www.rrmilkbooth.com")
    canvas.drawRightString(width - doc.rightMargin, y, f"Page {canvas.getPageNumber()}")
    canvas.restoreState()
