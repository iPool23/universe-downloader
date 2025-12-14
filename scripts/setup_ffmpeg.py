import os
import zipfile
import urllib.request
from pathlib import Path
import shutil

# Corrected base dir (one level up from scripts)
BASE_DIR = Path(__file__).parent.parent
BIN_DIR = BASE_DIR / "bin"
TEMP_ZIP = BASE_DIR / "ffmpeg.zip"

FFMPEG_URL = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"

def setup_ffmpeg():
    print(f"Downloading FFmpeg from {FFMPEG_URL}...")
    try:
        urllib.request.urlretrieve(FFMPEG_URL, TEMP_ZIP)
        print("Download complete.")
        
        print("Extracting...")
        with zipfile.ZipFile(TEMP_ZIP, 'r') as zip_ref:
            zip_ref.extractall(BASE_DIR)
        
        # Move bin content to project root bin
        extracted_dirs = [d for d in BASE_DIR.iterdir() if d.is_dir() and d.name.startswith("ffmpeg-master")]
        if extracted_dirs:
            ffmpeg_dir = extracted_dirs[0]
            bin_source = ffmpeg_dir / "bin"
            
            if not BIN_DIR.exists():
                BIN_DIR.mkdir()
            
            for item in bin_source.iterdir():
                shutil.copy2(item, BIN_DIR / item.name)
            
            # Cleanup
            shutil.rmtree(ffmpeg_dir)
            
        if TEMP_ZIP.exists():
            os.remove(TEMP_ZIP)
            
        print(f"FFmpeg setup complete. Executable is in: {BIN_DIR}")
        
    except Exception as e:
        print(f"Error setting up FFmpeg: {e}")
        if TEMP_ZIP.exists():
            os.remove(TEMP_ZIP)

if __name__ == "__main__":
    setup_ffmpeg()
