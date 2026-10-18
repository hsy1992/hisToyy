import sys
from pathlib import Path

if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--self-test":
        from app.smoke import run
        run(Path(sys.argv[2]))
    else:
        from app.gui import main
        raise SystemExit(main())
