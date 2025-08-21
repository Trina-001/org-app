import os
import sys
import subprocess
from pathlib import Path
import argparse
import time

def run_script(script_path, folder_path, script_name):
    """Run a Python script with the given folder path"""
    print(f"\n{'='*60}")
    print(f"🚀 RUNNING {script_name.upper()}")
    print(f"{'='*60}")
    
    try:
        # Import and run split.py functions
        if script_name == "SPLIT":
            # Import the functions from split.py
            sys.path.insert(0, os.path.dirname(script_path))
            import split
            
            # Run the main processing function from split.py
            processed, success = split.process_files(folder_path)
            
            if success:
                print(f"✅ {script_name} completed successfully!")
                return True
            else:
                print(f"⚠️ {script_name} completed with warnings!")
                return True  # Continue to next script even with warnings
                
        elif script_name == "ORGANIZE":
            # Import and run organize.py functions
            sys.path.insert(0, os.path.dirname(script_path))
            import organize
            
            # Find the WEBP folder created by split.py
            webp_folder_path = Path(folder_path) / "__WEBP To be move to the right folders"
            
            if not webp_folder_path.exists():
                print(f"❌ Error: WEBP folder not found at {webp_folder_path}")
                print("Make sure split.py ran successfully first.")
                return False
            
            # Run the organization function from organize.py
            success = organize.organize_webp_files(str(webp_folder_path))
            
            if success:
                print(f"✅ {script_name} completed successfully!")
                return True
            else:
                print(f"❌ {script_name} failed!")
                return False
                
    except ImportError as e:
        print(f"❌ Error importing {script_name.lower()}.py: {e}")
        print(f"Make sure {script_name.lower()}.py is in the same directory as this script.")
        return False
    except Exception as e:
        print(f"❌ Error running {script_name}: {str(e)}")
        return False

def find_script_files():
    """Find split.py and organize.py in the current directory"""
    current_dir = Path(__file__).parent
    
    split_path = current_dir / "split.py"
    organize_path = current_dir / "organize.py"
    
    missing_files = []
    if not split_path.exists():
        missing_files.append("split.py")
    if not organize_path.exists():
        missing_files.append("organize.py")
    
    if missing_files:
        print(f"❌ Error: Missing required files: {', '.join(missing_files)}")
        print("Make sure split.py and organize.py are in the same directory as this script.")
        return None, None
    
    return str(split_path), str(organize_path)

def validate_folder(folder_path):
    """Validate that the folder exists and is accessible"""
    path = Path(folder_path)
    
    if not path.exists():
        print(f"❌ Error: Folder '{folder_path}' doesn't exist")
        return False
    
    if not path.is_dir():
        print(f"❌ Error: '{folder_path}' is not a directory")
        return False
    
    # Check if we have read/write permissions
    if not os.access(path, os.R_OK | os.W_OK):
        print(f"❌ Error: No read/write permissions for '{folder_path}'")
        return False
    
    return True

def print_summary(folder_path):
    """Print a summary of the expected folder structure after processing"""
    path = Path(folder_path)
    
    print(f"\n{'='*60}")
    print("📋 EXPECTED FOLDER STRUCTURE AFTER PROCESSING")
    print(f"{'='*60}")
    print(f"📁 {path.name}/")
    print("  ├── 📁 Needs Labeling/")
    print("  │   └── (Image files and non-media files)")
    print("  ├── 📁 __WEBP To be move to the right folders/")
    print("  │   └── 📁 [Brand Names]/")
    print("  │       └── 📁 [Product Codes]/")
    print("  │           ├── 📁 WEBP/ (organized webp files)")
    print("  │           ├── 📁 JPEG/ (organized jpeg/png files)")
    print("  │           ├── 📁 Video/ (organized video files)")
    print("  │           └── 📁 Old Images/ (replaced files)")
    print("  └── 📁 gslisting/")
    print("      └── (Moved .gslisting folders)")
    print()

