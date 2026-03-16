import subprocess
import sys
from pathlib import Path
import shutil
import webbrowser


def find_project_base() -> Path:
    if getattr(sys, "frozen", False):
        start_dir = Path(sys.executable).resolve().parent
    else:
        start_dir = Path(__file__).resolve().parent

    candidates = [start_dir] + list(start_dir.parents)

    for candidate in candidates:
        if (candidate / "IA Model").exists() and (candidate / "Dockers").exists():
            return candidate

    print("\n[ERROR] Could not locate the project root folder.")
    print("The executable must be placed inside the project or one of its subfolders.")
    input("\nPress ENTER to close...")
    sys.exit(1)


BASE_DIR = find_project_base()
IA_DIR = BASE_DIR / "IA Model"
IA_DIST_DIR = IA_DIR / "dist"
DOCKER_DIR = BASE_DIR / "Dockers"
API_ML_DIR = DOCKER_DIR / "api-ml"
API_ML_TRAIN_DIR = DOCKER_DIR / "api-ml" / "train"
REGISTER_EXE = API_ML_DIR / "dist" / "register_joblib_metrics.exe"

def run_step(command, cwd, title):
    print(f"\n=== {title} ===")

    result = subprocess.run(
        command,
        shell=True,
        cwd=str(cwd)
    )

    if result.returncode != 0:
        print(f"Error during: {title}")
        input("\nPress ENTER to close...")
        sys.exit(result.returncode)


def check_exists(path, description):
    if not path.exists():
        print(f"\n[ERROR] Missing: {description}")
        print(f"Expected path: {path}")
        input("\nPress ENTER to close...")
        sys.exit(1)


def check_docker():
    if shutil.which("docker") is None:
        print("\n[ERROR] Docker is not installed.")
        input("\nPress ENTER to close...")
        sys.exit(1)


def move_model():
    print("\n=== Copying trained model ===")

    model_file = IA_DIST_DIR / "soc_action_recommender_rf.joblib"
    destination = API_ML_DIR / "soc_action_recommender_rf.joblib"

    if not model_file.exists():
        print("\n[ERROR] Trained model not found.")
        input("\nPress ENTER to close...")
        sys.exit(1)

    shutil.copy(model_file, destination)
    print(f"Model copied to: {destination}")

def move_dataset():
    print("\n=== Copying base dataset ===")

    model_file = IA_DIST_DIR / "soc_dataset.csv"
    destination = API_ML_TRAIN_DIR / "soc_dataset.csv"

    if not model_file.exists():
        print("\n[ERROR] Trained model not found.")
        input("\nPress ENTER to close...")
        sys.exit(1)

    shutil.copy(model_file, destination)
    print(f"Dataset copied to: {destination}")


def open_services():
    print("\n=== Opening web interfaces ===")
    webbrowser.open("http://localhost:5678/")
    webbrowser.open("http://localhost:5173/")

def register_model():
    print("\n=== Registering model in database ===")

    if not REGISTER_EXE.exists():
        print("\n[ERROR] register_joblib_metrics.exe not found.")
        print(f"Expected path: {REGISTER_EXE}")
        input("\nPress ENTER to close...")
        sys.exit(1)

    env = os.environ.copy()

    env["PG_HOST"] = "localhost"
    env["PG_PORT"] = "5432"
    env["PG_DB"] = "socdb"
    env["PG_USER"] = "soc"
    env["PG_PASS"] = "socpass"

    cmd = (
        f'"{REGISTER_EXE}" '
        f'--joblib soc_action_recommender_rf.joblib '
        f'--version v1.0.0 '
        f'--dataset train\\soc_dataset.csv '
        f'--artifact-path soc_action_recommender_rf.joblib '
        f'--set-active'
    )

    result = subprocess.run(
        cmd,
        shell=True,
        cwd=str(API_ML_DIR),
        env=env
    )

    if result.returncode != 0:
        print("\n[ERROR] Model registration failed.")
        input("\nPress ENTER to close...")
        sys.exit(result.returncode)


def main():
    print("Starting SOC system...")

    generate_exe = IA_DIST_DIR / "GenerateDataset.exe"
    train_exe = IA_DIST_DIR / "DatasetTraining.exe"

    check_exists(generate_exe, "IA Model/dist/GenerateDataset.exe")
    check_exists(train_exe, "IA Model/dist/DatasetTraining.exe")
    check_exists(API_ML_DIR, "Dockers/api-ml")
    check_exists(DOCKER_DIR / "compose.yml", "Dockers/compose.yml")

    check_docker()

    # 1 generate dataset
    run_step(
        f'"{generate_exe}"',
        IA_DIST_DIR,
        "Generating dataset"
    )

    # 2 train model
    run_step(
        f'"{train_exe}"',
        IA_DIST_DIR,
        "Training model"
    )

    # 3 move model
    move_model()

    # 4 move dataset
    move_dataset()

    # 5 start containers
    run_step(
        "docker compose -f compose.yml up -d --build",
        DOCKER_DIR,
        "Starting containers"
    )

    # wait for n8n to finish startup
    run_step(
        "timeout /t 15 > nul",
        DOCKER_DIR,
        "Waiting for n8n to finish startup"
    )

    # 6 import n8n workflows
    run_step(
        'docker exec n8n-minisoc sh -c "n8n import:workflow --separate --input=/data/flows || true"',
        DOCKER_DIR,
        "Importing n8n workflows"
    )

    # 7 register model in database
    register_model()

    open_services()

    print("\nSOC system started successfully.")
    input("\nPress ENTER to close...")


if __name__ == "__main__":
    main()