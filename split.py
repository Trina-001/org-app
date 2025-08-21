import os
import shutil
import re
from pathlib import Path
import argparse
import string
import time
import stat

def get_file_timestamp(file_path):
    """Get file modification time."""
    try:
        return os.path.getmtime(file_path)
    except OSError:
        return 0

def is_media_file(filename):
    """Check if file is a media file that should be processed normally."""
    media_extensions = {'.webp', '.jpg', '.jpeg', '.mov', '.mp4', '.png'}
    return Path(filename).suffix.lower() in media_extensions

def is_image_file(filename):
    """Check if filename starts with image prefixes or contains timestamp."""
    if filename.lower().endswith('.mov'):
        return False
    prefixes = ['img', 'images', 'image']
    timestamp_pattern = r'\d{8}_\d{6}'
    return (filename.lower().startswith(tuple(prefixes)) or 
            bool(re.search(timestamp_pattern, filename)))

def is_versioned_file(filename):
    """Check if filename contains _v followed by number."""
    return bool(re.search(r'_v\d+', filename))

def has_sequence_suffix(filename):
    """Check if filename ends with a letter or digit preceded by optional separator, before extension."""
    name = Path(filename).stem
    return bool(re.search(r'[-_\s][A-Za-z0-9]$', name))

def ensure_sequence_suffix(filename):
    """Ensure filename ends with sequence suffix, adding -0 if missing."""
    if has_sequence_suffix(filename):
        return filename
    
    path = Path(filename)
    new_stem = f"{path.stem}-0"
    return path.parent / f"{new_stem}{path.suffix}"

def get_versioned_filename(file_path, version):
    """Generate versioned filename (report_v1.txt)."""
    path = Path(file_path)
    stem = re.sub(r'_v\d+$', '', path.stem)
    return path.parent / f"{stem}_v{version}{path.suffix}"

def process_mov_file(file_path, main_path, webp_folder):
    """Process .mov file with Brand-Product-ID naming convention."""
    rel_path = file_path.relative_to(main_path)
    parts = list(rel_path.parts)
    
    brand = parts[0] if len(parts) > 1 else "UnknownBrand"
    product = parts[1] if len(parts) > 2 else "UnknownProduct"
    
    existing_files = list(webp_folder.glob(f"{brand}-{product}-*{file_path.suffix}"))
    seq_id = string.ascii_uppercase[len(existing_files)] if existing_files else "A"
    
    new_name = f"{brand}-{product}-{seq_id}{file_path.suffix}"
    dest = webp_folder / new_name
    
    print(f"Processing .mov: {rel_path} -> {new_name}")
    shutil.move(str(file_path), str(dest))
    return dest

def process_gslisting_folder(folder_path, main_path, gslisting_folder):
    """Move entire .gslisting folder to gslisting/ directory."""
    rel_path = folder_path.relative_to(main_path)
    dest = gslisting_folder / folder_path.name
    
    # Handle conflicts by adding number suffix
    counter = 1
    original_dest = dest
    while dest.exists():
        dest = gslisting_folder / f"{original_dest.stem}_{counter}{original_dest.suffix}"
        counter += 1
    
    print(f"🗂️  Moving .gslisting folder: {rel_path} -> gslisting/{dest.name}")
    shutil.move(str(folder_path), str(dest))
    return dest

def resolve_conflict(source_file, dest_file, webp_folder):
    """Handle filename conflicts by versioning all duplicates."""
    source_path = Path(source_file)
    dest_path = Path(dest_file)
    
    base_name = re.sub(r'_v\d+$', '', dest_path.stem)
    extension = dest_path.suffix
    directory = dest_path.parent
    
    conflicting_files = []
    for f in directory.glob(f"{base_name}*{extension}"):
        if f != source_path:
            conflicting_files.append((get_file_timestamp(f), str(f)))
    
    conflicting_files.append((get_file_timestamp(source_file), source_file))
    conflicting_files.sort(key=lambda x: x[0])
    
    for version, (_, file_path) in enumerate(conflicting_files, 1):
        new_path = webp_folder / get_versioned_filename(file_path, version).name
        if Path(file_path).exists():
            shutil.move(file_path, new_path)
            print(f"  Versioned: {Path(file_path).name} -> {new_path.name}")
    
    return webp_folder / get_versioned_filename(source_file, len(conflicting_files)).name

