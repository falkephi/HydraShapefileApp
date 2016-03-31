# -*- mode: python -*-

#    Copyright (c) 2016, Philipp Meier
#
#    This file is part of the Hydra Platform ShapefileApp (HydraShapefileApp).
#
#    HydraShapefileApp is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by the
#    Free Software Foundation, either version 3 of the License, or (at your
#    option) any later version.
#
#    HydraShapefileApp is distributed in the hope that it will be useful, but
#    WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
#    or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
#    for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with HydraShapefileApp.  If not, see <http://www.gnu.org/licenses/>.

block_cipher = None

def get_pandas_path():
    import pandas
    pandas_path = pandas.__path__[0]
    return pandas_path

a = Analysis(['ExportSHP.py'],
             pathex=['E:\\work\\HYDRA\\Appstore\\HydraShapefileApp\\ShapefileApp\\plugins\\Export\\src'],
             binaries=None,
             datas=None,
             hiddenimports=['urllib2', 'HydraLib', 'GIS', 'osgeo'],
             hookspath=None,
             runtime_hooks=None,
             excludes=None,
             win_no_prefer_redirects=None,
             win_private_assemblies=None,
             cipher=block_cipher)

dict_tree = Tree(get_pandas_path(), prefix='pandas', excludes=["*.pyc"])
a.datas += dict_tree
a.binaries = filter(lambda x: 'pandas' not in x[0], a.binaries)

pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='ExportSHP',
          debug=False,
          strip=None,
          upx=True,
          console=True )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=None,
               upx=True,
               name='ExportSHP')
