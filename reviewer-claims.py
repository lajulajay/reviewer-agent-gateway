#!/usr/bin/env python3
"""Print a note for each length claim in a review that its own quoted hex value contradicts.

Reviewers run without tools and miscount long identifiers (three false
SHA-256 findings on 2026-10-07; invocation-failures/). A line that quotes a
hex value of 32+ characters and calls something N characters long, where N
is within 3 of the value's real length but not equal to it, gets a note. The
wrapper records each note in the artifact so the owner can dismiss the
finding without another round.
"""

import re
import sys

HEX = re.compile(r"(?<![0-9A-Za-z])[0-9a-fA-F]{32,}(?![0-9A-Za-z])")
CLAIM = re.compile(r"(?i)\b(\d{2,3})[\s-]*(?:hexadecimal\s+|hex\s+)?(?:characters?|chars?|digits?)\b")


def notes(text):
    out = []
    for line in text.splitlines():
        values = HEX.findall(line)
        if not values:
            continue
        lengths = {len(v) for v in values}
        label = re.match(r"^\W*(F\d+|C\d+)", line)
        where = label.group(1) if label else "a review line"
        for m in CLAIM.finditer(line):
            n = int(m.group(1))
            if n in lengths:
                continue
            for v in values:
                if abs(len(v) - n) <= 3:
                    groups = " ".join(v[i:i + 8] for i in range(0, len(v), 8))
                    out.append(f"{where} says {n} characters, but the value it quotes is {len(v)} ({groups})")
                    break
    return list(dict.fromkeys(out))


if __name__ == "__main__":
    for note in notes(sys.stdin.read()):
        print(note)