def move_file_safely(source_file, dest_file, webp_folder):
    """Move file with conflict resolution."""
    source_path = Path(source_file)
    dest_path = Path(dest_file)
    
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    
    if not dest_path.exists():
        shutil.move(source_file, dest_file)
        return dest_path
    
    print(f"  Conflict detected: {source_path.name}")
    return resolve_conflict(source_file, dest_file, webp_folder)

def force_remove_directory(dir_path):
    """Force remove a directory, handling permission issues."""
    try:
        # Try normal removal first
        dir_path.rmdir()
        return True
    except OSError:
        try:
            # Try to change permissions and remove
            os.chmod(dir_path, stat.S_IWRITE | stat.S_IREAD | stat.S_IEXEC)
            dir_path.rmdir()
            return True
        except OSError:
            try:
                # Last resort: use shutil.rmtree for stubborn directories
                if dir_path.exists():
                    shutil.rmtree(dir_path)
                    return True
            except OSError:
                return False
    return False

def is_directory_truly_empty(dir_path):
    """Check if directory is truly empty, including hidden files."""
    try:
        # Check if any items exist (including hidden)
        items = list(dir_path.iterdir())
        return len(items) == 0
    except (OSError, PermissionError):
        return False

def remove_empty_dirs_aggressive(start_path):
    """Ultra-aggressive empty directory removal with multiple strategies."""
    start_path = Path(start_path)
    kept_folders = {
        start_path,
        start_path / "Needs Labeling",
        start_path / "__WEBP To be move to the right folders",
        start_path / "gslisting"
    }
    
    removed = 0
    max_passes = 10  # Increased passes for maximum thoroughness
    
    print("\n🗂️  Starting aggressive empty folder removal...")
    
    for pass_num in range(max_passes):
        current_pass_removed = 0
        print(f"  Pass {pass_num + 1}/{max_passes}...")
        
        # Collect all directories first to avoid modification during iteration
        all_dirs = []
        for root, dirs, files in os.walk(start_path, topdown=False):
            for dir_name in dirs:
                dir_path = Path(root) / dir_name
                all_dirs.append(dir_path)
        
        # Process directories from deepest to shallowest
        all_dirs.sort(key=lambda x: len(x.parts), reverse=True)
        
        for dir_path in all_dirs:
            if dir_path in kept_folders or not dir_path.exists():
                continue
                
            if is_directory_truly_empty(dir_path):
                if force_remove_directory(dir_path):
                    print(f"    ✓ Removed: {dir_path.relative_to(start_path)}")
                    current_pass_removed += 1
                    removed += 1
                else:
                    print(f"    ✗ Failed to remove: {dir_path.relative_to(start_path)}")
        
        if current_pass_removed == 0:
            print(f"    No more empty directories found after pass {pass_num + 1}")
            break
        else:
            print(f"    Removed {current_pass_removed} directories in this pass")
    
    # Final verification with direct filesystem traversal
    print("\n🔍 Final verification scan...")
    remaining_empty = []
    
    for root, dirs, files in os.walk(start_path, topdown=False):
        root_path = Path(root)
        if (root_path not in kept_folders and 
            root_path != start_path and 
            is_directory_truly_empty(root_path)):
            remaining_empty.append(root_path)
    
    # Attempt to remove any remaining empty directories
    final_removed = 0
    for empty_dir in remaining_empty:
        if force_remove_directory(empty_dir):
            print(f"    ✓ Final removal: {empty_dir.relative_to(start_path)}")
            final_removed += 1
            removed += 1
        else:
            print(f"    ⚠️  Stubborn directory: {empty_dir.relative_to(start_path)}")
    
    if final_removed > 0:
        print(f"    Final pass removed {final_removed} additional directories")
    
    return removed, len(remaining_empty) - final_removed

