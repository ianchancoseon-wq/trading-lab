"""Verify original import, frozen evidence, and the separately versioned R1 manifest."""
import hashlib
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
BASE = '042bee94dfd34e765b38bf17720024df7e427a1f'
R1 = '5d5c218ede04a469e55ecb8659c70ac2578e4d06'
POST_MERGE_MUTABLE = {'phase0c/LAB-STATE.md', 'phase0c/g2a/verify_integrity.py'}


def git_bytes(path, ref=BASE):
    return subprocess.check_output(['git', 'show', f'{ref}:{path}'], cwd=ROOT)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify():
    count = frozen = 0
    frozen_names = set()
    for row in git_bytes('IMPORT-MANIFEST.sha256').decode().splitlines():
        expected, name = row.split('  ', 1)
        assert sha(git_bytes(name)) == expected, f'import mismatch: {name}'
        count += 1
        if name.startswith('phase0c/g1/') or name == 'predictions/PRED-M1-001.md':
            assert sha((ROOT / name).read_bytes()) == expected, f'frozen file changed: {name}'
            frozen += 1
            if name.startswith("phase0c/g1/"):
                frozen_names.add(name)
    actual_names = {p.relative_to(ROOT).as_posix() for p in (ROOT / "phase0c/g1").rglob("*") if p.is_file()}
    assert actual_names == frozen_names, "frozen G1 tree membership changed"
    assert (ROOT / 'IMPORT-MANIFEST.sha256').read_bytes() == git_bytes('IMPORT-MANIFEST.sha256')
    for name in ('phase0c/G1-R4-HASHES.sha256', 'phase0c/G2a-HASHES.sha256'):
        assert (ROOT / name).read_bytes() == git_bytes(name), f'historical manifest changed: {name}'
    # The R1 manifest is immutable evidence of the R1 commit, not a promise that
    # later LAB-STATE handoff notes or this verification helper never change.
    manifest = ROOT / 'phase0c/G2a-R1-HASHES.sha256'
    assert manifest.read_bytes() == git_bytes('phase0c/G2a-R1-HASHES.sha256', R1), 'R1 manifest modified'
    r1 = unchanged = 0
    for row in manifest.read_text().splitlines():
        expected, name = row.split('  ', 1)
        assert sha(git_bytes(name, R1)) == expected, f'R1 historical mismatch: {name}'
        if name not in POST_MERGE_MUTABLE:
            assert sha((ROOT / name).read_bytes()) == expected, f'R1 preserved file changed: {name}'
            unchanged += 1
        r1 += 1
    print(f'PASS: {count} original import entries; {frozen} frozen G1/M1 files; '
          f'{r1} R1 historical entries; {unchanged} current R1 files unchanged')
    print('Frozen M1 SHA-256:', sha((ROOT / 'predictions/PRED-M1-001.md').read_bytes()))
    print('R1 manifest SHA-256:', sha(manifest.read_bytes()))


if __name__ == '__main__':
    verify()
