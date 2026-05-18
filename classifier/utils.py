from pathlib import Path

def find_locales_path(start_path: str, folder_name="locales"):
    current = Path(start_path).resolve()

    for parent in [current, *current.parents]:
        potential = parent / folder_name
        if potential.exists() and potential.is_dir():
            return str(potential)

    raise FileNotFoundError(f"{folder_name} not found")
