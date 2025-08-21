import os
import shutil
import re
from datetime import datetime
from collections import defaultdict

def normalize_filename(filename):
    """Normalize filenames by treating hyphens and spaces as equivalent before extension"""
    basename, ext = os.path.splitext(filename)
    
    # Handle version suffixes (_v1, _v2, etc.)
    version_match = re.search(r'_v\d+$', basename)
    if version_match:
        basename = basename[:version_match.start()]
    
    normalized = re.sub(r'[-_\s]', '', basename).strip().lower()
    return f"{normalized}{ext.lower()}"

def convert_alpha_to_numeric_suffix(filename):
    """Convert alphabetic suffixes to numeric equivalents (A=1, B=2, etc.)"""
    basename, ext = os.path.splitext(filename)
    
    # Handle version suffixes first
    version_suffix = ""
    version_match = re.search(r'_v\d+$', basename)
    if version_match:
        version_suffix = version_match.group(0)
        basename = basename[:version_match.start()]
    
    # Look for single alphabetic character at the end
    match = re.search(r'([a-zA-Z])$', basename)
    if match:
        alpha_char = match.group(1).upper()
        numeric_value = ord(alpha_char) - ord('A') + 1
        # Replace the alphabetic suffix with numeric
        converted_basename = basename[:-1] + str(numeric_value)
        return f"{converted_basename}{version_suffix}{ext}"
    
    return f"{basename}{version_suffix}{ext}"

def normalize_filename_with_alpha_numeric(filename):
    """Normalize filename with both space/hyphen normalization and alpha-to-numeric conversion"""
    # First convert alpha suffixes to numeric
    alpha_converted = convert_alpha_to_numeric_suffix(filename)
    # Then apply standard normalization
    return normalize_filename(alpha_converted)

def extract_basename_and_suffix(filename):
    """Extract the basename and suffix from a filename
    
    Examples:
    - Uniserve-UNIO22-4 -> basename: Uniserve-UNIO22-4, suffix: None
    - Uniserve-UNIO22-4-A -> basename: Uniserve-UNIO22-4, suffix: A
    - Uniserve-UNIO22-4-1 -> basename: Uniserve-UNIO22-4, suffix: 1
    - Uniserve-UNIO22-4-10 -> basename: Uniserve-UNIO22-4, suffix: 10
    """
    basename_no_ext, ext = os.path.splitext(filename)
    
    # Handle version suffixes first (_v1, _v2, etc.)
    version_suffix = ""
    version_match = re.search(r'_v\d+$', basename_no_ext)
    if version_match:
        version_suffix = version_match.group(0)
        basename_no_ext = basename_no_ext[:version_match.start()]
    
    # Look for suffix patterns at the end
    # Pattern 1: Single letter (A, B, C, etc.)
    single_letter_match = re.search(r'[-_]([A-Za-z])$', basename_no_ext)
    if single_letter_match:
        suffix = single_letter_match.group(1)
        basename = basename_no_ext[:single_letter_match.start()]
        return basename, suffix
    
    # Pattern 2: Single or multiple digits (1, 2, 10, etc.)
    digit_match = re.search(r'[-_](\d+)$', basename_no_ext)
    if digit_match:
        suffix = digit_match.group(1)
        basename = basename_no_ext[:digit_match.start()]
        return basename, suffix
    
    # Pattern 3: Letter followed by digits (A1, B2, etc.)
    letter_digit_match = re.search(r'[-_]([A-Za-z]\d+)$', basename_no_ext)
    if letter_digit_match:
        suffix = letter_digit_match.group(1)
        basename = basename_no_ext[:letter_digit_match.start()]
        return basename, suffix
    
    # No suffix found, the whole name is the basename
    return basename_no_ext, None

