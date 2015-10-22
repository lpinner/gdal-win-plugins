# -*- coding: utf-8 -*-
# Copyright (c) 2015 Luke Pinner
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

'''
    Kludgy setup.py based script to repackage Christoph Gohlke's prebuilt
    GDAL wheels from www.lfd.uci.edu/~gohlke/pythonlibs/#gdal
    and the Tamas Szekeres' ECW and MrSID plugin MSIs from www.gisinternals.com
    into a single wheel.

    Only files required to use the python bindings are included,
    the executables (i.e gdalinfo etc.) and python scripts (i.e gdal_calc.py)
    are not.
'''

## Imports
# Always prefer setuptools over distutils
from setuptools import setup
from distutils.dir_util import copy_tree
from codecs import open
import os,sys
import argparse
import fnmatch
import glob
import json
import shutil
import subprocess
import tempfile
import time
import wheel.install
import zipfile

INITTXT = """# __init__ for osgeo package.
import os
try:
    os.environ['GDAL_DATA'] = os.path.join(os.path.dirname(__file__), 'gdal-data')
    os.environ['GDAL_DRIVER_PATH'] = os.path.join(os.path.dirname(__file__), 'gdalplugins')
    os.environ['PATH'] = os.path.dirname(__file__) + ';' +os.environ['PATH']
except Exception:
    pass
"""

def err(f, p, e):
    import warnings,traceback
    warnings.warn('Unable to delete %s\n%s'%(p,traceback.format_exc().splitlines()[-1]))

def copytree(src, dst, symlinks=False, ignore=None):
    ''' http://stackoverflow.com/a/12514470/737471
        CC BY-SA 3.0
    '''
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            shutil.copytree(s, d, symlinks, ignore)
        else:
            shutil.copy2(s, d)


def create_platform_wheel(inwhl, outwhl, platname, version):

        #Ugly kludge as I can't figure out how to get setup() to
        #create a platform wheel from a precompiled build
        zin=zipfile.ZipFile(inwhl, 'r')
        whl = zin.open('%s-%s.dist-info/WHEEL'%(name,version)).read()
        whl = whl.replace('Root-Is-Purelib: true','Root-Is-Purelib: false')
        whl = whl.replace('Tag: py2-none-any','Tag: cp27-none-%s'%platname)
        info = zipfile.ZipInfo('%s-%s.dist-info/WHEEL'%(name,version))
        info.date_time = time.localtime(time.time())[:6]
        info.compress_type = zipfile.ZIP_DEFLATED
        zout = zipfile.ZipFile(outwhl, 'w')
        for item in zin.infolist():
            buffer = zin.read(item.filename)
            if (item.filename[-5:] != 'WHEEL'):
                zout.writestr(item, buffer)
            else:
                zout.writestr(info, whl)

        zout.close()
        zin.close()


def extract_wheel(whl, outdir):
    whl = wheel.install.WheelFile(whl)
    locs = {}
    for key in ('purelib', 'platlib', 'scripts', 'headers', 'data'):
        locs[key] = os.path.join(outdir, key)
        os.mkdir(locs[key])
    whl.install(overrides=locs)
    return whl


def extract_msi(msi, outdir):
    msipath = os.path.abspath(msi)
    outpath = os.path.join(outdir, os.path.splitext(msi)[0])
    cmd = 'msiexec /a "%s" /qn TARGETDIR="%s"'%(msipath, outpath)
    subprocess.check_call(cmd)
    return outpath


def update_init(filepath):
    #Set the env vars
    init = open(filepath).read()
    init = init.replace("# __init__ for osgeo package.", INITTXT)
    init = init.replace('\r','')
    open(filepath, 'w').write(init)


def repackage_wheel(whl, msis, platname, curdir, distdir, setupargs):
    try:

        tmpdir = os.path.abspath(
            tempfile.mkdtemp(prefix='gdal', dir=curdir))

        platlib = os.path.join(tmpdir,'platlib')
        libdir = os.path.join(platlib,'osgeo')

        #Unpack the wheel and move data into platlib
        whl = extract_wheel(whl, tmpdir)
        copy_tree(os.path.join(tmpdir,'data','Lib','site-packages','osgeo'), libdir)

        #Some metadata
        metadata = json.load(open(os.path.join(platlib,whl.distinfo_name,'metadata.json')))
        shutil.rmtree(os.path.join(platlib,whl.distinfo_name))
        version=metadata['version']

        #Set the env vars
        update_init(os.path.join(libdir,'__init__.py'))

        #Unpack the MSIs
        for msi in msis:
            outpath = extract_msi(msi, tmpdir)
            copy_tree(os.path.join(outpath, 'PFiles','GDAL'), libdir)

        #Build the wheel
        os.chdir(platlib)
        setup(
            version=version,
            py_modules = [f[:-3] for f in glob.glob('*.py')],
            package_dir={'':os.path.join(tmpdir,'platlib')},
            packages=['osgeo'],
            package_data={'': ['gdalserver.exe','*.dll', '*.pyd',
                            'gdalplugins/*', 'gdalplugins.disabled/*',
                            'license/*', 'data/gdal/*']},
            **setupargs
        )
        inwhl = os.path.join(platlib,'dist','%s-%s-py2-none-any.whl'%(name,version))
        outwhl = os.path.join(distdir,'%s-%s-cp27-none-%s.whl'%(name,version,platname))
        create_platform_wheel(inwhl, outwhl, platname, version)

    finally:
        #Cleanup
        os.chdir(curdir)
        shutil.rmtree(tmpdir, onerror=err)


