# AND!XOR DC33 Badge Tool

## Overview
The AND!XOR DC33 Badge Tool is a Python-based utility that allows you to extract and modify the contents of an AND!XOR DC33 badge firmware binary. It can pull out embedded files, replace GIF animations, and rebuild the firmware so it can be re-uploaded to the badge using `picotool`. This makes customizing badge visuals simple without needing to rebuild the original firmware from source.

## Features
- Extract embedded files from badge firmware  
- Patch new GIF animations  
- Generate a new flashable binary  
- Lightweight Python script with a simple GUI

## Requirements
- Python 3.8 or newer  
- `picotool` installed on your system  
- `littlefs-python` and `Pillow` installed via `requirements.txt`

### Install Python dependencies
```bash
pip install -r requirements.txt
```

## Usage

### 1. Place the Firmware Binary
If you have your own badge, you can extract and back up its firmware before making any changes. Connect the badge and run:

```bash
picotool save -a badge.bin -t bin -f
```

This will save the current firmware from your device into a file named `badge.bin`.

If you don’t have a badge or prefer to test first, there is an example firmware already included in the `Example Binary` folder called `bender_ctf_original.bin` that you can use instead.

### 2. Run the Patcher Tool
Place your firmware file (for example, `badge.bin`) into the same directory as `patcher_gui.py`, then run the patcher tool:

```bash
python3 patcher_gui.py
```

This will open the GUI interface where you can extract files from the binary, patch new GIFs, or replace existing assets.

### 3. Flash the New Firmware
Once patching is complete, a new binary file (for example, `badge_patched.bin`) will be created. Flash it back onto your badge with the following command:

```bash
picotool load -f badge_patched.bin
```

## Notes
- `littlefs-python` is used to read and write the badge’s internal filesystem.  
- `Pillow` is required for image and GIF manipulation.  
- Always back up your original firmware before making changes.  
- `picotool` must be installed separately to flash the firmware.

## Thanks & Credits

A huge thank you to **AND!XOR** for creating such a unique, creative, and fun badge experience. Their work has inspired countless hardware enthusiasts and badge hackers to explore, experiment, and learn. This tool is not affiliated with or endorsed by AND!XOR — it was built purely for educational purposes and to extend the incredible work they’ve already done.

All credit for the original badge hardware, firmware, and concept goes to the AND!XOR team. You can find their official badge repository here:

[ANDnXOR_DC33_Badge](https://github.com/ANDnXOR/ANDnXOR_DC33_Badge)

If you’re interested in other walkthroughs, examples, or projects involving this badge, check out their repository and the broader AND!XOR community for more resources and inspiration.


## License
This tool is provided as-is for educational and personal use. Use at your own risk.
