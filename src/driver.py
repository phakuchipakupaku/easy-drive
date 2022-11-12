import os

from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive


class EasyDrive:
    driver = None

    def __init__(self):
        self.parent_id_cache = {}

    def auth(
        self,
        client_config_file="client_secret.json",
        your_env="paperspace-gradient",
    ):
        google_auth = GoogleAuth()
        google_auth.DEFAULT_SETTINGS["client_config_file"] = client_config_file

        if your_env == "paperspace-gradient":
            google_auth.CommandLineAuth()
        else:
            google_auth.LocalWebserverAuth()
        EasyDrive.driver = GoogleDrive(google_auth)

    def get_filelist(self, parent_id="root"):
        query = '"{}" in parents and trashed=false'.format(parent_id)
        return self.driver.ListFile({"q": query}).GetList()

    def check_existence(self, drive_path):
        drive_path = self.check_path(input_path=drive_path)

        drive_path_splitted = drive_path.split("/")
        filename_for_key = parent_id = drive_path_splitted.pop(0)
        cnt = 0
        for name in drive_path_splitted:
            filename_for_key += f"/{name}"
            if filename_for_key in self.parent_id_cache.keys():
                parent_id = self.parent_id_cache[filename_for_key]
                cnt += 1
            else:
                filelist = self.get_filelist(parent_id=parent_id)
                filenames = [x["title"] for x in filelist]
                if name in filenames:
                    parent_id = filelist[filenames.index(name)]["id"]
                    self.parent_id_cache[filename_for_key] = parent_id
                    cnt += 1

        return True if cnt == len(drive_path_splitted) else False

    def create_one_folder(
        self,
        folder_name,
        parent_id,
        return_new_folder_parent_id=False,
    ):
        folder_metadata = {
            "title": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [{"id": parent_id}],
        }
        folder = self.driver.CreateFile(folder_metadata)
        folder.Upload()
        if return_new_folder_parent_id:
            return folder.get("id")

    def upload_file_to_exist_folder(
        self,
        filepath,
        filename,
        parent_id=None,
        parent_id_for_same_file=None,
    ):
        filepath = self.check_path(input_path=filepath)

        if parent_id_for_same_file is not None:
            gfile = self.driver.CreateFile({"id": parent_id_for_same_file})
        else:
            gfile = self.driver.CreateFile()
            gfile["parents"] = [{"id": parent_id}]

        gfile.SetContentFile(filepath)
        gfile["title"] = filename

        print(f"Uploading... ({filepath})")
        gfile.Upload()

    def upload_file(self, local_filepath, drive_dirpath, overwirte=True):
        local_filepath = self.check_path(input_path=local_filepath)
        drive_dirpath = self.check_path(input_path=drive_dirpath)

        dfilename = os.path.basename(local_filepath)
        drive_filepath = f"{drive_dirpath}/{dfilename}"

        exit_file = self.check_existence(drive_filepath)
        if exit_file:
            if overwirte:
                print(
                    f"This file ({drive_filepath}) already exists in your Google Drive. It will be overwritten."
                )
                same_exitence_id = self.parent_id_cache[drive_filepath]
                self.upload_file_to_exist_folder(
                    local_filepath, dfilename, parent_id_for_same_file=same_exitence_id
                )
            else:
                print(
                    f"This file ({drive_filepath}) already exists in your Google Drive."
                )
        else:
            self.create_folders_from_path(drive_dirpath)
            self.upload_file_to_exist_folder(
                local_filepath,
                dfilename,
                parent_id=self.parent_id_cache[drive_dirpath],
            )

    def create_folders_from_path(self, drive_dirpath):
        drive_dirpath = self.check_path(input_path=drive_dirpath)
        exist_folder = self.check_existence(drive_dirpath)
        if exist_folder:
            return

        folder_path_splitted = drive_dirpath.split("/")
        parent_id = folder_path_splitted.pop(0)
        existed_parent_id = filename_for_key = parent_id
        for name in folder_path_splitted:
            filename_for_key += f"/{name}"
            if filename_for_key in self.parent_id_cache.keys():
                existed_parent_id = self.parent_id_cache[filename_for_key]
                continue
            else:
                print(f"Creating folder... {filename_for_key}")
                parent_id = self.create_one_folder(
                    folder_name=name,
                    parent_id=existed_parent_id,
                    return_new_folder_parent_id=True,
                )
                existed_parent_id = self.parent_id_cache[filename_for_key] = parent_id

    def download_file(self, local_dirpath, drive_filepath):
        """drive 上の特定のファイルを local上の特定のフォルダにダウンロードする"""
        print(f"Downloading... {drive_filepath}")
        drive_filepath = self.check_path(drive_filepath)
        exit_file = self.check_existence(drive_path=drive_filepath)
        if not exit_file:
            raise FileNotFoundError()

        os.makedirs(local_dirpath, exist_ok=True)

        f = self.driver.CreateFile({"id": self.parent_id_cache[drive_filepath]})
        f.GetContentFile(os.path.join(local_dirpath, f["title"]))

    @staticmethod
    def check_path(input_path):
        input_path = str(input_path)
        if input_path[-1] == "/":
            return input_path[:-1]
        return input_path
