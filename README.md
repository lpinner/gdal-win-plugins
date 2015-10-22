# Introduction
This (kludgy) script will repackage the precompiled [GDAL](http://www.gdal.org) library and python bindings wheels from Cristoph Gohlke's [Unofficial Windows Binaries for Python Extension Packages](http://www.lfd.uci.edu/~gohlke/pythonlibs/#gdal) which is built against numpy 1.9 or the [GIS Internals](http://www.gisinternals.com) MSVC 2008 installers  which is built against numpy 1.7.  Any [GIS Internals](http://www.gisinternals.com) MSVC 2008 plugin (e.g. ECW and MrSID) installers will be extracted and bundled into the output wheel.

It generates platform wheels for Windows 32 and 64 bit Python 2.7.

The script requires the wheels and MSVC 2008 MSIs to be downloaded and placed in the same directory as the script.  For the wheels I published to BinStar, I used the GIS Internals [stable branch](http://www.gisinternals.com/stable.php) installers as the releases were not up to date.

If you're just looking for an easy way to install GDAL with the ECW and MrSID plugins, try:

# If you have numpy 1.7 installed (i.e an ArcGIS 10.1 or 10.2 python installation)
```pip install -i https://pypi.anaconda.org/luke/channel/np17/simple gdal```

# If you have numpy 1.9 installed
```pip install -i https://pypi.anaconda.org/luke/channel/np19/simple gdal```

# Requirements
 - setuptools >= 18.4
 - wheel

# Usage
    python repackage.py [--msi]

