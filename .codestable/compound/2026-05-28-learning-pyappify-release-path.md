---
doc_type: learning
track: knowledge
date: 2026-05-28
slug: pyappify-release-path
component: windows-packaging
tags: [pyappify, github-actions, windows-build, release, packaging]
---

# PyAppify Release Path

## Background

This repository's official Windows build path is defined in `.github/workflows/build.yml` and `.github/workflows/codex_windows_build.yml`. Both use `ok-oldking/pyappify-action@master` and produce release artifacts under `pyappify_dist/*`.

That artifact is not the same as a local `dist/ok-ww/ok-ww.exe` PyInstaller folder.

## Guiding Principle

For release or distribution work, follow the PyAppify workflow first. Use a local PyInstaller build only as a debugging artifact or temporary smoke-test package.

## Why It Matters

PyAppify builds a Tauri launcher. At runtime, the launcher prepares `data/apps/ok-ww/python`, installs dependencies from `requirements.txt`, and runs the repository's Python entry script. This avoids freezing all Python/OpenVINO/onnxocr runtime assets into one PyInstaller directory.

A local PyInstaller build has a different failure model: it must explicitly bundle dynamic imports, native DLLs, package data, and model files. Debugging the PyInstaller folder can therefore solve a local artifact while still not matching the official release artifact.

## When To Use

Use the PyAppify path when:

- The user asks for the build that matches CI or release packaging.
- The expected output is an installer or `pyappify_dist` artifact.
- You are validating `.github/workflows/build.yml` or `.github/workflows/codex_windows_build.yml`.

Use local PyInstaller only when:

- The user explicitly asks for a standalone local folder build.
- You need a fast local reproduction of frozen Python behavior.
- The result is clearly labeled as a non-release, local PyInstaller artifact.

## Example

Correct release-oriented mental model:

1. Install project Python dependencies.
2. Run the test suite.
3. Let `ok-oldking/pyappify-action@master` build the launcher.
4. Package profile installers from `pyappify.yml` into `pyappify_dist/*`.

Local limitation observed on 2026-05-28: this machine did not have a usable `npm`, `pnpm`, or `cargo` in PATH, so the full PyAppify action could not be reproduced locally in the current shell. The GitHub Actions workflow remains the authoritative build path.
