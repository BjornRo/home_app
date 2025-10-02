import os
import shutil
import sys
from pathlib import Path

import paramiko

TARGET_DIR = Path()
REMOTE_DIR = Path("docker")

TARGET_PATHS = {"services"}
TARGET_FILES = {"docker-compose.yml"}

CONFIG_TARGET_KEY = "public"

def main():
    config = paramiko.SSHConfig()
    with open(os.path.expanduser("~/.ssh/config")) as f:
        config.parse(f)
    cfg = dict(config.lookup(CONFIG_TARGET_KEY))

    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.connect(
        hostname=cfg["hostname"],
        port=int(cfg["port"]),
        username=cfg["user"],
        allow_agent=True,
        pkey=paramiko.ECDSAKey.from_private_key_file(cfg["identityfile"][0]),
    )
    try:
        modified, new_files = [], []
        with client.open_sftp() as sftp:
            for tf in TARGET_FILES:
                upload_file(sftp, Path(tf), modified, new_files)
            for tp in TARGET_PATHS:
                for local_file in TARGET_DIR.glob(f"{tp}/**/*"):
                    if str(local_file).endswith("__pycache__"):
                        shutil.rmtree(local_file)
                    elif "app.db" in str(local_file):
                        continue
                    upload_file(sftp, local_file, modified, new_files)

        if new_files or modified:
            print("New:", len(new_files))
            for f in new_files:
                print(" ", f)
            print()

            print("Modified:", len(modified))
            for f in modified:
                print(" ", f)

            args = " ".join(sys.argv[1:])
            if args:
                stdin, stdout, stderr = client.exec_command(f"docker restart {args}")
                print()
                print("Restarted:", stdout.readlines()[0].strip())
        else:
            print("No modified and no new files.")
    except:
        print(__import__("traceback").format_exc())
    client.close()


def upload_file(sftp: paramiko.SFTPClient, filepath: Path, mod: list[Path], new: list[Path]):
    if not filepath.is_file():
        return
    remote_file = REMOTE_DIR / filepath.relative_to(TARGET_DIR)
    try:
        remote_modified_time = sftp.lstat(remote_file.as_posix()).st_mtime
        if remote_modified_time is None:
            raise Exception("?")

        local_modified_time = int(os.path.getmtime(filepath))
        if local_modified_time <= remote_modified_time:
            return
        mod.append(filepath)
    except FileNotFoundError:
        new.append(filepath)
        for p in remote_file.parent.as_posix().split("/"):
            try:
                sftp.mkdir(p)
            except:
                pass
            sftp.chdir(p)
        sftp.chdir()
    sftp.put(str(filepath), remote_file.as_posix())


if __name__ == "__main__":
    main()
