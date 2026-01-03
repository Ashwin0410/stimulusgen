import re
import unicodedata
from pathlib import Path


def sanitize_filename(name: str) -> str:
    """
    Convert string to safe filename.
    Removes special characters, replaces spaces with underscores.
    """
    # Normalize unicode
    name = unicodedata.normalize("NFKD", name)
    name = "".join(c for c in name if not unicodedata.combining(c))
    
    # Replace spaces and special chars
    name = re.sub(r"[^\w\s\-.]", "", name)
    name = re.sub(r"\s+", "_", name)
    name = re.sub(r"_+", "_", name)
    name = name.strip("_")
    
    return name


def get_next_id(prefix: str, existing_ids: list[str]) -> str:
    """
    Generate next sequential ID with given prefix.
    Example: prefix="STIM" with existing ["STIM_001", "STIM_002"] returns "STIM_003"
    """
    max_num = 0
    pattern = re.compile(rf"^{prefix}_(\d+)$")
    
    for existing in existing_ids:
        match = pattern.match(existing)
        if match:
            num = int(match.group(1))
            max_num = max(max_num, num)
    
    return f"{prefix}_{max_num + 1:03d}"


def generate_output_filename(stimulus_id: str, extension: str = "mp3") -> str:
    """Generate output filename for a stimulus."""
    safe_id = sanitize_filename(stimulus_id)
    return f"{safe_id}.{extension}"


def extract_track_name(filepath: str | Path) -> str:
    """Extract clean track name from filepath."""
    path = Path(filepath)
    name = path.stem
    
    # Remove common prefixes like "Audiosocket_12345678_"
    name = re.sub(r"^Audiosocket_\d+_", "", name)
    
    # Replace underscores with spaces
    name = name.replace("_", " ")
    
    return name.strip()


def generate_track_id(filepath: str | Path) -> str:
    """Generate a short ID for a track based on its path."""
    import hashlib
    path_str = str(filepath)
    return hashlib.md5(path_str.encode()).hexdigest()[:12]