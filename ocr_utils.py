import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import re
from datetime import datetime
import numpy as np

# Configure Tesseract path (update for your system)
# For Ubuntu, it's usually in PATH automatically
# If not, uncomment and set:
# pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract'

def extract_milk_data_from_image(image_path):
    """
    Extract milk collection data from image using enhanced OCR
    Returns list of extracted entries
    """
    try:
        # Open and preprocess image
        image = Image.open(image_path)
        
        # Apply multiple preprocessing steps
        processed_image = preprocess_image_for_ocr(image)
        
        # Try multiple OCR configurations
        configs = [
            '--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.-/: ',
            '--oem 3 --psm 4',  # Assume a single column of text
            '--oem 3 --psm 11',  # Sparse text
            '--oem 3 --psm 12'   # Sparse text with orientation
        ]
        
        best_text = ""
        best_confidence = 0
        
        for config in configs:
            try:
                # Get data with confidence
                data = pytesseract.image_to_data(processed_image, config=config, output_type=pytesseract.Output.DICT)
                text = ' '.join(data['text'])
                confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0
                
                if avg_confidence > best_confidence:
                    best_confidence = avg_confidence
                    best_text = text
            except:
                continue
        
        # If no text found with advanced configs, try basic
        if not best_text.strip():
            best_text = pytesseract.image_to_string(processed_image)
        
        print(f"OCR Confidence: {best_confidence:.2f}%")
        print(f"Extracted Text:\n{best_text}")
        
        # Parse the extracted text
        entries = parse_milk_entries_enhanced(best_text)
        
        return entries
    except Exception as e:
        print(f"OCR Error: {e}")
        return []

def preprocess_image_for_ocr(image):
    """
    Enhance image for better OCR accuracy
    """
    # Convert to RGB if needed
    if image.mode != 'RGB':
        image = image.convert('RGB')
    
    # Convert to grayscale
    image = image.convert('L')
    
    # Increase contrast
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(2.5)
    
    # Increase sharpness
    enhancer = ImageEnhance.Sharpness(image)
    image = enhancer.enhance(2.0)
    
    # Apply thresholding (binarization)
    threshold = 128
    image = image.point(lambda p: p > threshold and 255)
    
    # Remove noise with median filter
    image = image.filter(ImageFilter.MedianFilter(size=3))
    
    # Resize if too small (2x for better recognition)
    if image.width < 1000:
        new_size = (image.width * 2, image.height * 2)
        image = image.resize(new_size, Image.Resampling.LANCZOS)
    
    return image

