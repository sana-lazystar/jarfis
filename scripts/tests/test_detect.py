"""Tests for jarfis.detect — project framework/language auto-detection."""

import json
import os

import pytest

from jarfis.detect import _add_unique, _grep_file, _load_package_json, detect


class TestAddUnique:
    def test_adds_new_item(self):
        lst = ["a"]
        _add_unique(lst, "b")
        assert lst == ["a", "b"]

    def test_no_duplicate(self):
        lst = ["a", "b"]
        _add_unique(lst, "a")
        assert lst == ["a", "b"]


class TestGrepFile:
    def test_finds_pattern(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello world spring-boot")
        assert _grep_file(str(f), "spring-boot") is True

    def test_pattern_not_found(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello world")
        assert _grep_file(str(f), "spring-boot") is False

    def test_nonexistent_file(self):
        assert _grep_file("/nonexistent/file.txt", "pattern") is False


class TestLoadPackageJson:
    def test_loads_dependencies(self, tmp_path):
        pkg = {"dependencies": {"react": "^18"}, "devDependencies": {"jest": "^29"}}
        (tmp_path / "package.json").write_text(json.dumps(pkg))
        deps, data = _load_package_json(str(tmp_path))
        assert "react" in deps
        assert "jest" in deps

    def test_no_package_json(self, tmp_path):
        deps, data = _load_package_json(str(tmp_path))
        assert deps is None


class TestDetect:
    def test_nextjs_project(self, project_dir, capsys):
        detect(project_dir)
        output = json.loads(capsys.readouterr().out)
        assert "next.js" in output["frameworks"]
        assert "react" not in output["frameworks"]  # next takes priority
        assert "typescript" in output["languages"]
        assert "pnpm" in output["package_managers"]
        assert output["confidence"] == "high"

    def test_react_project(self, tmp_path, capsys):
        pkg = {"dependencies": {"react": "^18", "react-dom": "^18"}}
        (tmp_path / "package.json").write_text(json.dumps(pkg))
        (tmp_path / "package-lock.json").write_text("")
        detect(str(tmp_path))
        output = json.loads(capsys.readouterr().out)
        assert "react" in output["frameworks"]
        assert output["project_type"] == "frontend"
        assert "npm" in output["package_managers"]

    def test_python_project(self, tmp_path, capsys):
        (tmp_path / "requirements.txt").write_text("django==4.2\nflask==3.0\n")
        detect(str(tmp_path))
        output = json.loads(capsys.readouterr().out)
        assert "python" in output["languages"]
        assert "django" in output["frameworks"]
        assert "flask" in output["frameworks"]
        assert output["runtime"] == "python"

    def test_go_project(self, tmp_path, capsys):
        (tmp_path / "go.mod").write_text("module example.com/myapp\n\nrequire gin-gonic/gin v1.9")
        detect(str(tmp_path))
        output = json.loads(capsys.readouterr().out)
        assert "go" in output["languages"]
        assert "gin" in output["frameworks"]

    def test_empty_directory(self, tmp_path, capsys):
        detect(str(tmp_path))
        output = json.loads(capsys.readouterr().out)
        assert output["confidence"] == "low"
        assert output["project_type"] == "unknown"

    def test_java_maven_project(self, tmp_path, capsys):
        (tmp_path / "pom.xml").write_text("<project><dependency>spring-boot</dependency></project>")
        detect(str(tmp_path))
        output = json.loads(capsys.readouterr().out)
        assert "java" in output["languages"]
        assert "maven" in output["package_managers"]
        assert "spring-boot" in output["frameworks"]

    def test_rust_project(self, tmp_path, capsys):
        (tmp_path / "Cargo.toml").write_text('[package]\nname = "myapp"')
        detect(str(tmp_path))
        output = json.loads(capsys.readouterr().out)
        assert "rust" in output["languages"]
        assert "cargo" in output["package_managers"]

    def test_react_native_project(self, tmp_path, capsys):
        pkg = {"dependencies": {"react-native": "^0.72", "react": "^18"}}
        (tmp_path / "package.json").write_text(json.dumps(pkg))
        detect(str(tmp_path))
        output = json.loads(capsys.readouterr().out)
        assert "react-native" in output["frameworks"]
        assert output["project_type"] == "mobile"
