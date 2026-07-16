import re
import subprocess
from dataclasses import dataclass


NUM_RE = re.compile(r"\d{1,3}(?:\s\d{3})*\.\d{2}(?:\s*-)?")


class ParseError(Exception):
    pass


@dataclass
class RawTransaction:
    date_str: str  # YYYY/MM/DD
    descricao: str
    debito: float | None
    credito: float | None


def pdf_to_layout_text(pdf_path: str) -> list[str]:
    """Runs pdftotext -layout and returns the output split into lines."""
    result = subprocess.run(
        ["pdftotext", "-layout", pdf_path, "-"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.splitlines()


def to_float(s: str) -> float:
    s = s.strip()
    neg = s.endswith("-")
    if neg:
        s = s[:-1].strip()
    val = float(s.replace(" ", ""))
    return -val if neg else val
