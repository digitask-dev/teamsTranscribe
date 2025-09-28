import sys
from pathlib import Path
root = Path('.').resolve()
for candidate in (root / 'src', root):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

print('start', flush=True)
import tests.test_transcription as t
print('module imported', flush=True)
t.test_transcriber_emits_after_window()
print('test executed', flush=True)
