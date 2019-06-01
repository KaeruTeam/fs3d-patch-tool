from scripts.darc import Darc
from scripts.msbt import Msbt

from sys import argv
from pathlib import Path
from io import BytesIO
import json

darc = Darc.Open(argv[1])
outputDir = Path(argv[2])
outputDir.mkdir(parents=True, exist_ok=True)

for entry in darc.root.entries:
  path = Path(entry.name)
  print(path.suffix)
  # If the file is an .msbt, convert it to .msbt.json
  if path.suffix == '.msbt':
    msbt = Msbt()
    msbt.read(BytesIO(entry.data))
    filepath = outputDir / path
    filepath = filepath.with_suffix('.msbt.json')
    msbt.dump_json(filepath)

  else:
    filepath = outputDir / path
    with filepath.open(mode='wb') as fp:
      fp.write(entry.data)
    