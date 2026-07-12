import sys
import importlib
from pathlib import Path
from types import ModuleType

def load_external_modules(project_root: Path, module_names: list[str]) -> dict[str, ModuleType]:
    """Import top-level modules from a sibling source project without leaking
    their generic names (models, data, ...) into Argus's own sys.modules."""
    root = str(project_root)
    shadowed = {name.split(".")[0] for name in module_names}
    saved = {
        name: sys.modules.pop(name)
        for name in list(sys.modules)
        if name.split(".")[0] in shadowed
    }

    sys.path.insert(0, root)
    try: 
        loaded = {name: importlib.import_module(name) for name in module_names}
    finally:
        sys.path.remove(root)
        for name in list(sys.modules):
            if name.split(".")[0] in shadowed:
                del sys.modules[name]
        sys.modules.update(saved)

    return loaded