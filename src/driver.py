import os

from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive


class EasyDrive:
    def __init__(
        self,
        client_config_file="client_secret.json",
        your_env="paperspace-gradient",
    ):
        self.client_config_file = client_config_file
        self.your_env = your_env
        self.driver = None
        self.parent_id_cache = {}

    def auth(self):
        google_auth = GoogleAuth()
        google_auth.DEFAULT_SETTINGS["client_config_file"] = self.client_config_file

        if self.your_env == "paperspace-gradient":
            google_auth.CommandLineAuth()
        else:
            google_auth.LocalWebserverAuth()
        self.driver = GoogleDrive(google_auth)

    def get_filelist(self, parent_id="root"):
        query = '"{}" in parents'.format(parent_id)
        return self.driver.ListFile({"q": query}).GetList()

    def check_existence(self, drive_path):
        drive_path = self.check_path(input_path=drive_path)

        drive_path_splitted = drive_path.split("/")
        parent_id = drive_path_splitted.pop(0)

        filename_for_key = parent_id
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

    def upload_file_to_exist_folder(self, filepath, filename, parent_id):
        filepath = self.check_path(input_path=filepath)
        gfile = self.driver.CreateFile()
        gfile["parents"] = [{"id": parent_id}]
        gfile.SetContentFile(filepath)
        gfile["title"] = filename
        gfile.Upload()

    def upload_file(self, filepath, drive_path):
        filepath = self.check_path(input_path=filepath)
        drive_path = self.check_path(input_path=drive_path)

        ddirname, dfilename = os.path.dirname(drive_path), os.path.basename(drive_path)
        self.create_folders_from_path(folder_path=ddirname)
        self.upload_file_to_exist_folder(
            filepath,
            dfilename,
            parent_id=self.parent_id_cache[ddirname],
        )

    def create_folders_from_path(self, folder_path):
        folder_path = self.check_path(input_path=folder_path)
        exist_folder = self.check_existence(folder_path)
        if exist_folder:
            return

        folder_path_splitted = folder_path.split("/")
        parent_id = folder_path_splitted.pop(0)
        filename_for_key = parent_id

        existed_parent_id = parent_id
        for name in folder_path_splitted:
            filename_for_key += f"/{name}"
            if filename_for_key in self.parent_id_cache.keys():
                existed_parent_id = self.parent_id_cache[filename_for_key]
                continue
            else:
                parent_id = self.create_one_folder(
                    folder_name=name,
                    parent_id=existed_parent_id,
                    return_new_folder_parent_id=True,
                )
                existed_parent_id = self.parent_id_cache[filename_for_key] = parent_id

    @staticmethod
    def check_path(input_path):
        input_path = str(input_path)
        if input_path[-1] == "/":
            return input_path[:-1]
        return input_path
