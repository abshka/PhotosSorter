# PhotosSorter

🔍 **Automatic photo and video organizer** that sorts files by date using EXIF metadata and handles video thumbnails.

## Features

- 📸 **Photo sorting** - Organizes images by EXIF date into year/month/day folders
- 🎥 **Video support** - Handles video files with their thumbnail (.thm) files
- 🔗 **MPG/THM merging** - Automatically embeds .thm thumbnails into .mpg videos and removes .thm files
- 🛡️ **Safe processing** - Dry-run mode to preview changes before execution
- 🚀 **Fast processing** - Multi-threaded with progress tracking
- 📝 **Detailed logging** - Complete operation history and error tracking

## Quick Start

1. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

2. **Create configuration**

   ```bash
   cp config.yaml.example config.yaml
   ```

3. **Edit config.yaml**

   ```yaml
   source_directory: "/path/to/your/photos"
   date_format: "YYYY/MM/DD"
   ```

4. **Preview changes** (safe)

   ```bash
   python run.py --dry-run
   ```

5. **Run sorting**
   ```bash
   python run.py
   ```

## Supported Formats

**Images:** JPEG, PNG, TIFF, RAW (CR2, NEF, ARW, DNG)
**Videos:** MPG, MP4, AVI, MOV, MKV
**Thumbnails:** THM (automatically merged with MPG videos)

## Example Output Structure

```
Photos/
├── 2024/
│   ├── 01/
│   │   ├── 15/
│   │   │   ├── IMG_001.jpg
│   │   │   └── VIDEO_001.mpg  # THM thumbnail embedded, .thm deleted
│   │   └── 20/
│   │       └── IMG_002.jpg
│   └── 02/
│       └── 14/
│           └── valentine.mp4
└── Unknown_Date/
    └── no_exif.jpg
```

## Command Line Options

```bash
python run.py                           # Normal run with config
python run.py --dry-run                 # Preview only (safe)
python run.py --source /path/to/photos  # Custom source folder
python run.py --scan /path/to/photos    # Show statistics only
python run.py --test-exif photo.jpg     # Check EXIF data
python run.py --no-confirm              # Skip confirmation
```

## Configuration

Key settings in `config.yaml`:

```yaml
# Basic settings
source_directory: "/path/to/photos"
target_directory: null # null = organize in source folder
date_format: "YYYY/MM/DD"

# Processing
processing:
  move_files: true # true=move, false=copy
  duplicate_handling: "rename" # skip, rename, overwrite

# Video processing
video:
  enabled: true
  mpg_processing:
    enable_merging: true # Merge MPG+THM files
    delete_thm_after_merge: true # Remove THM after merge

# Safety
safety:
  dry_run: false
  confirm_before_start: true
```

## Prerequisites

For video processing (MPG/THM merging), install ffmpeg:

```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# Arch Linux
sudo pacman -S ffmpeg

# macOS
brew install ffmpeg

# Windows
# Download from https://ffmpeg.org/
# Or use choco
choco install ffmpeg
```

## Troubleshooting

**No EXIF date found**: Files moved to `Unknown_Date` folder
**Permission denied**: Check folder permissions
**MPG merging fails**: Ensure ffmpeg is installed and accessible
**Too many duplicates**: Adjust `duplicate_handling` in config

**Debug a specific file**:

```bash
python run.py --test-exif problematic_file.jpg
```

## Safety First

- ⚠️ **Always backup your photos** before first use
- 🧪 **Test with `--dry-run`** to preview changes
- 📁 **Start with a small folder** to verify behavior
- 📋 **Check logs** in `logs/photos_sorter.log`

## License

MIT License - feel free to use and modify.
