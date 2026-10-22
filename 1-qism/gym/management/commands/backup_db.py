import shutil
import sqlite3
import subprocess
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Makes a consistent database backup (SQLite copy, or pg_dump for PostgreSQL) and deletes old ones."

    def add_arguments(self, parser):
        parser.add_argument("--dir", default=str(settings.BASE_DIR / "backups"))
        parser.add_argument("--keep", type=int, default=14, help="how many backups to keep")

    def handle(self, *args, **opts):
        out = Path(opts["dir"])
        out.mkdir(parents=True, exist_ok=True)
        db = settings.DATABASES["default"]
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")  # microseconds: two backups in the same second must not overwrite each other
        if db["ENGINE"].endswith("sqlite3"):
            target = out / f"fitnes-{stamp}.sqlite3"
            src, dst = sqlite3.connect(db["NAME"]), sqlite3.connect(target)
            with dst:
                src.backup(dst)  # safe while the site is running
            src.close()
            dst.close()
        else:
            pg_dump = shutil.which("pg_dump")
            if not pg_dump:
                raise CommandError("pg_dump was not found. Install the PostgreSQL client tools or use your host's backup feature.")
            target = out / f"fitnes-{stamp}.dump"
            subprocess.run([pg_dump, "--no-owner", "--format=custom", "--file", str(target), "--dbname",
                            f"postgresql://{db['USER']}:{db['PASSWORD']}@{db['HOST']}:{db['PORT'] or 5432}/{db['NAME']}"], check=True)
        old = sorted(out.glob("fitnes-*"), key=lambda p: p.stat().st_mtime, reverse=True)[opts["keep"]:]
        for p in old:
            p.unlink()
        self.stdout.write(f"Backup: {target} (deleted {len(old)} old)")
