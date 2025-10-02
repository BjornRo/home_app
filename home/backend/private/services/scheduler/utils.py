from __future__ import annotations

import os
import shutil
import sqlite3
import zipfile
from contextlib import asynccontextmanager, suppress
from ftplib import FTP, FTP_TLS, error_perm
from pathlib import Path

import aiosqlite

from appdata import cfg_schema, shared


class SingleFileBackupFTP_TLS(FTP_TLS):
    __slots__ = ("home_dir", "ftp_folder", "target_file", "backup_folder", "backup_size")

    def __init__(
        self,
        host: str,
        user: str,
        passwd: str,
        home_dir: str,
        ftp_folder: str,  # Folder to use in the home dir
        target_file: str,
        backup_folder="backup",
        size=10,
    ):
        super().__init__()  # Has to be first, otherwise it connects due to self.host
        self.host = host
        self.user = user
        self.passwd = passwd
        self.home_dir = Path(home_dir.strip("/").lower())
        self.ftp_folder = Path(ftp_folder.strip("/").lower())
        self.target_file = Path(target_file.rstrip("/"))
        self.backup_folder = Path(backup_folder.rstrip("/").lower())
        self.backup_size = size  # Generates new backups and deletes older that exceeds this number.

    def __enter__(self):
        self.connect()
        self.login(user=self.user, passwd=self.passwd, secure=True)
        self.prot_p()
        self.cwd(sorted(self.nlst())[0])  # Move into mounted drive
        # Build folders and enter
        for part in (self.home_dir / self.ftp_folder).parts:
            with suppress(error_perm):
                self.mkd(part)
            self.cwd(part)
        with suppress(error_perm):  # make backup folder
            self.mkd(self.backup_folder.name)
        return self

    def upload_file(self) -> bool:
        with self:
            # Check the backup folder of the files
            old_backup_list = self.lsdir(self.backup_folder.name, sorted_newest_first=True)
            if len(old_backup_list) >= self.backup_size:  # Remove one file to fit another
                self.delete(f"{self.backup_folder.name}/{old_backup_list[-1]}")
            with suppress(error_perm):  # If file does not exist on FTP. Will exist after first run.
                new_name = f"{self.backup_folder.name}/{shared.datetime_now_isofmtZ("minutes")}_{self.target_file.name}"
                self.rename(fromname=self.target_file.name, toname=new_name)  # Copy file to backup into backupfolder
            with open(self.target_file, "rb") as f:
                with suppress(error_perm):
                    self.storbinary(f"STOR {self.target_file.name}", f)
                    return True
            return False

    def get_file(self, overwite=True) -> bool:
        with self:
            if self.target_file.name in self.lsdir():
                if overwite and self.target_file.exists():
                    self.target_file.unlink()
                self.target_file.parent.mkdir(parents=True, exist_ok=True)

                with open(self.target_file, "wb") as f:
                    with suppress(error_perm):
                        self.retrbinary(f"RETR {self.target_file.name}", f.write)
                        return True
            return False

    def lsdir(self, dir: str = "", sorted_newest_first=False) -> list[str]:
        xs = []
        self.dir("-t" * sorted_newest_first, dir, lambda x: xs.append(x[x.rindex(" ") + 1 :]))
        return xs

    def ntransfercmd(self, cmd, rest=None):  # Transfers need the same session as the control connection.
        conn, size = FTP.ntransfercmd(self, cmd, rest)
        return self.context.wrap_socket(conn, server_hostname=self.host, session=self.sock.session), size  # type:ignore


def backup_db_routine(data_path: str, tmp_folder: str, zip_file: str, files: list[str], ftp_cfg: cfg_schema.FileKeyFTP):
    with suppress(FileNotFoundError):
        shutil.rmtree(tmp_folder)
    os.mkdir(tmp_folder)

    filefiles: list[tuple[str, str]] = []
    for file in files:
        tmp_filepath = os.path.join(tmp_folder, file)
        filefiles.append((file, tmp_filepath))
        source_conn = sqlite3.connect(os.path.join(data_path, file))
        target_conn = sqlite3.connect(tmp_filepath)
        with target_conn:
            source_conn.backup(target_conn)
        source_conn.close()
        target_conn.close()

    zip_filepath = os.path.join(tmp_folder, zip_file)
    with zipfile.ZipFile(zip_filepath, "w", zipfile.ZIP_BZIP2, compresslevel=9) as zipf:
        for file, tmp_filepath in filefiles:
            zipf.write(tmp_filepath, arcname=file)

    SingleFileBackupFTP_TLS(**ftp_cfg, target_file=zip_filepath).upload_file()


@asynccontextmanager
async def connect_db(filepath: Path):
    async with aiosqlite.connect(filepath) as conn:
        await conn.execute("PRAGMA foreign_keys = ON")
        await conn.execute("PRAGMA journal_mode = WAL")
        await conn.execute("PRAGMA temp_store = MEMORY")
        yield conn
