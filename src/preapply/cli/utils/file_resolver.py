"""File path resolution utilities for CLI."""

from pathlib import Path


def resolve_file_path(file_path: str) -> Path:
    """
    Resolve file path, checking if it exists in the current directory.
    
    Only searches the current directory. Does not search subdirectories.
    
    Args:
        file_path: User-provided file path or name
        
    Returns:
        Resolved Path object
        
    Raises:
        FileNotFoundError: If file cannot be found in current directory
    """
    # Try to resolve the path
    path = Path(file_path)
    
    # If it's an absolute path, use it as-is
    if path.is_absolute():
        if not path.exists():
            raise FileNotFoundError(
                f"File not found: {file_path}. Please check the file path and try again."
            )
        return path.resolve()
    
    # For relative paths, check in current directory
    current_dir = Path.cwd()
    resolved_path = (current_dir / path).resolve()
    
    if not resolved_path.exists():
        raise FileNotFoundError(
            f"File not found: {file_path}. Please check the file path and try again."
        )
    
    if not resolved_path.is_file():
        raise FileNotFoundError(
            f"Path is not a file: {file_path}. Please provide a valid file path."
        )
    
    return resolved_path
