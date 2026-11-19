"""Fork-only source fixes applied to the core checkout before the Linux compile.

CoAPortableJson::Value holds std::vector<std::pair<std::string, Value>>: the pair is instantiated while Value is still
incomplete. MSVC accepts it; clang with libstdc++ 16 (Ubuntu 26.04) rejects it. A named Member type, declared before
Value and defined after it, keeps `.first` / `.second`, structured bindings and emplace_back(key, value) working.

Each fix is skipped when the core already has it, and fails the build when neither form is found.
Usage: python3 scripts/fork-core-fixes.py CORE_DIR
"""
import sys
from pathlib import Path

FIXES = [
    (
        "src/server/coa/CoAPortableJson.h",
        """    struct Value
    {""",
        """    struct Member;

    struct Value
    {""",
        "        std::vector<std::pair<std::string, Value>> Members;\n",
        "        std::vector<Member> Members;\n",
        """        Value const* Find(std::string_view key) const;
    };
""",
        """        Value const* Find(std::string_view key) const;
    };

    struct Member
    {
        Member(std::string key, Value value) : first(std::move(key)), second(std::move(value)) { }

        std::string first;
        Value second;
    };
""",
    ),
]


def main(core: Path) -> int:
    for rel, *pairs in FIXES:
        path = core / rel
        text = path.read_text(encoding="utf-8")
        newline = "\r\n" if "\r\n" in text else "\n"
        pairs = [p.replace("\n", newline) for p in pairs]
        old_new = list(zip(pairs[0::2], pairs[1::2]))
        if all(new in text for _, new in old_new):
            print(f"{rel}: already fixed")
            continue
        for old, new in old_new:
            if text.count(old) != 1:
                print(f"{rel}: expected text not found exactly once; review this fix", file=sys.stderr)
                return 1
            text = text.replace(old, new)
        path.write_text(text, encoding="utf-8", newline="")
        print(f"{rel}: fixed")
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1])))
