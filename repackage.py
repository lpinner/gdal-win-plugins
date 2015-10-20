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


# Always prefer setuptools over distutils
from setuptools import setup, find_packages
from distutils.dir_util import copy_tree
from codecs import open
import os,sys
import glob
import json
import shutil
import subprocess
import tempfile
import time
import wheel.install
import zipfile

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

NAME = 'GDAL'
name = NAME.replace('-', '_')
curdir = os.path.dirname(os.path.abspath(__file__))
distdir = os.path.join(curdir,'dist')
if not os.path.exists(distdir): os.mkdir(distdir)

#This setup.py is only for building wheels
del sys.argv[1:]
sys.argv.append('bdist_wheel')


# Wheels from http://www.lfd.uci.edu/~gohlke/pythonlibs/#gdal
WHEEL_64 = glob.glob('GDAL-*-cp27-*-win_amd64.whl')
WHEEL_32 = glob.glob('GDAL-*-cp27-*-win32.whl')

# MSIs from http://www.gisinternals.com
MSI_64 = glob.glob('gdal-*-1500-x64-*.msi')
MSI_32 = [f for f in glob.glob('gdal-*-1500-*.msi') if not 'x64' in f]


for arch, files in {'32':[WHEEL_32, MSI_32], '64':[WHEEL_64, MSI_64]}.items():
    try:
        wheels = files[0]
        msis = files[1]
        if not wheels:continue

        tmpdir = os.path.abspath(
            tempfile.mkdtemp(prefix='gdal', dir=curdir))

        platlib = os.path.join(tmpdir,'platlib')
        libdir = os.path.join(platlib,'osgeo')
        plugindir = os.path.join(libdir,'gdalplugins')

        #Unpack the wheel and move data into platlib
        whl = wheel.install.WheelFile(wheels[0])
        locs = {}
        for key in ('purelib', 'platlib', 'scripts', 'headers', 'data'):
            locs[key] = os.path.join(tmpdir, key)
            os.mkdir(locs[key])
        whl.install(overrides=locs)
        copy_tree(os.path.join(tmpdir,'data','Lib','site-packages','osgeo'), libdir)

        # Disable any existing plugins
        os.rename(plugindir, '%s.disabled'%plugindir)
        os.mkdir(plugindir)

        #Enable the plugin env var
        init = open(os.path.join(libdir,'__init__.py')).read()
        init = init.replace("#os.environ['GDAL_DRIVER_PATH']", "os.environ['GDAL_DRIVER_PATH']")
        init = init.replace('\r','')
        open(os.path.join(libdir,'__init__.py'), 'w').write(init)

        #Get some metadata for use in setup()
        metadata = json.load(open(os.path.join(platlib,whl.distinfo_name,'metadata.json')))
        metadata['classifiers'].remove('Programming Language :: Python :: 2')  #This dist is cpy27 only
        metadata['classifiers'].remove('Programming Language :: Python :: 3')  #This dist is cpy27 only
        metadata['classifiers'].append('Programming Language :: Python :: 2.7')
        metadata['classifiers'].remove('Operating System :: OS Independent')  #This dist is win only
        metadata['classifiers'].append('Operating System :: Microsoft :: Windows')
        metadata['classifiers'].append('License :: Other/Proprietary License') #For the MrSID/ECW libs
        description = open(os.path.join(platlib,whl.distinfo_name,'DESCRIPTION.rst')).read()

        shutil.rmtree(os.path.join(platlib,whl.distinfo_name))

        #Unpack the MSIs
        for msi in msis:
            msipath = os.path.abspath(msi)
            outpath = os.path.join(tmpdir, os.path.splitext(msi)[0])
            cmd = 'msiexec /a "%s" /qn TARGETDIR="%s"'%(msipath, outpath)
            subprocess.check_call(cmd)

            oldpath = os.path.join(outpath, 'PFiles','GDAL')
            copy_tree(oldpath,os.path.join(tmpdir,'platlib','osgeo'))


        #Build the wheel
        os.chdir(platlib)
        setupargs = {
            'name':NAME,#metadata['name'],
            'version':metadata['version'],
            'description':metadata['summary'],
            'long_description':description,
            #'platforms':['windows'],
            'maintainer':metadata['name'],
            'author':'GDAL Project',
            'author_email':'gdal-dev@lists.osgeo.org',
            'url':'http://www.gdal.org',
            'license':metadata['license'],
            'classifiers':metadata['classifiers'],
            'py_modules': [f[:-3] for f in glob.glob('*.py')],
            'package_dir':{'':os.path.join(tmpdir,'platlib')},
            'packages':['osgeo'],
            'package_data':{'': ['gdalserver.exe','*.dll', '*.pyd',
                                 'gdalplugins/*', 'gdalplugins.disabled/*',
                                 'license/*', 'data/gdal/*']},
        }


        setup(**setupargs)

        #Ugly kludge as I can't figure out how to get setup() to
        #create a platform wheel from a precompiled build
        platname = 'win32' if arch=='32' else 'win_amd64'

        zin=zipfile.ZipFile(os.path.join(platlib,'dist','%s-%s-py2-none-any.whl'%(name,metadata['version'])), 'r')
        whl = zin.open('%s-%s.dist-info/WHEEL'%(name,metadata['version'])).read()
        whl = whl.replace('Root-Is-Purelib: true','Root-Is-Purelib: false')
        whl = whl.replace('Tag: py2-none-any','Tag: cp27-none-%s'%platname)
        info = zipfile.ZipInfo('%s-%s.dist-info/WHEEL'%(name,metadata['version']))
        info.date_time = time.localtime(time.time())[:6]
        info.compress_type = zipfile.ZIP_DEFLATED
        zout = zipfile.ZipFile(os.path.join(distdir,'%s-%s-cp27-none-%s.whl'%(name,metadata['version'],platname)), 'w')
        for item in zin.infolist():
            buffer = zin.read(item.filename)
            if (item.filename[-5:] != 'WHEEL'):
                zout.writestr(item, buffer)
            else:
                zout.writestr(info, whl)

        zout.close()
        zin.close()

        os.chdir(curdir)
    finally:
        #Cleanup
        shutil.rmtree(tmpdir, onerror=err)


