from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import mm


def create_milk_inventory_pdf(path="milk_inventory_form.pdf"):
    width, height = A4
    c = canvas.Canvas(path, pagesize=A4)
    margin = 12 * mm

    # Header
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2, height - margin, "PAID MILK ONLY (PMO)")
    c.setFont("Helvetica", 11)
    c.drawCentredString(width / 2, height - margin - 16, "DAILY MILK INVENTORY")

    # Top detail boxes: (A) School, (B) Month/Year, (C) Prepared by
    box_h = 20 * mm
    box_w = (width - margin * 2 - 10 * mm) / 3
    top_y = height - margin - 28
    labels = ["(A) SCHOOL", "(B) MONTH/YEAR", "(C) PREPARED BY"]
    c.setFont("Helvetica-Bold", 8)
    for i, label in enumerate(labels):
        x = margin + i * (box_w + 5 * mm)
        c.rect(x, top_y - box_h, box_w, box_h, stroke=1, fill=0)
        c.drawString(x + 4 * mm, top_y - 6 * mm, label)

    # Table area
    table_top = top_y - box_h - 8 * mm
    table_left = margin
    table_right = width - margin
    table_width = table_right - table_left

    # Column widths (approximation based on the sample image)
    col_widths = [12 * mm, 24 * mm, 28 * mm, 30 * mm, 28 * mm, 22 * mm, 20 * mm, 28 * mm, 28 * mm]
    # first column is the row number
    total_col_width = sum(col_widths)
    # If widths don't match available width, scale them
    scale = table_width / total_col_width
    col_widths = [w * scale for w in col_widths]

    rows = 31
    row_h = 8 * mm

    # Draw header row labels
    headers = ["No.", "Beginning Inventory", "Amount Delivered", "Total Milk Available", "Ending Inventory", "Total Milk Used", "Misc.", "No. Plants Served to Students", "Income Received/Temp"]
    c.setFont("Helvetica-Bold", 7.5)
    x = table_left
    for w, h in zip(col_widths, headers):
        c.rect(x, table_top - row_h, w, row_h, stroke=1, fill=0)
        c.drawCentredString(x + w / 2, table_top - row_h + 3 * mm, h)
        x += w

    # Draw rows for days 1..31
    c.setFont("Helvetica", 8)
    y = table_top - row_h
    for r in range(1, rows + 1):
        y -= row_h
        x = table_left
        for w in col_widths:
            c.rect(x, y, w, row_h, stroke=1, fill=0)
            x += w
        # draw row number in first cell
        c.drawCentredString(table_left + col_widths[0] / 2, y + row_h / 2 - 3, str(r))

    # Totals row
    y -= row_h
    x = table_left
    for w in col_widths:
        c.rect(x, y, w, row_h, stroke=1, fill=0)
        x += w
    c.setFont("Helvetica-Bold", 8)
    c.drawString(table_left + 2 * mm, y + row_h / 2 - 3, "TOTALS")

    # Bottom notes boxes (approximate)
    notes_h = 18 * mm
    notes_w = (table_width - 2 * 5 * mm) / 3
    notes_y = y - notes_h - 6 * mm
    notes_labels = ["Report the Total in SNEARS", "Ending Inventory on last service day for carry over to next month in SNEARS", "Report the Total in SNEARS"]
    c.setFont("Helvetica", 7)
    for i, nl in enumerate(notes_labels):
        nx = table_left + i * (notes_w + 5 * mm)
        c.rect(nx, notes_y, notes_w, notes_h, stroke=1, fill=0)
        c.drawString(nx + 3 * mm, notes_y + notes_h - 6 * mm, nl)

    c.showPage()
    c.save()


if __name__ == "__main__":
    create_milk_inventory_pdf()
    print("Generated milk_inventory_form.pdf")