def find_existing_file_variant(target_folder, filename):
    """Find if a file with the same normalized name already exists in the target folder"""
    if not os.path.exists(target_folder):
        return None
    
    # First try standard normalization (spaces/hyphens/underscores)
    normalized_new = normalize_filename(filename)
    
    # Then try alpha-to-numeric normalization
    alpha_numeric_new = normalize_filename_with_alpha_numeric(filename)
    
    print(f"DEBUG: Looking for matches for '{filename}'")
    print(f"  - Standard normalized: '{normalized_new}'")
    print(f"  - Alpha-numeric normalized: '{alpha_numeric_new}'")
    
    for existing_file in os.listdir(target_folder):
        if os.path.isfile(os.path.join(target_folder, existing_file)):
            normalized_existing = normalize_filename(existing_file)
            alpha_numeric_existing = normalize_filename_with_alpha_numeric(existing_file)
            
            # Check both normalization methods
            if (normalized_new == normalized_existing or 
                alpha_numeric_new == alpha_numeric_existing or
                normalized_new == alpha_numeric_existing or
                alpha_numeric_new == normalized_existing):
                
                print(f"  - Match found: '{existing_file}'")
                print(f"    - Existing standard: '{normalized_existing}'")
                print(f"    - Existing alpha-numeric: '{alpha_numeric_existing}'")
                return os.path.join(target_folder, existing_file)
    
    print(f"  - No matches found")
    return None

def is_variant_code(word):
    """Check if word is a variant code (single letter or number)"""
    return re.fullmatch(r'^[A-Za-z0-9]$', word)

