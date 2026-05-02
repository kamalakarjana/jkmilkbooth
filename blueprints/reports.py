"""
Reports & Dashboard Blueprint
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
from flask_login import login_required, current_user
from functools import wraps
from sqlalchemy import or_, func
import io
import csv
from models import db, Supplier, Customer, Collection, Sale, Withdrawal
from utils import get_today_ist, sort_by_id

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')

def role_required(*roles):
    """Role-based access control decorator"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            if current_user.role not in roles and current_user.role != 'admin':
                flash('Access denied. Insufficient permissions.', 'danger')
                return redirect(url_for('dashboard.index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@reports_bp.route('/daily')
@login_required
def daily():
    """Daily collection report"""
    req_date = request.args.get('date') or get_today_ist()
    session_filter = request.args.get('session', 'all')
    
    # FIXED: Use outer join to show all suppliers with their collections
    query = db.session.query(
        Supplier.supplier_id,
        Supplier.name,
        Collection.date,
        Collection.session,
        Collection.liters,
        Collection.fat,
        Collection.milk_type,
        Collection.rate_per_liter,
        Collection.amount,
        Collection.id
    ).outerjoin(Collection, (Supplier.id == Collection.supplier_id) & (Collection.date == req_date))
    
    if session_filter != 'all':
        query = query.filter(or_(Collection.session == session_filter, Collection.session == None))
    
    results = query.order_by(Supplier.supplier_id).all()
    
    # Process results
    rows = []
    for r in results:
        if r.date:
            rows.append({
                'supplier': {'supplier_id': r.supplier_id, 'name': r.name},
                'date': r.date,
                'session': r.session,
                'liters': r.liters,
                'fat': r.fat,
                'milk_type': r.milk_type,
                'rate_per_liter': r.rate_per_liter,
                'amount': r.amount,
                'id': r.id
            })
        else:
            rows.append({
                'supplier': {'supplier_id': r.supplier_id, 'name': r.name},
                'date': req_date,
                'session': '',
                'liters': 0,
                'fat': 0,
                'milk_type': '',
                'rate_per_liter': 0,
                'amount': 0,
                'id': None
            })
    
    # Calculate statistics
    actual_collections = Collection.query.filter_by(date=req_date).all()
    total_liters = sum(r.liters for r in actual_collections)
    total_amount = sum(r.amount for r in actual_collections)
    avg_fat = sum(r.fat for r in actual_collections) / len(actual_collections) if actual_collections else 0
    
    return render_template('reports/daily.html', 
                         rows=rows, 
                         date=req_date,
                         session_filter=session_filter,
                         total_liters=total_liters,
                         total_amount=total_amount,
                         avg_fat=avg_fat)

@reports_bp.route('/daily_sales')
@login_required
def daily_sales():
    """Daily sales report"""
    req_date = request.args.get('date') or get_today_ist()
    session_filter = request.args.get('session', 'all')
    
    query = Sale.query.filter_by(date=req_date)
    
    if session_filter != 'all':
        query = query.filter_by(session=session_filter)
    
    rows = query.order_by(Sale.session, Sale.customer_id).all()
    
    # Calculate statistics
    total_liters = sum(r.liters for r in rows)
    total_amount = sum(r.amount for r in rows)
    avg_fat = sum(r.fat for r in rows) / len(rows) if rows else 0
    
    return render_template('reports/daily_sales.html', 
                         rows=rows, 
                         date=req_date,
                         session_filter=session_filter,
                         total_liters=total_liters,
                         total_amount=total_amount,
                         avg_fat=avg_fat)

@reports_bp.route('/withdrawals')
@login_required
@role_required('admin', 'employee')
def withdrawals():
    """View all withdrawals"""
    today = get_today_ist()
    
    # Get all withdrawals, ordered by date
    all_withdrawals = Withdrawal.query.order_by(Withdrawal.date.desc()).limit(200).all()
    
    # Calculate totals by supplier
    suppliers_with_balance = {}
    for supplier in Supplier.query.all():
        cols = Collection.query.filter_by(supplier_id=supplier.id).all()
        wds = Withdrawal.query.filter_by(supplier_id=supplier.id).all()
        
        total_amount = sum(c.amount for c in cols)
        total_withdrawn = sum(w.amount for w in wds)
        balance = total_amount - total_withdrawn
        
        suppliers_with_balance[supplier.supplier_id] = {
            'name': supplier.name,
            'total_collections': total_amount,
            'total_withdrawn': total_withdrawn,
            'balance': balance
        }
    
    total_collections = sum(c.amount for c in Collection.query.all())
    total_withdrawn = sum(w.amount for w in Withdrawal.query.all())
    overall_balance = total_collections - total_withdrawn
    
    return render_template('reports/withdrawals.html',
                         all_withdrawals=all_withdrawals,
                         suppliers_with_balance=suppliers_with_balance,
                         total_collections=total_collections,
                         total_withdrawn=total_withdrawn,
                         overall_balance=overall_balance)

@reports_bp.route('/monthly')
@login_required
def monthly():
    """Monthly summary report"""
    from sqlalchemy import func
    from datetime import datetime
    
    selected_month = request.args.get('month') or get_today_ist()[:7]
    like = selected_month + '%'
    
    # FIXED: Use outer join to show ALL suppliers even without collections
    supplier_results = db.session.query(
        Supplier.supplier_id, 
        Supplier.name, 
        Supplier.mobile,
        func.coalesce(func.sum(Collection.liters), 0).label('total_liters'),
        func.coalesce(func.sum(Collection.amount), 0).label('total_amount')
    ).outerjoin(Collection, (Supplier.id == Collection.supplier_id) & (Collection.date.like(like)))\
     .group_by(Supplier.id).all()
    
    # Withdrawals
    wrows = db.session.query(
        Supplier.supplier_id, func.coalesce(func.sum(Withdrawal.amount), 0).label('withdrawn')
    ).outerjoin(Withdrawal, (Supplier.id == Withdrawal.supplier_id) & (Withdrawal.date.like(like)))\
     .group_by(Supplier.id).all()
    
    withdraw_map = {r.supplier_id: r.withdrawn for r in wrows}
    
    supplier_data = []
    for r in supplier_results:
        withdrawn = withdraw_map.get(r.supplier_id, 0) or 0
        balance = (r.total_amount or 0) - withdrawn
        supplier_data.append({
            "supplier_id": r.supplier_id, 
            "name": r.name, 
            "mobile": r.mobile,
            "total_liters": float(r.total_liters or 0), 
            "total_amount": int(r.total_amount or 0),
            "withdrawn": int(withdrawn), 
            "balance": int(balance)
        })
    
    supplier_data = sort_by_id(supplier_data, 'supplier_id')
    
    # Customer sales
    customer_results = db.session.query(
        Customer.cust_id, Customer.name, Customer.mobile,
        func.sum(Sale.liters).label('total_liters'),
        func.sum(Sale.amount).label('total_amount')
    ).outerjoin(Sale, (Customer.id == Sale.customer_id) & (Sale.date.like(like)))\
     .group_by(Customer.id).all()
    
    customer_data = []
    for r in customer_results:
        customer_data.append({
            "cust_id": r.cust_id, 
            "name": r.name, 
            "mobile": r.mobile,
            "total_liters": float(r.total_liters or 0), 
            "total_amount": int(r.total_amount or 0)
        })
    
    customer_data = sort_by_id(customer_data, 'cust_id')
    
    # Calculate totals
    monthly_total_liters = sum(d['total_liters'] for d in supplier_data)
    monthly_total_amount = sum(d['total_amount'] for d in supplier_data)
    monthly_total_withdrawn = sum(d['withdrawn'] for d in supplier_data)
    monthly_total_sales = sum(d['total_amount'] for d in customer_data)
    
    return render_template('reports/monthly.html', 
                         month=selected_month,
                         supplier_data=supplier_data,
                         customer_data=customer_data,
                         monthly_total_liters=monthly_total_liters,
                         monthly_total_amount=monthly_total_amount,
                         monthly_total_withdrawn=monthly_total_withdrawn,
                         monthly_total_sales=monthly_total_sales)

# ================== EXPORT ROUTES ==================

@reports_bp.route('/daily/export/csv')
@login_required
def export_daily_csv():
    """Export daily collections to CSV"""
    req_date = request.args.get('date') or get_today_ist()
    session_filter = request.args.get('session', 'all')
    
    # Get all collections for the date
    query = Collection.query.filter_by(date=req_date)
    if session_filter != 'all':
        query = query.filter_by(session=session_filter)
    
    collections = query.order_by(Collection.supplier_id).all()
    
    if not collections:
        flash(f'No data found for {req_date}', 'warning')
        return redirect(url_for('reports.daily', date=req_date))
    
    # Create CSV
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(['Date', 'Supplier ID', 'Name', 'Session', 'Milk Type', 'Liters', 'Fat %', 'Rate/L', 'Amount (₹)'])
    
    for c in collections:
        writer.writerow([
            c.date, c.supplier.supplier_id, c.supplier.name, c.session, 
            c.milk_type, c.liters, c.fat, c.rate_per_liter, c.amount
        ])
    
    buf.seek(0)
    filename = f"daily_collections_{req_date}_{session_filter}.csv"
    return send_file(
        io.BytesIO(buf.getvalue().encode('utf-8-sig')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename
    )

@reports_bp.route('/monthly/export/csv')
@login_required
def export_monthly_csv():
    """Export monthly summary to CSV"""
    selected_month = request.args.get('month') or get_today_ist()[:7]
    like = selected_month + '%'
    
    # Get supplier data
    supplier_results = db.session.query(
        Supplier.supplier_id, Supplier.name, Supplier.mobile,
        func.coalesce(func.sum(Collection.liters), 0).label('total_liters'),
        func.coalesce(func.sum(Collection.amount), 0).label('total_amount')
    ).outerjoin(Collection, (Supplier.id == Collection.supplier_id) & (Collection.date.like(like)))\
     .group_by(Supplier.id).all()
    
    # Withdrawals
    wrows = db.session.query(
        Supplier.supplier_id, func.coalesce(func.sum(Withdrawal.amount), 0).label('withdrawn')
    ).outerjoin(Withdrawal, (Supplier.id == Withdrawal.supplier_id) & (Withdrawal.date.like(like)))\
     .group_by(Supplier.id).all()
    
    withdraw_map = {r.supplier_id: r.withdrawn for r in wrows}
    
    if not supplier_results:
        flash(f'No data found for {selected_month}', 'warning')
        return redirect(url_for('reports.monthly', month=selected_month))
    
    # Create CSV
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(['Supplier ID', 'Name', 'Mobile', 'Total Liters', 'Collection Amount (₹)', 'Withdrawn (₹)', 'Balance (₹)'])
    
    for r in supplier_results:
        withdrawn = withdraw_map.get(r.supplier_id, 0) or 0
        balance = (r.total_amount or 0) - withdrawn
        writer.writerow([
            r.supplier_id, r.name, r.mobile or '', 
            r.total_liters or 0, r.total_amount or 0, withdrawn, balance
        ])
    
    buf.seek(0)
    filename = f"monthly_summary_{selected_month}.csv"
    return send_file(
        io.BytesIO(buf.getvalue().encode('utf-8-sig')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename
    )

@reports_bp.route('/daily/export/pdf')
@login_required
def export_daily_pdf():
    """Export daily collections to PDF"""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    
    req_date = request.args.get('date') or get_today_ist()
    session_filter = request.args.get('session', 'all')
    
    # Get all collections for the date
    query = Collection.query.filter_by(date=req_date)
    if session_filter != 'all':
        query = query.filter_by(session=session_filter)
    
    collections = query.order_by(Collection.supplier_id).all()
    
    if not collections:
        flash(f'No data found for {req_date}', 'warning')
        return redirect(url_for('reports.daily', date=req_date))
    
    # Calculate totals
    total_liters = sum(c.liters for c in collections)
    total_amount = sum(c.amount for c in collections)
    avg_fat = sum(c.fat for c in collections) / len(collections) if collections else 0
    
    # Create PDF
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4)
    styles = getSampleStyleSheet()
    
    # Title style
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30,
        alignment=1  # Center
    )
    
    # Header
    elements = []
    elements.append(Paragraph("RR Milk Management System", title_style))
    elements.append(Paragraph(f"Daily Collections Report - {req_date}", title_style))
    if session_filter != 'all':
        elements.append(Paragraph(f"Session: {session_filter.title()}", styles['Heading3']))
    elements.append(Spacer(1, 12))
    
    # Summary stats
    summary_data = [
        ['Total Liters', 'Total Amount', 'Average Fat %', 'Collections Count'],
        [f"{total_liters:.2f}", f"₹ {total_amount:,.0f}", f"{avg_fat:.1f}%", str(len(collections))]
    ]
    
    summary_table = Table(summary_data, colWidths=[2*inch, 2*inch, 2*inch, 2*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#8B4513')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 20))
    
    # Data table
    data = [['Supplier ID', 'Name', 'Session', 'Milk Type', 'Liters', 'Fat %', 'Rate/L', 'Amount (₹)']]
    for c in collections:
        data.append([
            c.supplier.supplier_id, c.supplier.name, c.session.title(), 
            c.milk_type.title(), f"{c.liters:.2f}", f"{c.fat:.1f}", 
            f"{c.rate_per_liter:.2f}", f"₹ {c.amount:,.0f}"
        ])
    
    table = Table(data, colWidths=[1*inch, 1.5*inch, 0.8*inch, 0.8*inch, 0.7*inch, 0.6*inch, 0.7*inch, 1*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ALIGN', (4, 1), (7, -1), 'RIGHT'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
    ]))
    elements.append(table)
    
    # Footer
    elements.append(Spacer(1, 20))
    elements.append(Paragraph(f"Generated on: {get_today_ist()}", styles['Normal']))
    elements.append(Paragraph("RR Milk Management System", styles['Normal']))
    
    doc.build(elements)
    buf.seek(0)
    
    filename = f"daily_collections_{req_date}_{session_filter}.pdf"
    return send_file(
        buf,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )

@reports_bp.route('/monthly/export/pdf')
@login_required
def export_monthly_pdf():
    """Export monthly summary to PDF"""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    
    selected_month = request.args.get('month') or get_today_ist()[:7]
    like = selected_month + '%'
    
    # Get supplier data
    supplier_results = db.session.query(
        Supplier.supplier_id, Supplier.name, Supplier.mobile,
        func.coalesce(func.sum(Collection.liters), 0).label('total_liters'),
        func.coalesce(func.sum(Collection.amount), 0).label('total_amount')
    ).outerjoin(Collection, (Supplier.id == Collection.supplier_id) & (Collection.date.like(like)))\
     .group_by(Supplier.id).all()
    
    # Withdrawals
    wrows = db.session.query(
        Supplier.supplier_id, func.coalesce(func.sum(Withdrawal.amount), 0).label('withdrawn')
    ).outerjoin(Withdrawal, (Supplier.id == Withdrawal.supplier_id) & (Withdrawal.date.like(like)))\
     .group_by(Supplier.id).all()
    
    withdraw_map = {r.supplier_id: r.withdrawn for r in wrows}
    
    if not supplier_results:
        flash(f'No data found for {selected_month}', 'warning')
        return redirect(url_for('reports.monthly', month=selected_month))
    
    # Calculate totals
    total_liters = sum(float(r.total_liters or 0) for r in supplier_results)
    total_amount = sum(int(r.total_amount or 0) for r in supplier_results)
    total_withdrawn = sum(withdraw_map.get(r.supplier_id, 0) for r in supplier_results)
    
    # Create PDF
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4)
    styles = getSampleStyleSheet()
    
    # Title style
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30,
        alignment=1  # Center
    )
    
    # Header
    elements = []
    elements.append(Paragraph("RR Milk Management System", title_style))
    elements.append(Paragraph(f"Monthly Summary Report - {selected_month}", title_style))
    elements.append(Spacer(1, 12))
    
    # Summary stats
    summary_data = [
        ['Total Liters', 'Total Collections (₹)', 'Total Withdrawn (₹)', 'Net Balance (₹)'],
        [f"{total_liters:.2f}", f"₹ {total_amount:,.0f}", f"₹ {total_withdrawn:,.0f}", f"₹ {total_amount - total_withdrawn:,.0f}"]
    ]
    
    summary_table = Table(summary_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#8B4513')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 20))
    
    # Suppliers table
    elements.append(Paragraph("Supplier Summary", styles['Heading2']))
    elements.append(Spacer(1, 12))
    
    supplier_data = [['Supplier ID', 'Name', 'Mobile', 'Liters', 'Collections (₹)', 'Withdrawn (₹)', 'Balance (₹)']]
    for r in supplier_results:
        withdrawn = withdraw_map.get(r.supplier_id, 0) or 0
        balance = (r.total_amount or 0) - withdrawn
        supplier_data.append([
            r.supplier_id, r.name, r.mobile or '-', 
            f"{r.total_liters or 0:.2f}", f"₹ {r.total_amount or 0:,.0f}", 
            f"₹ {withdrawn:,.0f}", f"₹ {balance:,.0f}"
        ])
    
    supplier_table = Table(supplier_data, colWidths=[0.8*inch, 1.2*inch, 1*inch, 0.7*inch, 1*inch, 1*inch, 1*inch])
    supplier_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ALIGN', (3, 1), (6, -1), 'RIGHT'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
    ]))
    elements.append(supplier_table)
    
    # Footer
    elements.append(Spacer(1, 20))
    elements.append(Paragraph(f"Generated on: {get_today_ist()}", styles['Normal']))
    elements.append(Paragraph("RR Milk Management System", styles['Normal']))
    
    doc.build(elements)
    buf.seek(0)
    
    filename = f"monthly_summary_{selected_month}.pdf"
    return send_file(
        buf,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )
