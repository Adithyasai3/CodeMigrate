"""Generate minimal, realistic code that uses a KB entry's API.

Used for (a) the retrieval benchmark (snippet -> analyzer -> query) and (b) synthetic
benchmark cases (whose ground truth is later established by execution, not by this module).
"""

from __future__ import annotations

from dataclasses import dataclass

from codemigrate.kb.schema import KBEntry
from codemigrate.kb.symbol_index import SymbolIndex


@dataclass
class Usage:
    code: str
    line: int  # 1-based line where the API is used
    style: str  # import | attribute | member | setting | template | meta | module_var
    filename: str = "case.py"


def api_kind(entry: KBEntry, index: SymbolIndex) -> str:
    """module | toplevel | member | setting | template | meta | module_var | unknown."""
    if entry.symbol_kind == "setting":
        return "setting"
    if entry.symbol_kind == "template":
        return "template"
    if entry.symbol_kind == "model_meta":
        return "meta"
    if entry.symbol_kind == "module_variable":
        return "module_var"
    api = entry.affected_api
    if not api.startswith("django."):
        return "unknown"
    if api in index.modules:
        return "module"
    parent = api.rsplit(".", 1)[0]
    if parent in index.modules:
        return "toplevel"
    grand = parent.rsplit(".", 1)[0]
    if grand in index.modules and parent.rsplit(".", 1)[1][:1].isupper():
        return "member"
    return "unknown"


def usage_for(entry: KBEntry, index: SymbolIndex, variant: int = 0) -> Usage | None:
    """Return a snippet using ``entry``'s API; ``variant`` selects alternative styles."""
    kind = api_kind(entry, index)
    api = entry.affected_api
    if kind == "module":
        parent, name = api.rsplit(".", 1)
        if variant == 0:
            return Usage(f"from {parent} import {name}\n\nprint({name}.__name__)\n", 1, "import")
        return Usage(f"import {api} as mod\n\nprint(mod.__name__)\n", 1, "import")
    if kind == "toplevel":
        parent, name = api.rsplit(".", 1)
        if variant == 0:
            return Usage(f"from {parent} import {name}\n\nVALUE = {name}\n", 1, "import")
        alias = parent.rsplit(".", 1)[1]
        pkg = parent.rsplit(".", 1)[0]
        return Usage(f"from {pkg} import {alias}\n\nVALUE = {alias}.{name}\n", 3, "attribute")
    if kind == "member":
        cls_path, member = api.rsplit(".", 1)
        mod, cls = cls_path.rsplit(".", 1)
        if variant == 0:
            return Usage(f"from {mod} import {cls}\n\nMEMBER = {cls}.{member}\n", 3, "member")
        return Usage(
            f"from {mod} import {cls}\n\n\nclass Custom({cls}):\n    def run(self):\n"
            f"        return self.{member}()\n",
            6,
            "member",
        )
    if kind == "setting":
        name = api.split(".", 1)[1]
        return Usage(
            f'SECRET_KEY = "x"\nINSTALLED_APPS = []\n{name} = True\n', 3, "setting", "settings.py"
        )
    if kind == "template":
        name = api.split(":", 1)[1]
        return Usage(
            f"{{% if items|{name}:2 %}}two{{% endif %}}\n", 1, "template", "templates/case.html"
        )
    if kind == "meta":
        return Usage(
            "from django.db import models\n\n\nclass Item(models.Model):\n"
            "    name = models.CharField(max_length=10)\n    rank = models.IntegerField()\n\n"
            "    class Meta:\n        app_label = 'cases'\n"
            "        index_together = [['name', 'rank']]\n",
            10,
            "meta",
        )
    if kind == "module_var":
        return Usage(
            "default_app_config = 'cases.apps.CasesConfig'\n", 1, "module_var", "__init__.py"
        )
    return None
