# Introduction
This (kludgy) script will repackage the precompiled [GDAL](http://www.gdal.org) library and python bindings wheels from Cristoph Gohlke's [Unofficial Windows Binaries for Python Extension Packages](http://www.lfd.uci.edu/~gohlke/pythonlibs/#gdal) and bundle in the ECW and MrSID plugins extracted from the [GIS Internals](http://www.gisinternals.com) MSVC 2008 installers.

It generates platform wheels for Windows 32 and 64 bit Python 2.7.

The script requires the wheels and MSVC 2008 MSIs to be downloaded and placed in the same directory as the script.  For the wheels I published to BinStar, I used the GIS Internals [stable branch](http://www.gisinternals.com/stable.php) installers as the releases were not up to date.

If you're just looking for an easy way to install GDAL with the ECW and MrSID plugins, try:
```pip install -i https://pypi.anaconda.org/luke/simple gdal```

# Requirements
 - setuptools >= 18.4
 - wheel

# Usage
    python repackage.py

