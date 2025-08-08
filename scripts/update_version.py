# scripts/update_version.py
import subprocess

def get_version():
    try:
        # Get latest Git tag (e.g., "v1.0.0")
        tag = subprocess.check_output(
            ["git", "describe", "--tags", "--abbrev=0"],
            stderr=subprocess.DEVNULL,
            shell=True
        ).decode().strip()
        return tag[1:] if tag.startswith("v") else tag
    except:
        return "0.0.0-dev"  # Fallback

# Update version.txt
with open("version.txt", "w") as f:
    f.write(get_version())