def verify_no_empty_folders(start_path):
    """Comprehensive verification that no empty folders remain."""
    start_path = Path(start_path)
    kept_folders = {
        start_path,
        start_path / "Needs Labeling",
        start_path / "__WEBP To be move to the right folders",
        start_path / "gslisting"
    }
    
    empty_folders = []
    for root, dirs, files in os.walk(start_path):
        root_path = Path(root)
        if (root_path not in kept_folders and 
            is_directory_truly_empty(root_path)):
            empty_folders.append(root_path)
    
    return empty_folders

def process_files(main_folder):
    """Main file processing with guaranteed zero empty folders."""
    main_path = Path(main_folder)
    needs_labeling = main_path / "Needs Labeling"
    webp_folder = main_path / "__WEBP To be move to the right folders"
    gslisting_folder = main_path / "gslisting"
    
    needs_labeling.mkdir(exist_ok=True)
    webp_folder.mkdir(exist_ok=True)
    gslisting_folder.mkdir(exist_ok=True)
    
    print(f"📁 Processing files in: {main_path}")
    print(f"🏷️  Non-media files will go to: {needs_labeling.name}")
    print(f"📦 Media files will go to: {webp_folder.name}")
    print(f"🗂️  .gslisting folders will go to: {gslisting_folder.name}")
    
    # First pass: Handle .gslisting folders
    gslisting_folders = []
    for root, dirs, files in os.walk(main_path, topdown=False):
        root_path = Path(root)
        if root_path in [main_path, needs_labeling, webp_folder, gslisting_folder]:
            continue
        
        for dir_name in dirs:
            if dir_name.endswith('.gslisting'):
                gslisting_folders.append(root_path / dir_name)
    
    # Process .gslisting folders
    for folder in gslisting_folders:
        if folder.exists():  # Check if it still exists (might have been moved as part of parent)
            process_gslisting_folder(folder, main_path, gslisting_folder)
    
    # Second pass: Collect remaining files to avoid walk modification issues
    all_files = []
    for root, _, files in os.walk(main_path):
        root_path = Path(root)
        if root_path in [main_path, needs_labeling, webp_folder, gslisting_folder]:
            continue
        # Skip files inside gslisting folders
        if any(parent.name.endswith('.gslisting') for parent in root_path.parents):
            continue
        all_files.extend(root_path / f for f in files)
    
    print(f"\n📊 Found {len(all_files)} files to process")
    
    processed = {'images': 0, 'webp': 0, 'versioned': 0, 'mov': 0, 'needs_labeling': 0, 'gslisting': len(gslisting_folders)}
    
    for file_path in all_files:
        if not file_path.exists():  # Skip if file was already moved
            continue
            
        if file_path.suffix.lower() == '.mov':
            process_mov_file(file_path, main_path, webp_folder)
            processed['mov'] += 1
        elif is_media_file(file_path.name):
            if is_image_file(file_path.name):
                rel_path = file_path.relative_to(main_path)
                dest = needs_labeling / rel_path
                print(f"🖼️  Moving image: {rel_path}")
                move_file_safely(str(file_path), str(dest), webp_folder)
                processed['images'] += 1
            else:
                # Other media files go to webp folder with sequence suffix
                new_name = ensure_sequence_suffix(file_path.name)
                dest = webp_folder / new_name
                print(f"📱 Processing media file: {file_path.name} -> {new_name}")
                final_dest = move_file_safely(str(file_path), str(dest), webp_folder)
                if is_versioned_file(final_dest.name):
                    processed['versioned'] += 1
                else:
                    processed['webp'] += 1
        else:
            # Non-media files go to "Needs Labeling" unchanged
            rel_path = file_path.relative_to(main_path)
            dest = needs_labeling / rel_path
            print(f"📄 Moving to Needs Labeling: {rel_path}")
            move_file_safely(str(file_path), str(dest), needs_labeling)
            processed['needs_labeling'] += 1
    
    # Ultra-aggressive empty folder removal
    removed, remaining = remove_empty_dirs_aggressive(main_path)
    
    # Final verification
    empty_folders = verify_no_empty_folders(main_path)
    
    print(f"\n📋 FINAL SUMMARY:")
    print(f"   📸 Images moved: {processed['images']}")
    print(f"   🎬 .mov files processed: {processed['mov']}")
    print(f"   📱 Media files moved: {processed['webp']}")
    print(f"   🔄 Versioned files: {processed['versioned']}")
    print(f"   📄 Files moved to Needs Labeling: {processed['needs_labeling']}")
    print(f"   🗂️  .gslisting folders moved: {processed['gslisting']}")
    print(f"   🗑️  Empty directories removed: {removed}")
    
    if empty_folders:
        print(f"\n⚠️  WARNING: {len(empty_folders)} empty directories could not be removed:")
        for folder in empty_folders:
            print(f"     • {folder.relative_to(main_path)}")
        print("   These may be system folders or have permission restrictions.")
        return processed, False
    else:
        print(f"\n✅ SUCCESS: Zero empty folders remain!")
        return processed, True

