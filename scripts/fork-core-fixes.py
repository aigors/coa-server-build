"""Fork-only source fixes applied to the core checkout (modules already placed) before the Linux compile.

The sources are compiled with MSVC for the Windows release, which accepts two things clang does not:

1. CoAPortableJson::Value holds std::vector<std::pair<std::string, Value>>: the pair is instantiated while Value is
   still incomplete, which libstdc++ 16 rejects. A named Member type, declared before Value and defined after it,
   keeps `.first` / `.second`, structured bindings and emplace_back(key, value) working.
2. A string literal in the bots' BotTalentBuilds.cpp holds a raw carriage return (byte 0x0D) where the escape `\r`
   was meant; clang reads it as a line break and the literal is left open. It becomes the escape.

Each fix is skipped when the source already has it, and fails the build when neither form is found.
Usage: python3 scripts/fork-core-fixes.py CORE_DIR
"""
import sys
from pathlib import Path

FIXES = [
    ("src/server/coa/CoAPortableJson.h", [
        ("    struct Value\n    {", "    struct Member;\n\n    struct Value\n    {"),
        ("        std::vector<std::pair<std::string, Value>> Members;\n", "        std::vector<Member> Members;\n"),
        ("        Value const* Find(std::string_view key) const;\n    };\n",
         "        Value const* Find(std::string_view key) const;\n    };\n\n"
         "    struct Member\n    {\n"
         "        Member(std::string key, Value value) : first(std::move(key)), second(std::move(value)) { }\n\n"
         "        std::string first;\n        Value second;\n    };\n"),
    ]),
    ("modules/mod-coa-playerbots/src/BotTalentBuilds.cpp", [
        # old: a raw CR (chr 13) followed by the two characters backslash, n; new: the escapes backslash r, backslash n.
        ('": " + error + "' + chr(13) + chr(92) + 'n";', '": " + error + "' + chr(92) + 'r' + chr(92) + 'n";'),
    ]),
]


def main(core: Path) -> int:
    for rel, pairs in FIXES:
        path = core / rel
        data = path.read_bytes().decode("utf-8")
        newline = "\r\n" if "\r\n" in data else "\n"
        pairs = [(o.replace("\n", newline), n.replace("\n", newline)) for o, n in pairs]
        if all(new in data for _, new in pairs):
            print(f"{rel}: already fixed")
            continue
        for old, new in pairs:
            if data.count(old) != 1:
                print(f"{rel}: expected text not found exactly once; review this fix", file=sys.stderr)
                return 1
            data = data.replace(old, new)
        path.write_bytes(data.encode("utf-8"))
        print(f"{rel}: fixed")
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1])))