def main():
    parser = argparse.ArgumentParser(
        description="File Organization Pipeline - Runs split.py then organize.py",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python pipeline.py /path/to/folder
  python pipeline.py "C:\\Users\\Documents\\Photos"
  python pipeline.py --dry-run /path/to/folder

This script will:
1. Run split.py to organize files into categories
2. Run organize.py to organize WEBP files by brand/product
        """
    )
    
    parser.add_argument("folder", nargs="?", help="Directory to organize")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without actually doing it")
    parser.add_argument("--skip-organize", action="store_true", help="Only run split.py, skip organize.py")
    parser.add_argument("--organize-only", action="store_true", help="Only run organize.py, skip split.py")
    
    args = parser.parse_args()
    
    # Get folder path
    folder_path = args.folder
    if not folder_path:
        folder_path = input("Enter the folder path to organize: ").strip().strip('"')
    
    # Validate folder
    if not validate_folder(folder_path):
        return 1
    
    # Find required script files
    split_path, organize_path = find_script_files()
    if not split_path or not organize_path:
        return 1
    
    print(f"🎯 TARGET FOLDER: {folder_path}")
    print(f"📄 SPLIT SCRIPT: {split_path}")
    print(f"📄 ORGANIZE SCRIPT: {organize_path}")
    
    if args.dry_run:
        print("\n🔍 DRY RUN MODE - No files will be moved")
        print("\nThis would run:")
        if not args.organize_only:
            print("1. split.py - Organize files into categories")
        if not args.skip_organize:
            print("2. organize.py - Organize WEBP files by brand/product")
        print_summary(folder_path)
        return 0
    
    # Confirm with user
    print_summary(folder_path)
    
    if not args.organize_only and not args.skip_organize:
        confirm = input("🤔 Run both split.py and organize.py on this folder? (y/N): ").strip().lower()
    elif args.organize_only:
        confirm = input("🤔 Run organize.py only on this folder? (y/N): ").strip().lower()
    elif args.skip_organize:
        confirm = input("🤔 Run split.py only on this folder? (y/N): ").strip().lower()
    
    if confirm not in ['y', 'yes']:
        print("❌ Operation cancelled by user")
        return 1
    
    # Record start time
    start_time = time.time()
    
    # Run the scripts
    success = True
    
    if not args.organize_only:
        # Step 1: Run split.py
        if not run_script(split_path, folder_path, "SPLIT"):
            print("❌ Split phase failed. Stopping pipeline.")
            return 1
    
    if not args.skip_organize:
        # Step 2: Run organize.py
        if not run_script(organize_path, folder_path, "ORGANIZE"):
            print("❌ Organize phase failed.")
            success = False
    
    # Calculate total time
    total_time = time.time() - start_time
    minutes = int(total_time // 60)
    seconds = int(total_time % 60)
    
    print(f"\n{'='*60}")
    if success:
        print("🎉 PIPELINE COMPLETED SUCCESSFULLY!")
    else:
        print("⚠️ PIPELINE COMPLETED WITH ERRORS!")
    print(f"⏱️ Total processing time: {minutes}m {seconds}s")
    print(f"{'='*60}")
    
    return 0 if success else 1

# app/merge.py (modified for web use)
import os
import sys
from pathlib import Path
import argparse
import time

# ... (keep all the existing functions from merge.py)

def main_web(folder_path):
    """Web version of main function that takes folder path as argument"""
    # Validate folder
    if not validate_folder(folder_path):
        return 1
    
    # Find required script files
    split_path, organize_path = find_script_files()
    if not split_path or not organize_path:
        return 1
    
    print(f"🎯 TARGET FOLDER: {folder_path}")
    
    # Record start time
    start_time = time.time()
    
    # Run the scripts - both organize and split
    success = True
    
    # Step 1: Run split.py
    if not run_script(split_path, folder_path, "SPLIT"):
        print("❌ Split phase failed. Stopping pipeline.")
        return 1
    
    # Step 2: Run organize.py
    if not run_script(organize_path, folder_path, "ORGANIZE"):
        print("❌ Organize phase failed.")
        success = False
    
    # Calculate total time
    total_time = time.time() - start_time
    minutes = int(total_time // 60)
    seconds = int(total_time % 60)
    
    print(f"\n{'='*60}")
    if success:
        print("🎉 PIPELINE COMPLETED SUCCESSFULLY!")
    else:
        print("⚠️ PIPELINE COMPLETED WITH ERRORS!")
    print(f"⏱️ Total processing time: {minutes}m {seconds}s")
    print(f"{'='*60}")
    
    return 0 if success else 1

if __name__ == "__main__":
    # Original main function remains for command line use
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user (Ctrl+C)")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {str(e)}")
        sys.exit(1)