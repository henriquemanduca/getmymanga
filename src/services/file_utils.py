import os
import platform


def get_default_download_folder():
    system = platform.system()
    if system == "Windows":
        return os.path.join(os.environ["USERPROFILE"], "Downloads")
    elif system == "Darwin":  # macOS
        return os.path.join(os.path.expanduser("~"), "Downloads")
    elif system == "Linux":
        return os.path.join(os.path.expanduser("~"), "Downloads")
    else:
        return ""

def rename_file_if_exists(file_path):
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
        for dir in dirs:
            os.rmdir(os.path.join(root, dir))
    os.rmdir(folder)