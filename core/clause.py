"""A clause: the smallest citable unit of rule text in a clause index."""

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class Clause:
    id: str  # "<doc>:<slug>", unique in an index
    doc: str  # short document id, e.g. "BR2010", "ADP2013"
    ref: str  # human citation inside the document, e.g. "reg 12(6A)"
    text: str
    url: str = ""
    licence: str = "OGL-3.0"


def save_jsonl(clauses, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("".join(json.dumps(asdict(c), ensure_ascii=False) + "\n" for c in clauses))


def load_jsonl(path):
    return [Clause(**json.loads(line)) for line in Path(path).read_text().splitlines() if line.strip()]
