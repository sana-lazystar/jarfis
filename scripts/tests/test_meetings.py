"""Tests for jarfis.meetings — recent meetings list."""

import json
import os

import pytest

from jarfis.meetings import main


class TestMain:
    def test_empty_meetings_dir(self, jarfis_env, capsys):
        main([])
        output = json.loads(capsys.readouterr().out)
        assert output == []

    def test_no_meetings_dir(self, jarfis_env, capsys):
        # Remove meetings dir
        os.rmdir(jarfis_env["meetings_dir"])
        main([])
        output = json.loads(capsys.readouterr().out)
        assert output == []

    def test_lists_meetings_with_summary(self, jarfis_env, capsys):
        meeting_dir = os.path.join(jarfis_env["meetings_dir"], "20260324-test-meeting")
        os.makedirs(meeting_dir)
        summary = (
            "---\n"
            "date: 2026-03-24\n"
            "meeting_name: Test Meeting\n"
            "idea: API migration discussion\n"
            "---\n\n"
            "# Meeting Summary\n"
        )
        with open(os.path.join(meeting_dir, "summary.md"), "w") as f:
            f.write(summary)

        main(["3"])
        output = json.loads(capsys.readouterr().out)
        assert len(output) == 1
        assert output[0]["date"] == "2026-03-24"
        assert output[0]["summary"] == "API migration discussion"

    def test_date_fallback_from_dirname(self, jarfis_env, capsys):
        meeting_dir = os.path.join(jarfis_env["meetings_dir"], "20260315-no-frontmatter")
        os.makedirs(meeting_dir)
        with open(os.path.join(meeting_dir, "summary.md"), "w") as f:
            f.write("# Just a heading\n\nSome content")

        main(["1"])
        output = json.loads(capsys.readouterr().out)
        assert len(output) == 1
        assert output[0]["date"] == "2026-03-15"

    def test_count_limits_results(self, jarfis_env, capsys):
        for i in range(5):
            d = os.path.join(jarfis_env["meetings_dir"], f"2026032{i}-meeting-{i}")
            os.makedirs(d)
            with open(os.path.join(d, "summary.md"), "w") as f:
                f.write(f"---\ndate: 2026-03-2{i}\n---\n# M{i}")

        main(["2"])
        output = json.loads(capsys.readouterr().out)
        assert len(output) == 2
