# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules

hiddenimports = [
    'src.globals',
    'src.scene.WWScene',
    'src.task.AutoCombatTask',
    'src.task.AutoLoginTask',
    'src.task.AutoPickTask',
    'src.task.AutoRogueTask',
    'src.task.ChangeEchoTask',
    'src.task.DailyTask',
    'src.task.DiagnosisTask',
    'src.task.EnhanceEchoTask',
    'src.task.FarmEchoTask',
    'src.task.FastTravelTask',
    'src.task.ForgeryTask',
    'src.task.MouseResetTask',
    'src.task.MultiAccountDailyTask',
    'src.task.NightmareNestTask',
    'src.task.SimulationTask',
    'src.task.SkipDialogTask',
    'src.task.TacetTask',
]
hiddenimports += collect_submodules('src.char')
hiddenimports += collect_submodules('src.combat')
hiddenimports += collect_submodules('src.combat.rotation')
hiddenimports += collect_submodules('onnxocr')
hiddenimports += collect_submodules('openvino.frontend')
hiddenimports = sorted(set(hiddenimports))

openvino_runtime_binaries = sorted(set(collect_dynamic_libs('openvino')))
openvino_runtime_datas = collect_data_files('openvino', includes=['libs/*.json'])
onnxocr_model_datas = collect_data_files('onnxocr', includes=['models/**/*'])


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=openvino_runtime_binaries,
    datas=[
        ('assets', 'assets'),
        ('i18n', 'i18n'),
        ('icons', 'icons'),
        ('ok_templates', 'ok_templates'),
        ('icon.png', '.'),
        ('icon.ico', '.'),
    ] + openvino_runtime_datas + onnxocr_model_datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ok-ww',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    uac_admin=True,
    icon=['icon.ico'],
    contents_directory='.',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ok-ww',
)