def extract_name_code_variant(basename):
    """Extract brand name, product code, and variant from filename"""
    # Remove version suffix for parsing
    original_basename = basename
    version_suffix = ""
    version_match = re.search(r'_v\d+$', basename)
    if version_match:
        version_suffix = version_match.group(0)
        basename = basename[:version_match.start()]
    
    cleaned = re.sub(r'[^\w\s\.-]', '', basename, flags=re.UNICODE)
    parts = re.split(r'[-_\s]', cleaned)
    parts = [p for p in parts if p]
    
    if not parts:
        return None, None, None
    
    print(f"DEBUG: Parsing '{original_basename}' -> parts: {parts}")
    
    # Special handling for patterns like "Uniserve-UNIO22-4"
    # Look for brand name followed by alphanumeric code with numbers
    if len(parts) >= 3:
        first_part = parts[0]
        # Check if first part is purely alphabetic (likely brand name)
        if re.fullmatch(r'[a-zA-Z]+', first_part):
            # Check if the remaining parts form a product code
            remaining_parts = parts[1:]
            
            # For cases like ["Uniserve", "UNIO22", "4"]
            # We want to keep "UNIO22-4" together as the product code
            if len(remaining_parts) >= 2:
                # Check if we have a pattern like alphanumeric + numeric
                second_part = remaining_parts[0]  # "UNIO22"
                third_part = remaining_parts[1]   # "4"
                
                # If second part contains letters and numbers, and third part is numeric
                # treat them as one product code
                if (re.search(r'[a-zA-Z]', second_part) and 
                    re.search(r'\d', second_part) and 
                    re.fullmatch(r'\d+', third_part)):
                    
                    # Join the product code parts
                    product_code_parts = remaining_parts
                    product_code = '-'.join(product_code_parts)
                    
                    print(f"DEBUG: Special case - Brand: '{first_part}', Product Code: '{product_code}'")
                    return first_part, product_code, None
    
    # Original logic continues here for other cases...
    name_parts = []
    code_parts = []
    variant = None
    
    # Check for variant (single letter/number at the end)
    if len(parts) > 1 and is_variant_code(parts[-1]):
        variant = parts[-1]
        parts = parts[:-1]
        print(f"DEBUG: Found variant: {variant}")
    
    # Look for technical terms with version numbers
    version_pattern = r'\d+\.\d+'
    tech_with_version_idx = -1
    
    for i, part in enumerate(parts):
        if re.search(version_pattern, part):
            tech_with_version_idx = i
            print(f"DEBUG: Found technical term with version at index {i}: {part}")
            break
    
    if tech_with_version_idx != -1:
        if tech_with_version_idx == 0:
            name_parts = parts[:1]
            code_parts = parts[1:] if len(parts) > 1 else []
        else:
            name_parts = parts[:tech_with_version_idx]
            code_parts = parts[tech_with_version_idx:]
    else:
        if len(parts) == 1:
            single_part = parts[0]
            brand_model_match = re.match(r'^([a-zA-Z]+)(\d+.*)$', single_part)
            if brand_model_match:
                brand = brand_model_match.group(1)
                model = brand_model_match.group(2)
                name_parts = [brand]
                code_parts = [model]
                print(f"DEBUG: Split single part brand+model: brand='{brand}', model='{model}'")
            else:
                name_parts = [single_part]
                code_parts = []
                
        elif len(parts) == 2:
            first_part, second_part = parts[0], parts[1]
            
            brand_model_match = re.match(r'^([a-zA-Z]+)(\d+.*)$', first_part)
            if brand_model_match:
                brand = brand_model_match.group(1)
                model_part1 = brand_model_match.group(2)
                name_parts = [brand]
                code_parts = [model_part1, second_part]
                print(f"DEBUG: First part has brand+model: brand='{brand}', model='{model_part1}+{second_part}'")
            else:
                if re.fullmatch(r'[a-zA-Z]+', first_part) and re.search(r'\d', second_part):
                    name_parts = [first_part]
                    code_parts = [second_part]
                    print(f"DEBUG: Clear brand-model split: brand='{first_part}', model='{second_part}'")
                else:
                    if len(second_part) >= 2:
                        name_parts = [first_part]
                        code_parts = [second_part]
                    else:
                        name_parts = parts
                        code_parts = []
        else:
            first_part = parts[0]
            
            if re.fullmatch(r'[a-zA-Z]+', first_part):
                name_parts = [first_part]
                code_parts = parts[1:]
                print(f"DEBUG: Multi-part with alphabetic brand: brand='{first_part}', code='{parts[1:]}'")
            else:
                product_code_start = 1
                for i in range(1, len(parts)):
                    if re.search(r'\d', parts[i]):
                        product_code_start = i
                        break
                
                name_parts = parts[:product_code_start]
                code_parts = parts[product_code_start:]
    
    name = ' '.join(name_parts).strip() if name_parts else None
    
    if code_parts:
        if len(code_parts) > 1:
            code_portion = basename
            if name_parts:
                for name_part in name_parts:
                    code_portion = re.sub(rf'^{re.escape(name_part)}[-_\s]*', '', code_portion, 1)
            
            if variant:
                code_portion = re.sub(rf'[-_\s]*{re.escape(variant)}$', '', code_portion)
            
            if '_' in code_portion and '-' not in code_portion:
                code = '_'.join(code_parts)
            else:
                code = '-'.join(code_parts)
        else:
            code = code_parts[0]
    else:
        code = None
    
    if not name and code:
        if not re.search(r'\d', code) and len(code.split('-')) == 1:
            name = code.replace('-', ' ')
            code = None
    
    if not name and not code:
        name = ' '.join(parts[:1]) if parts else None
    
    print(f"DEBUG: Final result -> name: '{name}', code: '{code}', variant: '{variant}'")
    return name, code, variant

def get_file_category(filename):
    """Get file category based on file extension"""
    ext = os.path.splitext(filename)[1].lower()
    basename = os.path.basename(filename).lower()
    
    if basename.startswith('img'):
        return 'Unedited'
    if ext in ['.webp']:
        return 'WEBP'
    if ext in ['.jpg', '.jpeg', '.png']:
        return 'JPEG'
    if ext in ['.mov']:
        return 'Video/Unedited video'
    if ext in ['.mp4']:
        return 'Video/Edited video'
    # if ext in ['.avi', '.mkv']:
        # return 'Video'
    return None

