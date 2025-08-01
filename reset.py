# reset.py
"""
This script cleans the project workspace by deleting auto-generated files
and folders, restoring the project to a clean state.

This allows for a fresh simulation run without any artifacts from previous runs.
"""
import os
import shutil

def clean_workspace():
    """
    Finds and deletes specified generated files and directories.
    """
    # Get the root directory of the project (where this script is located)
    project_root = os.path.dirname(os.path.abspath(__file__))
    print(f"Starting cleanup in project root: {project_root}\n")

    # --- Configuration: Define what to delete ---
    # Folders to delete recursively
    folders_to_delete = ["__pycache__", ".pytest_cache", "build", "dist", ".tox"]
    
    # Files with these extensions to delete
    file_extensions_to_delete = [".pyc", ".log", ".tmp"]

    # --- Deletion Logic ---
    deleted_count = 0
    for root, dirs, files in os.walk(project_root, topdown=True):
        
        # 1. Delete specified folders
        # We modify dirs in-place to prevent os.walk from traversing into them
        dirs_to_remove = [d for d in dirs if d in folders_to_delete]
        for dirname in dirs_to_remove:
            folder_path = os.path.join(root, dirname)
            try:
                print(f"Deleting folder: {folder_path}")
                shutil.rmtree(folder_path)
                dirs.remove(dirname) # Stop os.walk from trying to enter it
                deleted_count += 1
            except OSError as e:
                print(f"Error deleting {folder_path}: {e}")

        # 2. Delete specified file types
        for filename in files:
            if any(filename.endswith(ext) for ext in file_extensions_to_delete):
                file_path = os.path.join(root, filename)
                try:
                    print(f"Deleting file:   {file_path}")
                    os.remove(file_path)
                    deleted_count += 1
                except OSError as e:
                    print(f"Error deleting {file_path}: {e}")

    if deleted_count == 0:
        print("\nWorkspace is already clean. No files or folders to delete.")
    else:
        print(f"\nCleanup complete. Removed {deleted_count} items.")
    
    print("Agent state is reset by re-running main.py, which loads fresh data from initial_profiles.json.")


if __name__ == "__main__":
    clean_workspace() 