import sys
import tarfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import build_package  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]


def make_fixture_repo(tmp_path: Path) -> Path:
    (tmp_path / ".claude-plugin").mkdir(parents=True)
    (tmp_path / ".claude-plugin" / "marketplace.json").write_text('{"plugins": {}}')
    (tmp_path / ".claude-plugin" / "plugin.json").write_text("{}")
    (tmp_path / "skills").mkdir()
    (tmp_path / "skills" / "example.md").write_text("# skill")
    for d in ("plugins", "schemas", "templates"):
        (tmp_path / d).mkdir()
        (tmp_path / d / "placeholder.txt").write_text("x")
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\nversion = "1.2.3"\n')
    return tmp_path


def test_get_version_parses_pyproject(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "x"\nversion = "1.2.3"\n')

    assert build_package.get_version(pyproject) == "1.2.3"


def test_get_version_missing_raises(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "x"\n')

    with pytest.raises(ValueError, match="No version field"):
        build_package.get_version(pyproject)


def test_get_version_no_project_table_raises(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[tool.other]\nversion = "9.9.9"\n')

    with pytest.raises(ValueError, match=r"No \[project\] table"):
        build_package.get_version(pyproject)


def test_build_package_creates_versioned_tarball(tmp_path: Path) -> None:
    repo = make_fixture_repo(tmp_path / "repo")
    out = tmp_path / "out"

    tarball = build_package.build_package(repo, out)

    assert tarball == out / "project-mnemosyne-1.2.3.tar.gz"
    assert tarball.is_file()
    with tarfile.open(tarball, "r:gz") as tar:
        names = tar.getnames()
    assert ".claude-plugin/marketplace.json" in names
    assert ".claude-plugin/plugin.json" in names
    assert "skills/example.md" in names
    assert "plugins/placeholder.txt" in names
    assert "schemas/placeholder.txt" in names
    assert "templates/placeholder.txt" in names


def test_build_package_excludes_pycache_and_pyc(tmp_path: Path) -> None:
    repo = make_fixture_repo(tmp_path / "repo")
    cache = repo / "skills" / "__pycache__"
    cache.mkdir()
    (cache / "x.pyc").write_text("bytecode")
    (repo / "skills" / "stray.pyc").write_text("bytecode")

    tarball = build_package.build_package(repo, tmp_path / "out")

    with tarfile.open(tarball, "r:gz") as tar:
        names = tar.getnames()
    assert not any("__pycache__" in n for n in names)
    assert not any(n.endswith(".pyc") for n in names)


def test_build_package_missing_dir_raises(tmp_path: Path) -> None:
    repo = make_fixture_repo(tmp_path / "repo")
    (repo / "schemas" / "placeholder.txt").unlink()
    (repo / "schemas").rmdir()

    with pytest.raises(FileNotFoundError, match="schemas"):
        build_package.build_package(repo, tmp_path / "out")


def _make_tarball(tmp_path: Path, files: dict) -> Path:
    """Hand-build a tarball from a mapping of arcname -> content."""
    src = tmp_path / "src"
    tarball = tmp_path / "bundle.tar.gz"
    with tarfile.open(tarball, "w:gz") as tar:
        for arcname, content in files.items():
            path = src / arcname
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
            tar.add(path, arcname=arcname)
    return tarball


def test_verify_missing_marketplace_json(tmp_path: Path) -> None:
    tarball = _make_tarball(
        tmp_path,
        {
            ".claude-plugin/plugin.json": "{}",
            "skills/example.md": "# skill",
        },
    )

    problems = build_package.verify_package(tarball)

    assert problems == ["missing .claude-plugin/marketplace.json"]


def test_verify_invalid_marketplace_json(tmp_path: Path) -> None:
    tarball = _make_tarball(
        tmp_path,
        {
            ".claude-plugin/marketplace.json": "not json {",
            ".claude-plugin/plugin.json": "{}",
            "skills/example.md": "# skill",
        },
    )

    problems = build_package.verify_package(tarball)

    assert len(problems) == 1
    assert problems[0].startswith("marketplace.json is not valid JSON")


def test_verify_no_skill_files(tmp_path: Path) -> None:
    tarball = _make_tarball(
        tmp_path,
        {
            ".claude-plugin/marketplace.json": '{"plugins": {}}',
            ".claude-plugin/plugin.json": "{}",
        },
    )

    problems = build_package.verify_package(tarball)

    assert problems == ["no skill .md files in bundle"]


def test_main_success_and_failure_exit_codes(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    repo = make_fixture_repo(tmp_path / "repo")
    out = tmp_path / "out"

    assert build_package.main(["--repo-root", str(repo), "--output-dir", str(out)]) == 0
    assert "Built and verified" in capsys.readouterr().out

    # Break the fixture so verify fails: rebuild with no skill .md files.
    (repo / "skills" / "example.md").unlink()
    (repo / "skills" / "keep.txt").write_text("x")

    assert build_package.main(["--repo-root", str(repo), "--output-dir", str(out)]) == 1
    assert "no skill .md files in bundle" in capsys.readouterr().err


def test_main_default_output_dir(tmp_path: Path) -> None:
    repo = make_fixture_repo(tmp_path / "repo")

    assert build_package.main(["--repo-root", str(repo)]) == 0
    assert (repo / "dist" / "project-mnemosyne-1.2.3.tar.gz").is_file()


def test_real_repo_builds_clean(tmp_path: Path) -> None:
    tarball = build_package.build_package(REPO_ROOT, tmp_path)

    assert build_package.verify_package(tarball) == []


def test_real_repo_packages_namespaced_skill_utils_module() -> None:
    pyproject = (REPO_ROOT / "pyproject.toml").read_text()

    assert 'py-modules = ["mnemosyne_skill_utils"]' in pyproject
    assert 'py-modules = ["skill_utils"]' not in pyproject
    assert (REPO_ROOT / "scripts" / "mnemosyne_skill_utils.py").is_file()
    assert not (REPO_ROOT / "scripts" / "skill_utils.py").exists()
