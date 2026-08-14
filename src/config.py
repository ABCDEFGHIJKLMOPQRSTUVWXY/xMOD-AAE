import os


def get_app_data_dir() -> str:
    appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
    path = os.path.join(appdata, "xMOD-AAE")
    os.makedirs(path, exist_ok=True)
    return path


def get_books_dir() -> str:
    path = os.path.join(get_app_data_dir(), "books")
    os.makedirs(path, exist_ok=True)
    return path


def get_cache_dir() -> str:
    path = os.path.join(get_app_data_dir(), "cache")
    os.makedirs(path, exist_ok=True)
    return path


def get_db_path() -> str:
    return os.path.join(get_app_data_dir(), "store.db")