def create_old_images_folder(target_folder, category=None):
    """Create Old Images folder with optional category subfolder"""
    old_images_path = os.path.join(target_folder, "Old Images")
    
    if category:
        # Handle nested categories like "Video/Unedited video"
        category_parts = category.split('/')
        for part in category_parts:
            old_images_path = os.path.join(old_images_path, part)
    
    if not os.path.exists(old_images_path):
        os.makedirs(old_images_path)
        print(f"Created Old Images folder: {old_images_path}")
    return old_images_path

def handle_existing_file(existing_file_path, old_images_folder):
    """Handle existing files by moving them to Old Images with timestamp"""
    filename = os.path.basename(existing_file_path)
    base, ext = os.path.splitext(filename)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    new_name = f"{base}_replaced_{timestamp}{ext}"
    
    old_file_path = os.path.join(old_images_folder, new_name)
    
    try:
        shutil.move(existing_file_path, old_file_path)
        print(f"Moved existing file to Old Images: {os.path.relpath(old_file_path)}")
    except Exception as e:
        print(f"Error moving existing file to Old Images: {e}")

def group_files_by_basename(files):
    """Group files by their basename for better organization
    
    Returns a dictionary where keys are basenames and values are lists of files
    """
    basename_groups = defaultdict(list)
    
    for filename in files:
        basename, suffix = extract_basename_and_suffix(filename)
        basename_groups[basename].append(filename)
        print(f"DEBUG: File '{filename}' -> basename: '{basename}', suffix: '{suffix}'")
    
    return basename_groups

def determine_product_code_from_basename_group(basename_group, brand_name):
    """Determine the product code folder name from a group of files with the same basename"""
    if not basename_group:
        return None
    
    # Use the first file to determine the product code structure
    first_file = basename_group[0]
    basename_no_ext = os.path.splitext(first_file)[0]
    basename, suffix = extract_basename_and_suffix(first_file)
    
    print(f"DEBUG: Determining product code from basename group: {basename_group}")
    print(f"DEBUG: Using file '{first_file}' as reference")
    print(f"DEBUG: Extracted basename: '{basename}', suffix: '{suffix}'")
    
    # Extract the product code from the basename
    name, product_code, variant = extract_name_code_variant(basename)
    
    print(f"DEBUG: From basename extraction -> name: '{name}', product_code: '{product_code}', variant: '{variant}'")
    
    if product_code:
        return product_code
    elif name and name.lower() != brand_name.lower():
        # If no clear product code but name differs from brand, use the name
        return name
    else:
        # Fallback: use the basename itself as product code
        return basename


def consolidate_product_codes(product_codes):
    """Consolidate product codes to use the most specific version
    
    For example, if we have both 'UNIO22' and 'UNIO22-4', we should use 'UNIO22-4'
    """
    if not product_codes:
        return product_codes
    
    # Group codes by their base (before any hyphen-number suffix)
    code_groups = defaultdict(list)
    
    for code in product_codes:
        # Find the base code (everything before a pattern like -4, -10, etc.)
        base_match = re.match(r'^([A-Za-z0-9]+)', code)
        if base_match:
            base = base_match.group(1)
            code_groups[base].append(code)
    
    consolidated = {}
    
    for base, codes in code_groups.items():
        if len(codes) == 1:
            # Only one code for this base, keep it
            consolidated[codes[0]] = codes[0]
        else:
            # Multiple codes, find the most specific one
            # Sort by length (longer is more specific) and then alphabetically
            sorted_codes = sorted(codes, key=lambda x: (-len(x), x))
            most_specific = sorted_codes[0]
            
            print(f"DEBUG: Consolidating codes {codes} -> using '{most_specific}'")
            
            # Map all codes to the most specific one
            for code in codes:
                consolidated[code] = most_specific
    
    return consolidated

