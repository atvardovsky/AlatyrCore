"""Repository-local Python import graph shared by source tooling."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ImportScan:
    dependencies: frozenset[Path]
    complete: bool


class LocalPythonImportGraph:
    """Resolve static imports against one repository's ``tools`` package."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.modules = self._module_paths()
        self._path_modules = {path: name for name, path in self.modules.items()}
        self._scans: dict[Path, ImportScan] = {}
        self._reverse_dependencies: dict[Path, set[Path]] | None = None

    def _module_paths(self) -> dict[str, Path]:
        modules: dict[str, Path] = {}
        tools = self.root / "tools"
        if not tools.is_dir():
            return modules
        for path in sorted(tools.rglob("*.py")):
            relative = path.relative_to(tools).with_suffix("")
            parts = relative.parts[:-1] if relative.name == "__init__" else relative.parts
            modules[".".join(parts)] = path.resolve()
        return modules

    def _resolve_relative(
        self, module: str | None, level: int, current_package: str
    ) -> str | None:
        if level == 0:
            return module or ""
        package_parts = current_package.split(".") if current_package else []
        remove = level - 1
        if remove > len(package_parts):
            return None
        base = package_parts[: len(package_parts) - remove]
        if module:
            base.extend(module.split("."))
        return ".".join(base)

    def scan(self, path: Path) -> ImportScan:
        resolved_path = path.resolve()
        cached = self._scans.get(resolved_path)
        if cached is not None:
            return cached
        try:
            tree = ast.parse(
                resolved_path.read_text(encoding="utf-8"), filename=str(resolved_path)
            )
        except (OSError, SyntaxError, UnicodeError):
            result = ImportScan(frozenset(), False)
            self._scans[resolved_path] = result
            return result

        current_module = self._path_modules.get(resolved_path)
        current_package = ""
        if current_module:
            current_package = (
                current_module
                if resolved_path.name == "__init__.py"
                else current_module.rpartition(".")[0]
            )
        dependencies: set[Path] = set()
        complete = True
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                base = self._resolve_relative(node.module, node.level, current_package)
                if base is None:
                    complete = False
                    continue
                if base:
                    names.append(base)
                names.extend(
                    f"{base}.{alias.name}" if base else alias.name
                    for alias in node.names
                    if alias.name != "*"
                )
            elif isinstance(node, ast.Call):
                dynamic = (
                    isinstance(node.func, ast.Name) and node.func.id == "__import__"
                ) or (
                    isinstance(node.func, ast.Attribute)
                    and node.func.attr == "import_module"
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "importlib"
                )
                if dynamic:
                    if (
                        not node.args
                        or not isinstance(node.args[0], ast.Constant)
                        or not isinstance(node.args[0].value, str)
                    ):
                        complete = False
                        continue
                    names.append(node.args[0].value)
            for name in names:
                candidate = self.modules.get(name)
                if candidate is not None:
                    dependencies.add(candidate)
        result = ImportScan(frozenset(dependencies), complete)
        self._scans[resolved_path] = result
        return result

    def transitive_dependencies(self, path: Path) -> set[Path]:
        closure: set[Path] = set()
        pending = [path.resolve()]
        visited: set[Path] = set()
        while pending:
            current = pending.pop()
            if current in visited:
                continue
            visited.add(current)
            for dependency in self.scan(current).dependencies:
                if dependency == path.resolve() or dependency in closure:
                    continue
                closure.add(dependency)
                pending.append(dependency)
        return closure

    def reverse_dependents(self, changed: set[Path]) -> set[Path]:
        impacted = {path.resolve() for path in changed}
        if self._reverse_dependencies is None:
            reverse_dependencies: dict[Path, set[Path]] = {}
            for importer in self.modules.values():
                for dependency in self.scan(importer).dependencies:
                    reverse_dependencies.setdefault(dependency, set()).add(importer)
            self._reverse_dependencies = reverse_dependencies
        pending = list(impacted)
        while pending:
            dependency = pending.pop()
            for importer in self._reverse_dependencies.get(dependency, set()):
                if importer not in impacted:
                    impacted.add(importer)
                    pending.append(importer)
        return impacted
