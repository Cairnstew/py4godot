#!/usr/bin/env python3
"""
Generate Python type stubs (.pyi files) for py4godot.

This script generates comprehensive type stubs that enable IDE autocompletion
and type checking for py4godot classes and modules.

Usage:
    python generate_stubs.py [--output-dir OUTPUT_DIR] [--clean] [--verbose]
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Optional

# Add the generation_files directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "generation_files"))


class StubGenerator:
    """Main stub generator class."""

    def __init__(self, output_dir: str = "py4godot", verbose: bool = False):
        self.output_dir = Path(output_dir)
        self.verbose = verbose
        self.extension_api_path = self.output_dir / "gdextension-api" / "extension_api.json"
        self.data: dict[str, Any] = {}
        self.classes: set[str] = set()
        self.builtin_classes: set[str] = set()
        self.normal_classes: set[str] = set()
        self.singletons: set[str] = set()
        self.typed_arrays: set[str] = set()

    def log(self, message: str) -> None:
        if self.verbose:
            print(f"[stub-gen] {message}")

    def load_extension_api(self) -> None:
        """Load the GDExtension API JSON."""
        self.log(f"Loading extension API from {self.extension_api_path}")
        with open(self.extension_api_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)

        # Collect all class names
        self.builtin_classes = {c["name"] for c in self.data.get("builtin_classes", [])}
        self.normal_classes = {c["name"] for c in self.data.get("classes", [])}
        self.classes = self.builtin_classes | self.normal_classes
        self.singletons = {s["name"] for s in self.data.get("singletons", [])}

        self.log(f"Found {len(self.builtin_classes)} builtin classes, {len(self.normal_classes)} normal classes")

    def generate_type_mapping(self) -> dict[str, str]:
        """Map Godot types to Python types."""
        return {
            "String": "str",
            "StringName": "str",
            "NodePath": "str",
            "Variant": "Any",
            "bool": "bool",
            "int": "int",
            "float": "float",
            "void": "None",
            "Nil": "None",
        }

    def ungodottype(self, type_: str, is_core: bool = False) -> str:
        """Convert a Godot type to a Python type."""
        type_map = self.generate_type_mapping()

        if type_ in type_map:
            return type_map[type_]

        if type_.startswith("enum::"):
            return "int"

        if type_.startswith("bitfield::"):
            return "int"

        if type_.startswith("typedarray::"):
            return "Array"

        if type_ in self.builtin_classes:
            if is_core:
                return type_
            return f"core.{type_}"

        if type_ in self.normal_classes:
            if is_core:
                return type_
            return type_

        return type_

    def generate_constructor_args(self, constructor: dict) -> str:
        """Generate constructor arguments string."""
        if "arguments" not in constructor:
            return ""

        args = []
        for arg in constructor["arguments"]:
            name = arg["name"]
            # Handle Python keywords
            if name in ("from", "len", "in", "for", "with", "class", "pass", "raise", "global", "str", "typeof"):
                name = name + "_"

            type_ = self.ungodottype(arg["type"])
            args.append(f"{name}: {type_}")

        return ", ".join(args)

    def generate_method_stub(self, class_name: str, method: dict, is_core: bool = False) -> str:
        """Generate a method stub."""
        name = method["name"]

        # Handle Python keywords
        if name in ("from", "len", "in", "for", "with", "class", "pass", "raise", "global", "str", "typeof"):
            name = name + "_"

        # Build arguments
        args = ["self"]
        if "arguments" in method:
            for arg in method["arguments"]:
                arg_name = arg["name"]
                if arg_name in ("from", "len", "in", "for", "with", "class", "pass", "raise", "global", "str", "typeof"):
                    arg_name = arg_name + "_"

                arg_type = self.ungodottype(arg["type"], is_core)

                # Handle default values
                default = ""
                if "default_value" in arg:
                    default_val = arg["default_value"]
                    if isinstance(default_val, bool):
                        default = f" = {str(default_val).lower()}"
                    elif isinstance(default_val, str):
                        # Skip complex defaults for now
                        default = ""
                    elif default_val is not None:
                        default = f" = {default_val}"

                args.append(f"{arg_name}: {arg_type}{default}")

        # Build return type
        ret_type = "None"
        if "return_value" in method:
            ret_type = self.ungodottype(method["return_value"]["type"], is_core)
        elif "return_type" in method:
            ret_type = self.ungodottype(method["return_type"], is_core)

        args_str = ", ".join(args)

        # Add static method decorator if needed
        prefix = ""
        if method.get("is_static", False):
            prefix = "@staticmethod\n    "

        return f"{prefix}def {name}({args_str}) -> {ret_type}: ..."

    def generate_property_stub(self, class_name: str, prop: dict, is_core: bool = False) -> str:
        """Generate a property stub."""
        name = prop["name"]
        prop_type = self.ungodottype(prop["type"], is_core)

        lines = []
        lines.append(f"@property")
        lines.append(f"def {name}(self) -> {prop_type}: ...")

        if "setter" in prop and prop["setter"]:
            lines.append(f"@{name}.setter")
            lines.append(f"def {name}(self, value: {prop_type}) -> None: ...")

        return "\n    ".join(lines)

    def generate_class_stub(self, class_data: dict, is_core: bool = False) -> str:
        """Generate a complete class stub."""
        class_name = class_data["name"]

        if class_name in ("Nil", "bool", "float", "int"):
            return ""

        # Determine base class
        if "inherits" in class_data:
            base = class_data["inherits"]
            if not is_core:
                base = f"core.{base}"
        elif class_name in self.builtin_classes:
            base = "VariantTypeWrapper4"
        else:
            base = "object"

        lines = []
        lines.append(f"class {class_name}({base}):")
        lines.append(f'    """Godot {class_name} class."""')

        # Add docstring
        if class_name in self.data.get("classes", []):
            for cls in self.data["classes"]:
                if cls["name"] == class_name and "description" in cls:
                    desc = cls["description"].split("\n")[0][:80]
                    lines[1] = f'    """{desc}"""'

        # Add __init__
        if is_core:
            lines.append("")
            lines.append("    def __init__(self) -> None: ...")

        # Add constructors
        if "constructors" in class_data:
            for i, constructor in enumerate(class_data["constructors"]):
                args = self.generate_constructor_args(constructor)
                if args:
                    lines.append(f"")
                    lines.append(f"    @staticmethod")
                    lines.append(f"    def new{i}({args}) -> {class_name}: ...")

        # Add singleton instance method
        if class_name in self.singletons:
            lines.append("")
            lines.append("    @staticmethod")
            lines.append(f"    def instance() -> {class_name}: ...")

        # Add properties
        if "properties" in class_data:
            for prop in class_data["properties"]:
                lines.append("")
                prop_stub = self.generate_property_stub(class_name, prop, is_core)
                lines.append(f"    {prop_stub}")

        # Add methods
        if "methods" in class_data:
            for method in class_data["methods"]:
                lines.append("")
                method_stub = self.generate_method_stub(class_name, method, is_core)
                lines.append(f"    {method_stub}")

        return "\n".join(lines)

    def generate_utility_functions_stub(self) -> str:
        """Generate stubs for utility functions."""
        lines = []
        lines.append('"""Utility functions for py4godot."""')
        lines.append("from typing import Any")
        lines.append("")

        for func in self.data.get("utility_functions", []):
            name = func["name"]

            # Build arguments
            args = []
            if "arguments" in func:
                for arg in func["arguments"]:
                    arg_name = arg["name"]
                    arg_type = self.ungodottype(arg["type"])
                    args.append(f"{arg_name}: {arg_type}")

            # Build return type
            ret_type = "Any"
            if "return_type" in func:
                ret_type = self.ungodottype(func["return_type"])

            args_str = ", ".join(args)
            lines.append(f"def {name}({args_str}) -> {ret_type}: ...")

        return "\n".join(lines)

    def generate_constants_stub(self) -> str:
        """Generate stubs for global constants."""
        lines = []
        lines.append('"""Global constants for py4godot."""')
        lines.append("")

        for constant in self.data.get("global_constants", []):
            name = constant["name"]
            value = constant["value"]
            lines.append(f"{name}: int = {value}")

        return "\n".join(lines)

    def generate_enums_stub(self) -> str:
        """Generate stubs for global enums."""
        lines = []
        lines.append('"""Global enums for py4godot."""')
        lines.append("")

        for enum in self.data.get("global_enums", []):
            enum_name = enum["name"]
            lines.append(f"class {enum_name}:")
            for value in enum["values"]:
                lines.append(f"    {value['name']}: int = {value['value']}")
            lines.append("")

        return "\n".join(lines)

    def write_stub(self, path: Path, content: str) -> None:
        """Write a stub file, creating directories as needed."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        self.log(f"  Wrote {path}")

    def generate_all_stubs(self) -> None:
        """Generate all stub files."""
        self.load_extension_api()

        # Create output directory structure
        classes_dir = self.output_dir / "classes"
        classes_dir.mkdir(parents=True, exist_ok=True)

        # Generate core stubs (builtin classes)
        self.log("Generating core stubs...")
        core_content = []
        core_content.append('"""Core Godot types."""')
        core_content.append("from typing import Any")
        core_content.append("")
        core_content.append("from py4godot.utils.VariantTypeWrapper4 import VariantTypeWrapper4")
        core_content.append("")

        for class_data in self.data.get("builtin_classes", []):
            stub = self.generate_class_stub(class_data, is_core=True)
            if stub:
                core_content.append(stub)
                core_content.append("")

        self.write_stub(classes_dir / "__init__.py", "\n".join([
            '"""py4godot classes module."""',
            "",
            "import py4godot.classes.core as core",
            "",
        ]))

        self.write_stub(classes_dir / "core.pyi", "\n".join(core_content))

        # Generate stubs for normal classes
        self.log("Generating class stubs...")
        for class_data in self.data.get("classes", []):
            class_name = class_data["name"]
            stub = self.generate_class_stub(class_data, is_core=False)
            if stub:
                content = []
                content.append(f'"""Stubs for {class_name}."""')
                content.append("from typing import Any")
                content.append("")
                content.append(f"import py4godot.classes.core as core")
                content.append("")
                content.append(stub)
                content.append("")

                self.write_stub(classes_dir / f"{class_name}.pyi", "\n".join(content))

        # Generate utility functions stub
        self.log("Generating utility functions stub...")
        util_stub = self.generate_utility_functions_stub()
        self.write_stub(self.output_dir / "functions.pyi", util_stub)

        # Generate constants stub
        self.log("Generating constants stub...")
        const_stub = self.generate_constants_stub()
        self.write_stub(self.output_dir / "constants.pyi", const_stub)

        # Generate enums stub
        self.log("Generating enums stub...")
        enum_stub = self.generate_enums_stub()
        self.write_stub(self.output_dir / "enums.pyi", enum_stub)

        self.log("Stub generation complete!")

    def clean(self) -> None:
        """Remove all generated stub files."""
        import glob

        patterns = [
            str(self.output_dir / "classes" / "*.pyi"),
            str(self.output_dir / "*.pyi"),
        ]

        for pattern in patterns:
            for file in glob.glob(pattern):
                os.remove(file)
                self.log(f"  Removed {file}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate Python type stubs for py4godot"
    )
    parser.add_argument(
        "--output-dir",
        default="py4godot",
        help="Output directory for stubs (default: py4godot)"
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean generated stubs before generating"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output"
    )

    args = parser.parse_args()

    generator = StubGenerator(output_dir=args.output_dir, verbose=args.verbose)

    if args.clean:
        generator.clean()

    generator.generate_all_stubs()


if __name__ == "__main__":
    main()
