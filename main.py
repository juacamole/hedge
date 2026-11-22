import os
import sys

import storage
from view import Hedge


def main() -> None:
    preloaded = []
    for path in sys.argv[1:]:
        try:
            preloaded.append((storage.load(path), os.path.basename(path)))
        except (OSError, ValueError) as error:
            sys.exit(f"could not load {path}: {error}")
    Hedge(preloaded).run()


if __name__ == "__main__":
    main()