def determine_final_product_codes(brand_files):
    """Determine the final product codes for all files in a brand, consolidating similar ones"""
    
    # First pass: collect all product codes for this brand
    all_product_codes = set()
    file_to_product_code = {}
    
    for filename in brand_files:
        basename_no_ext = os.path.splitext(filename)[0]
        basename, suffix = extract_basename_and_suffix(filename)
        
        name, product_code, variant = extract_name_code_variant(basename)
        
        if product_code:
            all_product_codes.add(product_code)
            file_to_product_code[filename] = product_code
    
    print(f"DEBUG: All product codes found: {all_product_codes}")
    
    # Consolidate the product codes
    code_mapping = consolidate_product_codes(all_product_codes)
    
    print(f"DEBUG: Code mapping: {code_mapping}")
    
    # Apply the consolidation mapping
    final_file_to_product_code = {}
    for filename, original_code in file_to_product_code.items():
        if original_code in code_mapping:
            final_file_to_product_code[filename] = code_mapping[original_code]
        else:
            final_file_to_product_code[filename] = original_code
    
    return final_file_to_product_code

def organize_webp_folder_only(webp_folder_path):
    """Organize files within the WEBP folder only, creating brand/product/category structure with product code consolidation"""
    print(f"Organizing files in WEBP folder: {webp_folder_path}")
    
    # First pass: collect all files and group them by brand
    brand_files = defaultdict(list)
    
    for root, dirs, files in os.walk(webp_folder_path):
        for filename in files:
            if '.' not in filename:
                continue
            
            basename_no_ext = os.path.splitext(filename)[0]
            
            # Extract brand name from the file
            name, product_code, variant = extract_name_code_variant(basename_no_ext)
            
            if name:
                brand_files[name].append(filename)
    
    # Second pass: for each brand, determine consolidated product codes
    for brand_name, files in brand_files.items():
        print(f"\nProcessing brand: {brand_name}")
        print(f"Files in brand: {files}")
        
        # Get the final product code mapping for all files in this brand
        file_to_final_product_code = determine_final_product_codes(files)
        
        print(f"Final product code mapping: {file_to_final_product_code}")
        
        # Group files by their final product code
        product_code_groups = defaultdict(list)
        for filename in files:
            final_product_code = file_to_final_product_code.get(filename)
            product_code_groups[final_product_code].append(filename)
        
        # Process each product code group
        for product_code, files_in_product in product_code_groups.items():
            print(f"\nProcessing product code group: {product_code}")
            print(f"Files in group: {files_in_product}")
            
            # Create brand folder
            brand_folder_path = os.path.join(webp_folder_path, brand_name)
            os.makedirs(brand_folder_path, exist_ok=True)
            
            # Create product folder if product code exists
            if product_code:
                product_folder_path = os.path.join(brand_folder_path, product_code)
                os.makedirs(product_folder_path, exist_ok=True)
                target_folder = product_folder_path
                print(f"Created/using product folder: {product_code}")
            else:
                target_folder = brand_folder_path
            
            # Process each file in the product code group
            for filename in files_in_product:
                # Find the actual file path
                file_path = None
                for root, dirs, files in os.walk(webp_folder_path):
                    if filename in files:
                        file_path = os.path.join(root, filename)
                        break
                
                if not file_path:
                    print(f"Warning: Could not find file path for {filename}")
                    continue
                
                print(f"Processing file: {filename}")
                
                # Determine file category and create category folder if needed
                file_category = get_file_category(filename)
                if file_category:
                    # Handle nested categories like "Video/Unedited video"
                    category_parts = file_category.split('/')
                    category_folder_path = target_folder
                    for part in category_parts:
                        category_folder_path = os.path.join(category_folder_path, part)
                        os.makedirs(category_folder_path, exist_ok=True)
                    
                    final_destination_folder = category_folder_path
                    print(f"Created/using category folder: {file_category}")
                else:
                    final_destination_folder = target_folder
                
                # Check for existing files with normalized names
                existing_file_path = find_existing_file_variant(final_destination_folder, filename)
                final_destination = os.path.join(final_destination_folder, filename)
                
                if existing_file_path:
                    existing_filename = os.path.basename(existing_file_path)
                    print(f"Found existing file with similar name: {existing_filename}")
                    print(f"New file: {filename}")
                    
                    old_images_folder = create_old_images_folder(target_folder, file_category)
                    handle_existing_file(existing_file_path, old_images_folder)
                elif os.path.exists(final_destination):
                    print(f"File already exists at destination: {final_destination}")
                    old_images_folder = create_old_images_folder(target_folder, file_category)
                    handle_existing_file(final_destination, old_images_folder)
                
                # Move the file to its final destination
                try:
                    if file_path != final_destination:
                        shutil.move(file_path, final_destination)
                        print(f"Moved {filename} to: {os.path.relpath(final_destination, webp_folder_path)}")
                except Exception as e:
                    print(f"Error moving {filename}: {str(e)}")

