---
doc_type: learning
track: pitfall
date: 2026-05-28
slug: pyinstaller-runtime-assets
component: windows-packaging
severity: high
tags: [pyinstaller, openvino, onnxocr, packaging, executable]
---

# PyInstaller Runtime Assets Pitfall

## Problem

Freezing this project with a hand-written PyInstaller command can produce an executable that starts but fails later when OCR or dynamic task loading is used.

## Symptoms

- `ModuleNotFoundError` from `ok.util.clazz.init_class_by_name()` when importing config-driven modules such as `src.globals`.
- OpenVINO reports that the ONNX model cannot be read and lists only partial frontends such as `jax` and `pytorch`.
- After the ONNX frontend is bundled, OpenVINO can still report `Device with "CPU" name is not registered in the OpenVINO Runtime`.

## What Did Not Work

Adding only `--collect-submodules src` was not enough. PyInstaller did not discover all nested `src.task.*` modules, OpenVINO frontends, OpenVINO runtime plugin DLLs, or `onnxocr` model files.

Fixing only the latest missing DLL also led to a chain of new runtime failures: first missing ONNX frontend, then missing OCR model data, then missing CPU plugin.

## Solution

Treat the PyInstaller build as a full runtime packaging problem, not a single import problem:

- Explicitly include config-driven modules from `config.py`.
- Collect `src.char`, `src.combat`, and `src.combat.rotation` submodules.
- Collect `onnxocr` submodules and `onnxocr/models/**/*`.
- Collect `openvino.frontend`.
- Collect all dynamic libraries from `collect_dynamic_libs("openvino")`.
- Include OpenVINO runtime data such as `openvino/libs/*.json`.

## Why It Works

The failing dependencies are loaded dynamically by configuration strings, OpenVINO runtime discovery, and package data paths. Those mechanisms are invisible or only partially visible to PyInstaller static analysis, so they must be declared as packaging inputs.

## Prevention

When changing a PyInstaller build for this project, validate beyond startup:

- Confirm expected dynamic modules are present in the archive.
- Confirm OCR model files exist under the packaged `onnxocr/models/ppocrv5/` path.
- Confirm every `.dll` from `.venv/Lib/site-packages/openvino/libs` exists in the packaged OpenVINO libs folder.
- Run `Core().read_model()` and `Core().compile_model(..., device_name="CPU")` against packaged `det`, `rec`, and `cls` ONNX models.

Related artifact: `.codestable/issues/2026-05-28-pyinstaller-dynamic-imports/pyinstaller-dynamic-imports-fix-note.md`.
