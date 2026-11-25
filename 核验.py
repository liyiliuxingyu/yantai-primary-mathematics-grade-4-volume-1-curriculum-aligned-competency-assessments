from pathlib import Path
import hashlib
import sys


def main():
    root = Path(__file__).resolve().parent
    entries = (root / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
    failed = 0
    for line in entries:
        expected, name = line.split("  ", 1)
        try:
            with (root / name).open("rb") as stream:
                actual = hashlib.file_digest(stream, "sha256").hexdigest()
        except OSError as exc:
            print(f"{name} 读取失败（{exc.strerror}）", file=sys.stderr)
            failed += 1
            continue
        if actual != expected:
            print(f"{name} 校验值不匹配", file=sys.stderr)
            failed += 1

    print(f"共 {len(entries)} 项，通过 {len(entries) - failed} 项，失败 {failed} 项。")
    return int(failed != 0)


if __name__ == "__main__":
    sys.exit(main())
