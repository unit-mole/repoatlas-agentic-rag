from pathlib import Path

from repoatlas.repositories.clone import clone_repository


def main():
    dest = Path("data/repositories/httpx")
    print(clone_repository("https://github.com/encode/httpx.git", dest))


if __name__ == "__main__":
    main()