def repackage_msi(pymsi, msis, platname, name, curdir, distdir, setupargs):
    try:

        version = pymsi.split('-')[1].split('.w')[0]

        tmpdir = os.path.abspath(
            tempfile.mkdtemp(prefix='gdal', dir=curdir))

        #Unpack the MSIs
        outpath = extract_msi(pymsi, tmpdir)
        pkgdir = os.path.join(outpath, 'Lib', 'site-packages')
        libdir = os.path.join(pkgdir, 'osgeo')
        for msi in msis:
            outpath = extract_msi(msi, tmpdir)
            copy_tree(os.path.join(outpath, 'PFiles','GDAL'), libdir)

        #Set the env vars
        update_init(os.path.join(libdir,'__init__.py'))

        #Clean out the scripts
        pyds = glob.glob(os.path.join(libdir,'_*.pyd'))
        keepers = [os.path.join(libdir, os.path.basename(f)[1:-1]) for f in pyds] + [os.path.join(libdir,'__init__.py')]
        pys = [f for f in glob.glob(os.path.join(libdir,'*.py')) if f not in keepers]
        for py in pys: os.unlink(py)

        #Build the wheel
        os.chdir(pkgdir)
        setup(
            version=version,
            py_modules = [f[:-3] for f in glob.glob('*.py')],
            package_dir={'':pkgdir},
            packages=['osgeo'],
            package_data={'': ['gdalserver.exe','*.dll', '*.pyd',
                               'gdalplugins/*', 'license/*', 'gdal-data/*']},
            **setupargs
        )
        inwhl = os.path.join(pkgdir,'dist','%s-%s-py2-none-any.whl'%(name,version))
        outwhl = os.path.join(distdir,'%s-%s-cp27-none-%s.whl'%(name,version,platname))
        create_platform_wheel(inwhl, outwhl, platname, version)

    finally:
        #Cleanup
        os.chdir(curdir)
        shutil.rmtree(tmpdir, onerror=err)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-m','--msi', action='store_true',
                        help="Looks for GDAL core in GIS Internals MSI, default is to look for wheels.")
    args = parser.parse_args()

    setupargs = json.load(open(__file__.replace('.py','.json')))
    name = setupargs['name'].replace('-', '_')
    curdir = os.path.dirname(os.path.abspath(__file__))

    if args.msi:
        distdir = os.path.join(curdir,'dist-np17') #gisinternals built against numpy 1.7x
    else:
        distdir = os.path.join(curdir,'dist-np19') #Gohlke's built against numpy 1.9x
    if not os.path.exists(distdir): os.mkdir(distdir)

    #This setup.py is only for building wheels
    del sys.argv[1:]
    sys.argv.append('bdist_wheel')

    for platname in ('win32','win_amd64'):
        arch = platname[-2:]
        if args.msi:
            # MSIs from http://www.gisinternals.com
            try:pymsi = glob.glob('GDAL-*.win*%s-py*.msi'%arch)[0]
            except IndexError:continue

            if arch == '64':
                msis = glob.glob('gdal-*-1500-x64-*.msi')
            else:
                msis = [f for f in glob.glob('gdal-*-1500-*.msi') if not '64' in f]

            repackage_msi(pymsi, msis, platname, name, curdir, distdir, setupargs)
        else:
            # Wheels from http://www.lfd.uci.edu/~gohlke/pythonlibs/#gdal
            try:whl = glob.glob('GDAL-*-cp27-*-win*%s.whl'%arch)[0]
            except IndexError:continue

            # MSIs from http://www.gisinternals.com
            if arch == '64':
                msis = [f for f in glob.glob('gdal-*-1500-x64-*.msi') if not 'core' in f]
            else:
                msis = [f for f in glob.glob('gdal-*-1500-*.msi') if not 'x64' in f and not 'core' in f]

            repackage_wheel(whl, msis, platname, curdir, distdir, setupargs)


