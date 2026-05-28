---
doc_type: issue-fix
issue: pyinstaller-dynamic-imports
status: fixed
severity: high
root_cause_type: packaging
tags:
  - build
  - pyinstaller
  - executable
---

# PyInstaller Dynamic Imports Fix Note

## Problem

The packaged executable failed during startup with `ModuleNotFoundError` while `ok.util.clazz.init_class_by_name()` imported the configured `my_app` class.

After that was fixed, enabling OCR-related behavior in the packaged executable failed with OpenVINO reporting that it could not read `dist\ok-ww\onnxocr\models\ppocrv5\det\det.onnx` and only listed `jax` and `pytorch` as available frontends.

After the ONNX frontend and models were bundled, OpenVINO then reported `Device with "CPU" name is not registered in the OpenVINO Runtime`, because the CPU plugin was also missing from the frozen runtime.

## Root Cause

`config.py` supplies several classes as string module paths, including `src.globals`, `src.scene.WWScene`, and task modules. PyInstaller did not discover all of those dynamic imports from static analysis, so the frozen archive was missing `src.globals` and some task modules.

The frozen app also missed package runtime assets that are loaded outside normal static imports:

- OpenVINO frontend/runtime modules and `openvino\libs\*.dll`, including `openvino_onnx_frontend.dll`, `openvino_intel_cpu_plugin.dll`, GPU/NPU plugins, and TBB DLLs
- OpenVINO runtime data such as `openvino\libs\cache.json`
- `onnxocr` model data under `onnxocr\models\ppocrv5\`

## Fix

`ok-ww.spec` now explicitly lists the config-driven dynamic modules in `hiddenimports` and also collects the project character and combat subpackages.

It also collects `onnxocr`, `openvino.frontend`, all OpenVINO dynamic runtime libraries, OpenVINO runtime JSON data, and bundled `onnxocr` model files.

The repository's official Windows release path is still `.github/workflows/build.yml` / `.github/workflows/codex_windows_build.yml`, which builds `pyappify_dist/*` through `ok-oldking/pyappify-action@master`. That path uses a PyAppify launcher and installs normal Python dependencies under `data/apps/ok-ww/python`; it is not the same artifact as the local `dist\ok-ww` PyInstaller folder.

## Verification

- Rebuilt with `.\.venv\Scripts\pyinstaller.exe --clean --noconfirm ok-ww.spec`.
- Verified the frozen archive contains `src.globals`, `src.task.AutoLoginTask`, `src.task.AutoRogueTask`, `src.task.MultiAccountDailyTask`, `src.task.EnhanceEchoTask`, `src.task.DiagnosisTask`, and `src.task.FastTravelTask`.
- Confirmed packaged runtime assets still include `dist\ok-ww\assets\coco_annotations.json`.
- Confirmed `dist\ok-ww\openvino\frontend\onnx\py_onnx_frontend.cp312-win_amd64.pyd` and `dist\ok-ww\openvino\libs\openvino_onnx_frontend.dll` exist.
- Confirmed every `.dll` from `.venv\Lib\site-packages\openvino\libs` is present in `dist\ok-ww\openvino\libs`.
- Confirmed `dist\ok-ww\openvino\libs\cache.json` exists.
- Confirmed `dist\ok-ww\onnxocr\models\ppocrv5\det\det.onnx`, `rec\rec.onnx`, `cls\cls.onnx`, and `ppocrv5_dict.txt` exist.
- Verified OpenVINO can read and compile the packaged OCR `det`, `rec`, and `cls` ONNX models from `dist\ok-ww` with `device_name='CPU'`.
- `.\.venv\Scripts\python.exe -m unittest tests.TestTeamRotation` passed.

## Notes

Launching the UAC-manifested executable inside the current sandbox reports Windows error `0xc0000142`, so GUI startup must be checked from a normal desktop session.
