## FS3D Patch Tool

Generate [luma](https://github.com/AuroraWright/Luma3DS) code patches for Flipnote Studio 3D which allow the app to connect to a custom Flipnote Gallery World replacement server. Currently used to generate patches for [Kaeru Gallery](https://kaeru.world/kw).

### Features

* No source files necessary
* Out-of-the-box support for the latest version of FS3D accross all regions (EUR/USA 1.0.1, JPN 1.3.3)
* Translation file patches for text replacement, since Nintendo never finished translating strings for the online gallery feature.
* Replaces the Flipnote Gallery World / DSi Gallery URL with a custom server URL
* Patches out the NASC server check, since Nintendo's NASC server no longer officially supports FS3D
* Replaces SSL certificates with your own .DER format certs

### Usage

1. Download this repo to your local machine.
2. Install Python -- all scripts were tested on Python 3.7.1 but should work on 3.5 +
3. Download and compile this [multiplatform version of `blz.c`](https://gist.github.com/thejsa/705a59a6c63989f752a32ce94b1849aa) and place it in the tool's root directory. You may need to adjust the `BLZ_PATH` variable on line 19 of `build.py` depending on your platform.
4. Tweak `config.ini` to your needs, make sure you pay attention to the file comments.
5. Generate the patch by running `python3 build.py`. This script will create a new `luma` folder which contains your patches
6. Drop the `luma` folder into your 3DS' SD card root, [enable luma's game patching feature](https://github.com/AuroraWright/Luma3DS/wiki/Optional-features) and enjoy your patched version of Flipnote Studio 3D!

### Todo

* Tweak version strings, http headers, etc (?)
* Texture replacements (?)

### Credits

* [Shutterbug2000](https://github.com/shutterbug2000) - Original code patch
* [Jaames](https://github.com/jaames) - Japanese region port, Python tooling