#!/usr/bin/env python3
"""Print the measured length of a quoted hex value whose stated length differs.

Reviewers run without tools and miscount long identifiers (three false
SHA-256 findings on 2026-10-07; invocation-failures/). A line that quotes a
hex value of 32+ characters and mentions N hex characters, where N is within
3 of the value's real length but not equal to it, gets a note giving every
hex length the line states and the value's measured length. The note does not
say which number refers to the value: "is 62 hex characters, expected 64" is
a correct finding about a truncated value. The owner reads the finding with
the note and decides; the wrapper records the note so that needs no round.
"""

import re
import sys

HEX = re.compile(r"(?<![0-9A-Za-z])[0-9a-fA-F]{32,}(?![0-9A-Za-z])")
CLAIM = re.compile(r"(?i)\b(\d{2,3})[\s-]*(?:hexadecimal|hex)[\s-]+(?:characters?|chars?|digits?)\b")


def notes(text):
    out = []
    for line in text.splitlines():
        values = HEX.findall(line)
        if not values:
            continue
        lengths = {len(v) for v in values}
        label = re.match(r"^\W*(F\d+|C\d+)", line)
        where = label.group(1) if label else "a review line"
        claims = sorted({int(m.group(1)) for m in CLAIM.finditer(line)})
        for v in values:
            if any(n != len(v) and abs(len(v) - n) <= 3 for n in claims):
                groups = " ".join(v[i:i + 8] for i in range(0, len(v), 8))
                stated = ", ".join(map(str, claims))
                out.append(f"{where} states {stated} hex characters; the quoted value measures {len(v)} ({groups})")
    return list(dict.fromkeys(out))


if __name__ == "__main__":
    for note in notes(sys.stdin.read()):
        print(note)