def parse_milk_entries_enhanced(text):
    """
    Enhanced parsing of OCR text to extract milk collection entries
    """
    entries = []
    lines = text.split('\n')
    
    # Patterns for detection
    date_patterns = [
        r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',  # DD/MM/YYYY or MM/DD/YYYY
        r'(\d{4}[/-]\d{1,2}[/-]\d{1,2})'     # YYYY-MM-DD
    ]
    
    supplier_pattern = r'([A-Za-z]+[\s]*\d+|\d+[\s]*[A-Za-z]+|[A-Z]+\d+)'
    liters_pattern = r'(\d+\.?\d*)\s*(?:l|L|lit|Liters?|Ltr)'
    fat_pattern = r'(\d+\.?\d*)\s*(?:%|fat|Fat|FAT)'
    
    current_date = datetime.now().strftime('%Y-%m-%d')
    current_session = 'morning'
    
    # Known supplier IDs from database (you should populate these)
    # This helps with recognition
    known_suppliers = get_known_supplier_ids()
    
    for line in lines:
        line = line.strip()
        if not line or len(line) < 3:
            continue
        
        entry = {}
        
        # Extract date
        for pattern in date_patterns:
            date_match = re.search(pattern, line)
            if date_match:
                date_str = date_match.group(1)
                try:
                    # Convert to YYYY-MM-DD format
                    if '/' in date_str:
                        parts = date_str.split('/')
                    else:
                        parts = date_str.split('-')
                    
                    if len(parts) == 3:
                        if len(parts[2]) == 4:  # YYYY
                            current_date = f"{parts[2]}-{int(parts[1]):02d}-{int(parts[0]):02d}"
                        elif len(parts[0]) == 4:  # YYYY
                            current_date = f"{parts[0]}-{int(parts[1]):02d}-{int(parts[2]):02d}"
                        else:  # DD/MM/YYYY
                            year = parts[2]
                            if len(year) == 2:
                                year = f"20{year}"
                            current_date = f"{year}-{int(parts[1]):02d}-{int(parts[0]):02d}"
                    break
                except:
                    pass
        
        # Detect session
        line_lower = line.lower()
        if 'morning' in line_lower or 'am' in line_lower or 'mor' in line_lower:
            current_session = 'morning'
        elif 'evening' in line_lower or 'pm' in line_lower or 'eve' in line_lower or 'even' in line_lower:
            current_session = 'evening'
        
        # Extract supplier ID - try multiple approaches
        supplier_id = None
        
        # Method 1: Look for known supplier IDs
        for known_id in known_suppliers:
            if known_id.lower() in line_lower:
                supplier_id = known_id
                break
        
        # Method 2: Use regex pattern
        if not supplier_id:
            supplier_match = re.search(supplier_pattern, line, re.IGNORECASE)
            if supplier_match:
                potential_id = supplier_match.group(1).upper()
                # Clean up the ID
                potential_id = re.sub(r'\s+', '', potential_id)
                if len(potential_id) >= 2:
                    supplier_id = potential_id
        
        if supplier_id:
            entry['supplier_id'] = supplier_id
        
        # Extract liters - look for numbers followed by L or similar
        liters_match = re.search(liters_pattern, line, re.IGNORECASE)
        if liters_match:
            entry['liters'] = float(liters_match.group(1))
        else:
            # Try just finding any number that could be liters (between 0.5 and 50)
            numbers = re.findall(r'(\d+\.?\d*)', line)
            for num in numbers:
                val = float(num)
                if 0.5 <= val <= 50:  # Reasonable milk quantity range
                    entry['liters'] = val
                    break
        
        # Extract fat percentage
        fat_match = re.search(fat_pattern, line, re.IGNORECASE)
        if fat_match:
            entry['fat'] = float(fat_match.group(1))
        else:
            # Default fat based on milk type
            entry['fat'] = 6.0  # Default buffalo fat
        
        # Extract milk type
        if 'cow' in line_lower:
            entry['milk_type'] = 'cow'
            if 'fat' not in entry:
                entry['fat'] = 4.0  # Default cow fat
        else:
            entry['milk_type'] = 'buffalo'
        
        # Only add entry if we have supplier ID and liters
        if entry.get('supplier_id') and entry.get('liters'):
            entry['date'] = current_date
            entry['session'] = current_session
            entries.append(entry)
            print(f"Extracted entry: {entry}")
    
    return entries

def get_known_supplier_ids():
    """
    Get list of known supplier IDs from database
    This function will be called from app context
    """
    try:
        from app import app, Supplier
        with app.app_context():
            suppliers = Supplier.query.all()
            return [s.supplier_id for s in suppliers]
    except:
        # Return some common patterns if database not accessible
        return ['S001', 'S002', 'S003', 'S004', 'S005', 'S006', 'S007', 'S008', 'S009', 'S010']

def enhance_image_brightness(image, factor=1.5):
    """Enhance image brightness"""
    enhancer = ImageEnhance.Brightness(image)
    return enhancer.enhance(factor)

def rotate_image_if_needed(image):
    """Auto-rotate image based on orientation"""
    try:
        from PIL import ImageOps
        # Check EXIF data for orientation
        if hasattr(image, '_getexif'):
            exif = image._getexif()
            if exif:
                orientation = exif.get(274, 1)
                if orientation == 3:
                    image = image.rotate(180, expand=True)
                elif orientation == 6:
                    image = image.rotate(270, expand=True)
                elif orientation == 8:
                    image = image.rotate(90, expand=True)
    except:
        pass
    return image
