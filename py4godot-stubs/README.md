# py4godot-stubs

Type stubs (`.pyi` files) for [py4godot](https://github.com/niklas2902/py4godot), providing
full IDE autocompletion and static type checking for the Godot Python bindings.

This is a **PEP 561** compatible stub package. Once installed, any type checker that
understands `py.typed` markers (Pylance, pyright, mypy, PyCharm, etc.) will
automatically pick up the type information.

## What's included

The stubs are auto-generated from Godot's `extension_api.json` and cover:

| Module | Contents |
|---|---|
| `py4godot/classes/*.pyi` | All Godot engine classes (Node3D, CharacterBody3D, Input, Resource, etc.) |
| `py4godot/classes/core.pyi` | Built-in / value types (Vector3, Color, Transform3D, String, Array, etc.) |
| `py4godot/functions.pyi` | Global utility functions (sin, lerp, print, randf_range, etc.) |
| `py4godot/constants.pyi` | Global constants (PI, TAU, INF, etc.) |
| `py4godot/enums.pyi` | Global enums (Error, PropertyHint, Side, etc.) |
| `py4godot/signals.pyi` | Signal helper types |

Every Godot class stub includes:

- **Properties** with `@property` / `@setter` pairs and correct return types
- **Methods** with full signatures, default values, and return types
- **Constructors** as `@staticmethod` methods (new0, new1, ...)
- **Singleton access** via `ClassName.instance()`
- **Inheritance** matching the real Godot class hierarchy

## Installation

### For end users (pip install from this directory)

```bash
pip install -e ./py4godot-stubs
```

### Using the convenience script (from the repo root)

```bash
./stubs.sh install     # generate + sync + pip install in one step
```

### Manual sync (developer workflow)

```bash
# 1. Generate stubs from extension_api.json
python generate_stubs.py

# 2. Copy them into the distribution package
./stubs.sh sync

# 3. Install so your IDE picks them up
pip install -e ./py4godot-stubs
```

## Editor setup

### VS Code / Cursor (Pylance)

The `py.typed` marker and PEP 561 install should be enough. If Pylance still
can't find the types, add to `.vscode/settings.json`:

```json
{
  "python.analysis.extraPaths": [
    "${workspaceFolder}/py4godot"
  ]
}
```

### PyCharm

Stubs are auto-detected when `py4godot-stubs` is installed into the project's
Python interpreter. No extra configuration needed.

### Vim / Neovim (pyright)

Ensure your `pyrightconfig.json` includes the stubs directory:

```json
{
  "extraPaths": ["./py4godot"]
}
```

Or install the stubs package and pyright will find them via the `py.typed` marker.

### mypy

```bash
pip install -e ./py4godot-stubs
mypy --python-version 3.12 your_project/
```

## Regenerating stubs

Stubs are regenerated whenever the Godot version changes (i.e. a new
`extension_api.json`). From the repo root:

```bash
./stubs.sh generate     # regenerate stubs
./stubs.sh sync         # copy into py4godot-stubs/
```

Or the all-in-one:

```bash
./stubs.sh install
```

## Validating stubs

Run pyright against the stubs to check for type errors:

```bash
./stubs.sh validate
```

## File structure

```
py4godot-stubs/
  py.typed              # PEP 561 marker (empty file)
  pyproject.toml        # Build metadata (setuptools)
  setup.cfg             # Legacy build metadata
  README.md             # This file
  py4godot/             # Stub files (sync'd from py4godot/)
    classes/
      __init__.py
      core.pyi          # Built-in types
      Node3D.pyi        # One file per Godot class
      Resource.pyi
      ...
    functions.pyi       # Global utility functions
    constants.pyi       # Global constants
    enums.pyi           # Global enums
    signals.pyi         # Signal helpers
```

## Versioning

The stubs package version tracks the py4godot release it was generated from.
When py4godot releases a new version, regenerate and bump the version in
`py4godot-stubs/pyproject.toml`.

## Troubleshooting

**Stubs not detected by IDE:**
- Ensure the package is installed: `pip show py4godot-stubs`
- Verify `py.typed` exists: `ls py4godot-stubs/py4godot/py.typed`
- Restart your IDE / language server after installing

**Wrong types for a class:**
- Regenerate: `./stubs.sh generate`
- The stubs are auto-generated from `extension_api.json` -- they reflect whatever
  Godot version that file came from

**Type checker errors in stubs:**
- Run `./stubs.sh validate` to see what pyright reports
- Most warnings are about unresolvable forward references in the Godot hierarchy
  and are harmless for IDE usage
