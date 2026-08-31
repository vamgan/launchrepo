import os, subprocess, tempfile


def git(repo, *args):
    subprocess.run(["git", "-C", repo, *args], check=True, capture_output=True, text=True)


def make_repo(files=None, commits=1, remote=None):
    repo = tempfile.mkdtemp()
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "test@example.com")
    git(repo, "config", "user.name", "Test")
    for rel, content in (files or {"README.md": "# test\n"}).items():
        path = os.path.join(repo, rel)
        if os.path.dirname(rel):
            os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "initial")
    for n in range(commits - 1):
        with open(os.path.join(repo, "README.md"), "a", encoding="utf-8") as fh:
            fh.write(f"\nline {n}\n")
        git(repo, "add", "-A")
        git(repo, "commit", "-qm", f"change {n}")
    if remote:
        git(repo, "remote", "add", "origin", remote)
    return repo
