# -*- mode: python -*-

block_cipher = None


a = Analysis(['ImportSHP.py'],
             pathex=['E:\\work\\HYDRA\\Appstore\\HydraShapefileApp\\ShapefileApp\\plugins\\Import\\src'],
             binaries=None,
             datas=None,
             hiddenimports=['urllib2', 'HydraLib', 'GIS', 'osgeo'],
             hookspath=None,
             runtime_hooks=None,
             excludes=None,
             win_no_prefer_redirects=None,
             win_private_assemblies=None,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='ImportSHP',
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
               name='ImportSHP')