def clean_up_empty_product_folders(webp_folder_path):
    """Clean up empty product folders that may have been created during consolidation"""
    print("Cleaning up empty product folders...")
    
    for root, dirs, files in os.walk(webp_folder_path, topdown=False):
        for dir_name in dirs:
            dir_path = os.path.join(root, dir_name)
            
            # Skip Old Images folders
            if dir_name == "Old Images":
                continue
            
            try:
                # Check if directory is empty or only contains empty subdirectories
                is_empty = True
                for sub_root, sub_dirs, sub_files in os.walk(dir_path):
                    if sub_files or any(sub_dir != "Old Images" for sub_dir in sub_dirs):
                        is_empty = False
                        break
                
                if is_empty:
                    shutil.rmtree(dir_path)
                    print(f"Removed empty folder: {os.path.relpath(dir_path, webp_folder_path)}")
            except OSError as e:
                print(f"Could not remove folder {dir_path}: {e}")

def organize_webp_folder_only(webp_folder_path):
    """Organize files within the WEBP folder only, creating brand/product/category structure with product code consolidation"""
    print(f"Organizing files in WEBP folder: {webp_folder_path}")
    
    # First pass: collect all files and group them by brand
    brand_files = defaultdict(list)
    
    for root, dirs, files in os.walk(webp_folder_path):
        for filename in files:
            if '.' not in filename:
                continue
            
            basename_no_ext = os.path.splitext(filename)[0]
            
            # Extract brand name from the file
            name, product_code, variant = extract_name_code_variant(basename_no_ext)
            
            if name:
                brand_files[name].append(filename)
    
    # Second pass: for each brand, determine consolidated product codes
    for brand_name, files in brand_files.items():
        print(f"\nProcessing brand: {brand_name}")
        print(f"Files in brand: {files}")
        
        # Get the final product code mapping for all files in this brand
        file_to_final_product_code = determine_final_product_codes(files)
        
        print(f"Final product code mapping: {file_to_final_product_code}")
        
        # Group files by their final product code
        product_code_groups = defaultdict(list)
        for filename in files:
            final_product_code = file_to_final_product_code.get(filename)
            product_code_groups[final_product_code].append(filename)
        
        # Process each product code group
        for product_code, files_in_product in product_code_groups.items():
            print(f"\nProcessing product code group: {product_code}")
            print(f"Files in group: {files_in_product}")
            
            # Create brand folder
            brand_folder_path = os.path.join(webp_folder_path, brand_name)
            os.makedirs(brand_folder_path, exist_ok=True)
            
            # Create product folder if product code exists
            if product_code:
                product_folder_path = os.path.join(brand_folder_path, product_code)
                os.makedirs(product_folder_path, exist_ok=True)
                target_folder = product_folder_path
                print(f"Created/using product folder: {product_code}")
            else:
                target_folder = brand_folder_path
            
            # Process each file in the product code group
            for filename in files_in_product:
                # Find the actual file path
                file_path = None
                for root, dirs, files in os.walk(webp_folder_path):
                    if filename in files:
                        file_path = os.path.join(root, filename)
                        break
                
                if not file_path:
                    print(f"Warning: Could not find file path for {filename}")
                    continue
                
                print(f"Processing file: {filename}")
                
                # Determine file category and create category folder if needed
                file_category = get_file_category(filename)
                if file_category:
                    # Handle nested categories like "Video/Unedited video"
                    category_parts = file_category.split('/')
                    category_folder_path = target_folder
                    for part in category_parts:
                        category_folder_path = os.path.join(category_folder_path, part)
                        os.makedirs(category_folder_path, exist_ok=True)
                    
                    final_destination_folder = category_folder_path
                    print(f"Created/using category folder: {file_category}")
                else:
                    final_destination_folder = target_folder
                
                # Check for existing files with normalized names
                existing_file_path = find_existing_file_variant(final_destination_folder, filename)
                final_destination = os.path.join(final_destination_folder, filename)
                
                if existing_file_path:
                    existing_filename = os.path.basename(existing_file_path)
                    print(f"Found existing file with similar name: {existing_filename}")
                    print(f"New file: {filename}")
                    
                    old_images_folder = create_old_images_folder(target_folder, file_category)
                    handle_existing_file(existing_file_path, old_images_folder)
                elif os.path.exists(final_destination):
                    print(f"File already exists at destination: {final_destination}")
                    old_images_folder = create_old_images_folder(target_folder, file_category)
                    handle_existing_file(final_destination, old_images_folder)
                
                # Move the file to its final destination
                try:
                    if file_path != final_destination:
                        shutil.move(file_path, final_destination)
                        print(f"Moved {filename} to: {os.path.relpath(final_destination, webp_folder_path)}")
                except Exception as e:
                    print(f"Error moving {filename}: {str(e)}")

