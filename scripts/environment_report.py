import json
import platform
import subprocess
import sys


def main():
    report = {
        "python": sys.version,
        "platform": platform.platform(),
    }

    try:
        import torch

        report["torch"] = torch.__version__
        report["cuda_available"] = torch.cuda.is_available()
        report["cuda_version"] = torch.version.cuda
        report["gpu"] = torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
        report["bf16_supported"] = (
            torch.cuda.is_bf16_supported() if torch.cuda.is_available() else False
        )
    except (ImportError, RuntimeError) as exc:
        report["torch_error"] = str(exc)

    release = platform.release().lower()
    report["wsl"] = "WSL2" if "microsoft" in release else "not-detected"

    for cmd, name in [
        (["git", "--version"], "git"),
        (["docker", "--version"], "docker"),
    ]:
        try:
            report[name] = subprocess.check_output(
                cmd,
                text=True,
                stderr=subprocess.STDOUT,
                timeout=10,
            ).strip()
        except (OSError, subprocess.SubprocessError) as exc:
            report[f"{name}_error"] = str(exc)

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
