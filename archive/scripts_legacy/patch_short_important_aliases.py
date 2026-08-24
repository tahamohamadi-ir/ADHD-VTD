from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from textwrap import dedent


ROOT = Path.cwd()
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
path = ROOT / "src/schema/schema_linker.py"

old = path.read_text(encoding="utf-8")
backup = path.with_suffix(path.suffix + f".bak_{STAMP}")
shutil.copy2(path, backup)
print(f"Backup created: {backup}")

new = old

new = new.replace(
'''    STOPWORDS = {
        "است",''',
'''    IMPORTANT_SHORT_ALIASES = {
        "زن",
        "مرد",
    }

    STOPWORDS = {
        "است",'''
)

new = new.replace(
'''            if len(token) < 3:
                continue

            if token in self.STOPWORDS:
                continue''',
'''            if len(token) < 3 and token not in self.IMPORTANT_SHORT_ALIASES:
                continue

            if token in self.STOPWORDS and token not in self.IMPORTANT_SHORT_ALIASES:
                continue'''
)

new = new.replace(
'''        if len(token) < 4 or len(alias_norm) < 4:
            return False''',
'''        if token in self.IMPORTANT_SHORT_ALIASES and alias_norm in self.IMPORTANT_SHORT_ALIASES:
            return True

        if len(token) < 4 or len(alias_norm) < 4:
            return False'''
)

path.write_text(new, encoding="utf-8")
print("✅ Patched short important aliases in schema_linker.py")
