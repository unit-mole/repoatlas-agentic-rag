import shutil
import subprocess
from pathlib import Path

ROOT = Path("data/fixture_repo")


def main():
    if ROOT.exists():
        shutil.rmtree(ROOT)
    (ROOT / "src/demo").mkdir(parents=True)
    (ROOT / "tests").mkdir(parents=True)
    (ROOT / "src/demo/cache.py").write_text(
        """class Cache:\n    def __init__(self, timeout=30): self.timeout=timeout; self.values={}\n    def get(self,key): return self.values.get(key)\n    def set(self,key,value): self.values[key]=value\n"""
    )
    (ROOT / "src/demo/auth.py").write_text(
        """from .cache import Cache\nclass TokenManager:\n    def __init__(self, cache: Cache): self.cache=cache\n    def refresh_token(self,user):\n        cached=self.cache.get(user)\n        if cached: return cached\n        token=f"token-{user}"\n        self.cache.set(user,token)\n        return token\n"""
    )
    (ROOT / "tests/test_auth.py").write_text(
        """from src.demo.cache import Cache\nfrom src.demo.auth import TokenManager\ndef test_refresh_uses_cache():\n    c=Cache();m=TokenManager(c);assert m.refresh_token("a")==m.refresh_token("a")\n"""
    )
    (ROOT / "pyproject.toml").write_text('[tool.pytest.ini_options]\npythonpath=["."]\n')
    subprocess.run(["git", "init"], cwd=ROOT, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "fixture@example.com"], cwd=ROOT, check=True)
    subprocess.run(["git", "config", "user.name", "RepoAtlas Fixture"], cwd=ROOT, check=True)
    subprocess.run(["git", "add", "."], cwd=ROOT, check=True)
    subprocess.run(
        ["git", "commit", "-m", "fixture base"], cwd=ROOT, check=True, capture_output=True
    )
    print(ROOT)


if __name__ == "__main__":
    main()
