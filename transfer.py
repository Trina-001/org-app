import os
import shutil
from pathlib import Path

def handle_duplicate(src_file, dest_file):
    """
    Handle duplicate files by adding a number suffix to the filename.
    Returns the final destination path.
    """
    if not dest_file.exists():
        return dest_file
    
    # Extract filename parts
    stem = dest_file.stem
    suffix = dest_file.suffix
    parent = dest_file.parent
    
    counter = 1
    while True:
        new_name = f"{stem}_{counter}{suffix}"
        new_dest = parent / new_name
        if not new_dest.exists():
            return new_dest
        counter += 1

def move_contents_recursively(src_dir, dest_dir):
    """
    Recursively move contents from src_dir to dest_dir, preserving structure.
    Handles duplicates by renaming files.
    """
    moved_items = []
    
    for item in src_dir.rglob('*'):
        if item.is_file():
            # Calculate relative path from source directory
            rel_path = item.relative_to(src_dir)
            target_path = dest_dir / rel_path
            
            # Create target directory if it doesn't exist
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Handle duplicates
            final_target = handle_duplicate(item, target_path)
            
            try:
                shutil.move(str(item), str(final_target))
                moved_items.append((str(item), str(final_target)))
                print(f"Moved: {item} -> {final_target}")
            except Exception as e:
                print(f"Error moving {item}: {e}")
    
    return moved_items

def normalize_folder_name(name):
    """
    Normalize folder name for comparison by:
    - Converting to lowercase
    - Removing spaces, hyphens, and underscores
    """
    return name.lower().replace(' ', '').replace('-', '').replace('_', '')

def find_matching_folder(source_name, main_folders):
    """
    Find matching folder using normalized name comparison.
    Returns the actual folder path if found, None otherwise.
    """
    normalized_source = normalize_folder_name(source_name)
    
    for folder_name, folder_path in main_folders.items():
        normalized_main = normalize_folder_name(folder_name)
        if normalized_source == normalized_main:
            return folder_path, folder_name
    
    return None, None

# app/transfer.py (modified for web use)
import os
import shutil
from pathlib import Path

# ... (keep all the existing functions from transfer.py)

def organize_webp_folders(main_folder_path):
    """
    Web version of the main function that takes folder path as argument
    and returns True/False instead of using input()
    """
    main_folder = Path(main_folder_path)
    webp_source_folder = main_folder / "__WEBP To be move to the right folders"
    
    # Check if paths exist
    if not main_folder.exists():
        print(f"Error: Main folder '{main_folder}' does not exist!")
        return False
    
    if not webp_source_folder.exists():
        print(f"Error: Source folder '{webp_source_folder}' does not exist!")
        return False
    
    # Get list of folders in main directory (excluding the source folder)
    main_folders = {folder.name: folder for folder in main_folder.iterdir() 
                   if folder.is_dir() and folder.name != "__WEBP To be move to the right folders"}
    
    print(f"Found {len(main_folders)} folders in main directory:")
    for folder_name in main_folders.keys():
        print(f"  - {folder_name}")
    
    # Process folders in the WEBP source directory
    folders_to_remove = []
    total_moved = 0
    
    for source_subfolder in webp_source_folder.iterdir():
        if not source_subfolder.is_dir():
            continue
            
        folder_name = source_subfolder.name
        print(f"\nProcessing folder: {folder_name}")
        
        # Check if matching folder exists in main directory using fuzzy matching
        target_folder, matched_name = find_matching_folder(folder_name, main_folders)
        
        if target_folder:
            print(f"Found matching folder: '{folder_name}' -> '{matched_name}'")
            print(f"Target path: {target_folder}")
            
            # Move contents while preserving structure
            moved_items = move_contents_recursively(source_subfolder, target_folder)
            
            if moved_items:
                print(f"Successfully moved {len(moved_items)} items")
                total_moved += len(moved_items)
                folders_to_remove.append(source_subfolder)
            else:
                print("No items were moved (folder might be empty)")
                # Still mark for removal if folder is empty
                if not any(source_subfolder.iterdir()):
                    folders_to_remove.append(source_subfolder)
        else:
            print(f"No matching folder found for: {folder_name}")
            # Show normalized name for debugging
            normalized = normalize_folder_name(folder_name)
            print(f"  Normalized name: '{normalized}'")
    
    # Remove empty source folders
    print(f"\nRemoving {len(folders_to_remove)} processed folders...")
    for folder_to_remove in folders_to_remove:
        try:
            # Double-check that folder is empty or only contains empty subdirectories
            if not any(item.is_file() for item in folder_to_remove.rglob('*')):
                shutil.rmtree(folder_to_remove)
                print(f"Removed folder: {folder_to_remove}")
            else:
                print(f"Warning: Folder {folder_to_remove} still contains files, not removing")
        except Exception as e:
            print(f"Error removing folder {folder_to_remove}: {e}")
    
    print(f"\nOrganization complete! Total files moved: {total_moved}")
    return True

# Keep the original main function for command line use
if __name__ == "__main__":
    main()

    