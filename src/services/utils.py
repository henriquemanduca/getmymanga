import os
import platform
import zipfile


def remove_leading_zeros(num: str) -> str:
    inum = int(num, base=10)
    return str(inum)


def add_leading_zeros(num: int, total_len: int) -> str:
    snum = str(num)
    return snum.zfill(total_len)


def get_default_download_folder() -> str:
    system = platform.system()
    if system == "Windows":
        return os.path.join(os.environ["USERPROFILE"], "Downloads")
    elif system == "Darwin":  # macOS
        return os.path.join(os.path.expanduser("~"), "Downloads")
    elif system == "Linux":
        return os.path.join(os.path.expanduser("~"), "Downloads")
    else:
        return ""


def create_folder(folder_path) -> str:
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        return folder_path
    else:
        new_folder_path = rename_folder_if_exists(folder_path)
        os.makedirs(new_folder_path)
        return new_folder_path


def rename_folder_if_exists(folder_path) -> str:
    if os.path.exists(folder_path):
        i = 1
        new_folder_path = f"{folder_path}_{i}"
        while os.path.exists(new_folder_path):
            i += 1
            new_folder_path = f"{folder_path}_{i}"

        return new_folder_path

    return folder_path


def rename_file_if_exists(file_path) -> str:
    if os.path.exists(file_path):
        file_name, file_extension = os.path.splitext(file_path)
        i = 1
        new_file_path = f"{file_name}_{i}{file_extension}"
        while os.path.exists(new_file_path):
            i += 1
            new_file_path = f"{file_name}_{i}{file_extension}"

        return new_file_path

    return file_path


def remove_files(folder):
    for root, dirs, files in os.walk(folder):
        for file in files:
            os.remove(os.path.join(root, file))
        for _dir in dirs:
            os.rmdir(os.path.join(root, _dir))
    os.rmdir(folder)


def create_cbr(folder_path, cbr_file_path):
    if not os.path.exists(folder_path):
        return

    with zipfile.ZipFile(cbr_file_path, 'w', zipfile.ZIP_DEFLATED) as cbr_file:
        for folder_name, subfolders, files in os.walk(folder_path):
            for filename in files:
                file_path = os.path.join(folder_name, filename)
                cbr_file.write(str(file_path), str(os.path.relpath(str(file_path), str(folder_path))))
