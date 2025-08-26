from __future__ import annotations

import re


def build_dependency_graph(content: str) -> dict[str, list[str]]:
    dependencies: dict[str, list[str]] = {
        "imports": [],
        "internal_references": [],
        "third_party_imports": [],
        "stdlib_imports": [],
    }

    import_patterns = [
        r"import\s+([a-zA-Z_][a-zA-Z0-9_.]*)",
        r"from\s+([a-zA-Z_][a-zA-Z0-9_.]*)\s+import",
        r'#include\s*[<"]([^>"]+)[>"]',
        r"require\s*\([\'\"]([^\'\"]+)[\'\"]\)",
        r"import\s+.*\s+from\s+[\'\"]([^\'\"]+)[\'\"]",
    ]

    for pattern in import_patterns:
        imports = re.findall(pattern, content)
        dependencies["imports"].extend(imports)

    python_stdlib = {
        "os",
        "sys",
        "json",
        "math",
        "random",
        "datetime",
        "collections",
        "itertools",
        "functools",
        "operator",
        "re",
        "urllib",
        "http",
        "pathlib",
        "typing",
        "dataclasses",
        "abc",
        "enum",
        "logging",
        "threading",
        "multiprocessing",
        "subprocess",
        "socket",
        "sqlite3",
        "csv",
        "pickle",
        "gzip",
        "zipfile",
        "tarfile",
        "shutil",
        "tempfile",
    }

    for imp in dependencies["imports"]:
        base_module = imp.split(".")[0]
        if base_module in python_stdlib:
            dependencies["stdlib_imports"].append(imp)
        elif is_third_party_import(imp):
            dependencies["third_party_imports"].append(imp)
        else:
            dependencies["internal_references"].append(imp)

    return dependencies


def is_third_party_import(import_name: str) -> bool:
    base_module = import_name.split(".")[0].lower()
    known_third_party = {
        "requests",
        "numpy",
        "pandas",
        "flask",
        "django",
        "fastapi",
        "tensorflow",
        "torch",
        "pytorch",
        "sklearn",
        "scipy",
        "matplotlib",
        "seaborn",
        "plotly",
        "streamlit",
        "dash",
        "celery",
        "redis",
        "sqlalchemy",
        "alembic",
        "pydantic",
        "marshmallow",
        "click",
        "typer",
        "pytest",
        "unittest2",
        "mock",
        "httpx",
        "aiohttp",
        "websockets",
        "uvicorn",
        "gunicorn",
        "jinja2",
        "mako",
        "babel",
        "pillow",
        "opencv",
        "cv2",
        "boto3",
        "azure",
        "google",
    }
    if base_module in known_third_party:
        return True
    if any(pattern in base_module for pattern in ["lib", "client", "sdk", "api"]):
        return True
    if "_" in base_module and not base_module.startswith("_"):
        return True
    if (
        base_module.islower()
        and not base_module.startswith("test")
        and base_module not in ["main", "app", "config", "utils", "helpers"]
    ):
        return True
    return False
