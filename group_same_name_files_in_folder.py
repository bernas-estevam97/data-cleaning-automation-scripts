import shutil
import logging
from pathlib import Path
from tqdm import tqdm


LOG_FILE_NAME = "file_organizer.log"


def setup_logging(log_path: Path) -> None:
    """Configure file-based logging."""
    logging.basicConfig(
        filename=str(log_path),
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def organize_files(directory: Path) -> None:
    """
    Organize files in the given directory by moving each file
    into a folder named after its filename (without extension).
    """
    if not directory.exists() or not directory.is_dir():
        raise ValueError("The provided path is not a valid directory.")

    log_file_path = directory / LOG_FILE_NAME
    setup_logging(log_file_path)

    files = [
        f for f in directory.iterdir()
        if f.is_file() and f.name != LOG_FILE_NAME
    ]

    total_files = len(files)

    if total_files == 0:
        print("\nNo files found to organize.")
        return

    print(f"\nFound {total_files} files. Starting organization...\n")

    success_count = 0
    error_count = 0

    progress = tqdm(files, desc="Organizing", unit="file")

    for file in progress:
        folder_name = file.stem
        target_folder = directory / folder_name
        destination = target_folder / file.name

        try:
            target_folder.mkdir(exist_ok=True)

            # Prevent overwriting existing files
            if destination.exists():
                logging.warning(
                    f"SKIPPED: '{file.name}' already exists in '{folder_name}/'"
                )
                continue

            shutil.move(str(file), str(destination))
            logging.info(f"SUCCESS: Moved '{file.name}' to '{folder_name}/'")
            success_count += 1

        except Exception as e:
            logging.error(
                f"FAILED: Could not move '{file.name}'. Reason: {e}"
            )
            error_count += 1

        progress.set_postfix(
            success=success_count,
            errors=error_count
        )

    print("\n" + "-" * 40)
    print("Organization Complete")
    print(f"Successfully moved : {success_count}")
    print(f"Errors encountered : {error_count}")
    print(f"Log file           : {log_file_path}")
    print("-" * 40)


def main() -> None:
    print("File Organizer")
    print("Press Ctrl+C at any time to cancel.\n")

    try:
        folder_input = input("Enter the folder path to organize: ").strip().strip('"')
        directory = Path(folder_input).expanduser().resolve()

        organize_files(directory)

    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"\nError: {e}")


if __name__ == "__main__":
    main()