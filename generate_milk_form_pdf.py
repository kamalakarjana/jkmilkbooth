from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import mm


def create_milk_inventory_pdf(path="milk_inventory_form.pdf"):
    width, height = A4
    c = canvas.Canvas(path, pagesize=A4)
    margin = 12 * mm

    # Beautiful header band
    header_h = 26 * mm
    c.setFillColorRGB(0.07, 0.4, 0.6)  # deep teal
    c.rect(0, height - header_h, width, header_h, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(width / 2, height - header_h / 2 + 6, "PAID MILK ONLY (PMO)")
    c.setFont("Helvetica", 10)
    c.drawCentredString(width / 2, height - header_h / 2 - 8, "DAILY MILK INVENTORY")

    # Top detail fields with subtle borders
    field_w = (width - margin * 2 - 10 * mm) / 3
    field_h = 14 * mm
    top_y = height - header_h - 6 * mm
    labels = ["(A) SCHOOL", "(B) MONTH/YEAR", "(C) PREPARED BY"]
    c.setFont("Helvetica-Bold", 8)
    for i, label in enumerate(labels):
        x = margin + i * (field_w + 5 * mm)
        c.setFillColorRGB(0.95, 0.98, 1)
        c.rect(x, top_y - field_h, field_w, field_h, stroke=0, fill=1)
        c.setFillColor(colors.black)
        c.rect(x, top_y - field_h, field_w, field_h, stroke=1, fill=0)
        c.drawString(x + 4 * mm, top_y - 5 * mm, label)
        # underline for user-filled value
        c.line(x + 4 * mm, top_y - field_h + 4 * mm, x + field_w - 4 * mm, top_y - field_h + 4 * mm)

    # Table area: compute available space and make table fit one page
    table_top = top_y - field_h - 6 * mm
    table_left = margin
    table_right = width - margin
    table_bottom = 38 * mm  # leave room for notes and footer
    table_height = table_top - table_bottom

    # columns: define relative widths and normalize to available width
    rel_widths = [0.055, 0.185, 0.16, 0.16, 0.14, 0.12, 0.06, 0.06, 0.04]
    table_width = table_right - table_left
    col_widths = [table_width * r for r in rel_widths]

    rows = 31
    row_h = table_height / (rows + 1.5)  # reserve extra for header and totals
    if row_h < 6 * mm:
        row_h = 6 * mm

    # Header row
    headers = ["No.", "Beginning Inventory", "Amount Delivered", "Total Milk Available", "Ending Inventory", "Total Milk Used", "Misc.", "# Students", "Income"]
    c.setFont("Helvetica-Bold", 8)
    x = table_left
    header_y = table_top
    c.setFillColorRGB(0.88, 0.94, 0.98)  # light blue header
    c.rect(table_left, header_y - row_h, table_width, row_h, stroke=0, fill=1)
    c.setFillColor(colors.black)
    for w, h in zip(col_widths, headers):
        c.rect(x, header_y - row_h, w, row_h, stroke=1, fill=0)
        c.drawCentredString(x + w / 2, header_y - row_h / 2 - 3, h)
        x += w

    # Rows with subtle zebra striping
    y = header_y - row_h
    c.setFont("Helvetica", 7.5)
    for r in range(1, rows + 1):
        y -= row_h
        x = table_left
        if r % 2 == 0:
            c.setFillColorRGB(0.98, 0.99, 1)
            c.rect(table_left, y, table_width, row_h, stroke=0, fill=1)
            c.setFillColor(colors.black)
        for w in col_widths:
            c.rect(x, y, w, row_h, stroke=1, fill=0)
            x += w
        # row number
        c.drawCentredString(table_left + col_widths[0] / 2, y + row_h / 2 - 3, str(r))

    # Totals row
    y -= row_h
    x = table_left
    c.setFillColorRGB(0.95, 0.97, 0.99)
    c.rect(table_left, y, table_width, row_h, stroke=0, fill=1)
    c.setFillColor(colors.black)
    for w in col_widths:
        c.rect(x, y, w, row_h, stroke=1, fill=0)
        x += w
    c.setFont("Helvetica-Bold", 8)
    c.drawString(table_left + 3 * mm, y + row_h / 2 - 3, "TOTALS")

    # Bottom notes and signature lines
    notes_y = y - 6 * mm
    notes_h = 28 * mm
    notes_w = (table_width - 10 * mm) / 3
    note_texts = [
        "Report the Total in SNEARS",
        "Ending inventory on last service day (carry over to next month in SNEARS)",
        "Report the Total in SNEARS"
    ]
    c.setFont("Helvetica", 7)
    for i, nt in enumerate(note_texts):
        nx = table_left + i * (notes_w + 5 * mm)
        c.rect(nx, notes_y - notes_h, notes_w, notes_h, stroke=1, fill=0)
        c.drawString(nx + 3 * mm, notes_y - 6 * mm, nt)

    # Footer small print
    c.setFont("Helvetica-Oblique", 7)
    c.setFillColorRGB(0.2, 0.2, 0.2)
    c.drawCentredString(width / 2, 10 * mm, "Form B6 - Daily Milk Inventory — Generated")

    c.showPage()
    c.save()


if __name__ == "__main__":
    create_milk_inventory_pdf()
    print("Generated milk_inventory_form.pdf")