def remove_empty_folders(folder_path):
    """Remove empty folders recursively within the WEBP folder"""
    print(f"Removing empty folders in: {folder_path}")
    
    for root, dirs, files in os.walk(folder_path, topdown=False):
        for dir_name in dirs:
            dir_path = os.path.join(root, dir_name)
            
            # Skip Old Images folders
            if dir_name == "Old Images":
                continue
                
            try:
                if not os.listdir(dir_path):
                    os.rmdir(dir_path)
                    print(f"Removed empty folder: {os.path.relpath(dir_path, folder_path)}")
            except OSError:
                pass

def organize_webp_files(webp_folder_path):
    """Main function to organize files within the WEBP folder with product code consolidation"""
    
    if not os.path.exists(webp_folder_path):
        print(f"Error: Folder '{webp_folder_path}' does not exist.")
        return False
    
    # Verify this is actually a WEBP folder
    folder_name = os.path.basename(webp_folder_path).lower()
    if not folder_name.startswith('__webp'):
        print(f"Warning: The folder name doesn't start with '__webp'. Continuing anyway...")
    
    print(f"Found WEBP folder: {webp_folder_path}")
    print("Starting organization within WEBP folder with product code consolidation...")
    
    # Organize files within the WEBP folder
    organize_webp_folder_only(webp_folder_path)
    
    # Clean up empty folders (including consolidated product folders)
    clean_up_empty_product_folders(webp_folder_path)
    
    print("Organization complete! All files organized within the WEBP folder.")
    
    return True

# Main execution
if __name__ == "__main__":
    # Get folder path from user
    folder_to_organize = input("Enter the path of '__WEBP To be move to the right folders' folder: ").strip().strip('"')
    
    # Run the organization
    success = organize_webp_files(folder_to_organize)
    
    if success:
        print("\n✅ Organization completed successfully!")
        # print("All files have been organized within the WEBP folder.")
    else:
        print("\n❌ Organization failed!")
    
    input("Press Enter to exit...")