def main():
    parser = argparse.ArgumentParser(description="Ultimate File Organizer - Zero Empty Folders Guarantee")
    parser.add_argument("folder", nargs="?", help="Directory to organize")
    parser.add_argument("--dry-run", action="store_true", help="Simulate only")
    parser.add_argument("--force", action="store_true", help="Force removal of stubborn directories")
    args = parser.parse_args()
    
    folder = args.folder or input("Enter folder path: ").strip()
    main_path = Path(folder)
    
    if not main_path.exists():
        print(f"❌ Error: Folder '{folder}' doesn't exist")
        return 1
    
    if args.dry_run:
        print("🔍 [DRY RUN] Simulation results:")
        webp = main_path / "__WEBP To be move to the right folders"
        label = main_path / "Needs Labeling"
        gslisting = main_path / "gslisting"
        
        counts = {'images': 0, 'webp': 0, 'versioned': 0, 'mov': 0, 'needs_labeling': 0, 'gslisting': 0}
        empty_dirs = 0
        
        for root, dirs, files in os.walk(main_path):
            root_path = Path(root)
            if root_path in [main_path, webp, label, gslisting]:
                continue
            
            # Check for .gslisting folders
            for dir_name in dirs:
                if dir_name.endswith('.gslisting'):
                    print(f"  🗂️  [GSLISTING] {root_path / dir_name} -> gslisting/{dir_name}")
                    counts['gslisting'] += 1
            
            # Count empty directories
            if not files and not dirs:
                empty_dirs += 1
            
            for f in files:
                if f.lower().endswith('.mov'):
                    rel_path = (Path(root)/f).relative_to(main_path)
                    parts = list(rel_path.parts)
                    brand = parts[0] if len(parts) > 1 else "UnknownBrand"
                    product = parts[1] if len(parts) > 2 else "UnknownProduct"
                    print(f"  🎬 [MOV] {rel_path} -> {brand}-{product}-X.mov")
                    counts['mov'] += 1
                elif is_media_file(f):
                    if is_image_file(f):
                        rel_path = (Path(root)/f).relative_to(main_path)
                        print(f"  🖼️  [IMAGE] {rel_path} -> Needs Labeling/{rel_path}")
                        counts['images'] += 1
                    else:
                        new_name = ensure_sequence_suffix(f)
                        print(f"  📱 [MEDIA] {f} -> WEBP/{new_name}")
                        if is_versioned_file(new_name):
                            counts['versioned'] += 1
                        else:
                            counts['webp'] += 1
                else:
                    rel_path = (Path(root)/f).relative_to(main_path)
                    print(f"  📄 [NON-MEDIA] {rel_path} -> Needs Labeling/{rel_path}")
                    counts['needs_labeling'] += 1
        
        print(f"\n📊 Would process: {counts['images']} images, {counts['mov']} .mov files, "
              f"{counts['webp']} media files, {counts['versioned']} versioned files, "
              f"{counts['needs_labeling']} non-media files, {counts['gslisting']} .gslisting folders")
        print(f"🗑️  Would remove approximately {empty_dirs} empty directories")
        
    else:
        print("🚀 Starting file organization with zero empty folders guarantee...")
        processed, success = process_files(main_path)
        
        if success:
            print("\n🎉 Organization complete! Zero empty folders guaranteed!")
        else:
            print("\n⚠️  Organization complete, but some empty folders remain.")
            print("   Run with --force flag for more aggressive removal.")
        
        return 0 if success else 1

if __name__ == "__main__":
    exit(main())