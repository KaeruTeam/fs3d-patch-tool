## FS3D Patch Tool

Generate [luma](https://github.com/AuroraWright/Luma3DS) code patches for Flipnote Studio 3D which allow the app to connect to a custom Flipnote Gallery World replacement server. Currently used to generate patches for [Kaeru Gallery](https://kaeru.world/kw).

### Features

* No source files necessary
* Out-of-the-box support for the latest version of FS3D accross all regions
* Replaces the Flipnote Gallery World / DSi Gallery URL with a custom server URL
* Patches out the NASC server check, since Nintendo's NASC server no longer officially supports FS3D
* Replaces SSL certificates with your own .DER format certs

### Usage

1. Install Python -- all scripts were tested on Python 3.7.1 but should work on 3.5 +
2. Tweak `config.ini` to your needs, make sure you pay attention to the file comments
3. Generate the patch by running `python3 generate_patch.py`. This script will create a new `luma` folder which contains your patches.
4. Drop the `luma` into your 3DS' SD card root, [enable luma's game patching feature](https://github.com/AuroraWright/Luma3DS/wiki/Optional-features) and enjoy your patched version Flipnote Studio 3D!

### Todo

* Generation of .msbt translation files from .json (in progress)
* Tweak version strings, http headers, etc (?)
* Texture replacements (?)

### Credits

* [Shutterbug2000](https://github.com/shutterbug2000) - Original code patch
* [Jaames](https://github.com/james) - Japanese region port, Python tooling