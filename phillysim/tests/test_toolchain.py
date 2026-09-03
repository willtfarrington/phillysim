"""EP-13: the pinned toolchain installed from crafted archives and digests, no network.

A fake opener serves a crafted JDK archive and a crafted jar; the pins are overridden
to the crafted bytes' digests, so the install path runs exactly as against GitHub:
allowlist, capped streaming, the byte count and SHA-256 compared before anything is
installed, the archive extracted under the zip-slip and bomb guards, ``java -version``
(a probe here) checked for the pinned version, the record written with relative paths.
The negatives feed a wrong digest, a slip member, a bomb, a wrong Java version, and a
symlink escaping the root, and require the refusal to leave nothing behind.
"""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import os
import tarfile
import zipfile
from dataclasses import replace
from pathlib import Path

import pytest
from typer.testing import CliRunner

from phillysim.cli import app
from phillysim.guards import GuardError, Limits, check_url_allowed, extract_tar, inspect_tar
from phillysim.routing import toolchain as tc
from phillysim.routing.toolchain import (
    ALLOWLIST,
    JAR,
    JAR_SHA256,
    JDK_ARCHIVES,
    JDK_DIR_NAME,
    JDK_LIMITS,
    JDK_VERSION,
    RECORD_NAME,
    Toolchain,
    ToolchainError,
)

JAVA_VERSION_OUTPUT = (
    'openjdk version "21.0.12.1" 2026-08-19 LTS\n'
    "OpenJDK Runtime Environment Temurin-21.0.12.1+1 (build 21.0.12.1+1-LTS)\n"
    "OpenJDK 64-Bit Server VM Temurin-21.0.12.1+1 (build 21.0.12.1+1-LTS, mixed mode, sharing)"
)
OLD_JAVA_OUTPUT = 'openjdk version "17.0.2" 2022-01-18\n'


def good_probe(_java: Path) -> str:
    return JAVA_VERSION_OUTPUT


def old_probe(_java: Path) -> str:
    return OLD_JAVA_OUTPUT


class FakeResponse:
    def __init__(self, data: bytes) -> None:
        self._buffer = io.BytesIO(data)
        self.status = 200
        self.headers = {"Content-Length": str(len(data))}

    def read(self, size: int = -1) -> bytes:
        return self._buffer.read(size)

    def close(self) -> None:
        pass


class FakeOpener:
    def __init__(self, routes: dict[str, bytes]) -> None:
        self.routes = routes
        self.calls: list[str] = []

    def __call__(self, url: str, allowlist, timeout: float) -> FakeResponse:
        check_url_allowed(url, allowlist)
        self.calls.append(url)
        return FakeResponse(self.routes[url])


def zip_bytes(members: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in members.items():
            zf.writestr(name, data)
    return buffer.getvalue()


def jdk_members(root: str = JDK_DIR_NAME) -> dict[str, bytes]:
    return {
        f"{root}/bin/java.exe": os.urandom(4096),
        f"{root}/bin/server/jvm.dll": os.urandom(4096),
        f"{root}/lib/modules": os.urandom(8192),
        f"{root}/release": b'JAVA_VERSION="21.0.12.1"\n',
    }


def pins_for(jdk: bytes, jar: bytes, platform: str = "windows") -> dict[str, tc.Archive]:
    archive = JDK_ARCHIVES[platform]
    return {
        archive.file_name: replace(archive, bytes=len(jdk), sha256=hashlib.sha256(jdk).hexdigest()),
        JAR.file_name: replace(JAR, bytes=len(jar), sha256=hashlib.sha256(jar).hexdigest()),
    }


@pytest.fixture
def crafted() -> tuple[bytes, bytes, FakeOpener, dict[str, tc.Archive]]:
    jdk = zip_bytes(jdk_members())
    jar = os.urandom(20_000)
    opener = FakeOpener({JDK_ARCHIVES["windows"].url: jdk, JAR.url: jar})
    return jdk, jar, opener, pins_for(jdk, jar)


def install(home: Path, opener, pins, probe=good_probe, platform: str = "windows"):
    chain = Toolchain(home, platform)
    return chain, tc.install(chain, opener=opener, pins=pins, java_version=probe)


# --- the pins -----------------------------------------------------------------------------


def test_pins_are_adr_0008s() -> None:
    windows, linux = JDK_ARCHIVES["windows"], JDK_ARCHIVES["linux"]
    assert (windows.bytes, windows.sha256) == (
        205_073_461,
        "f9d6e191ab098c0d416e7d588a24420a8621cd2f4720dab2459b8b7b2d2d8b4e",
    )
    assert (linux.bytes, linux.sha256) == (
        207_473_347,
        "ce79869e1307ed8ee1e2baa86a412b1eb5b75d10a01006d788a6f968bcfaee94",
    )
    assert windows.file_name == "OpenJDK21U-jdk_x64_windows_hotspot_21.0.12.1_1.zip"
    assert linux.file_name == "OpenJDK21U-jdk_x64_linux_hotspot_21.0.12.1_1.tar.gz"
    assert (JAR.file_name, JAR.bytes, JAR_SHA256) == (
        "r5-v7.5.1-r5py-all.jar",
        64_437_972,
        "d50be106cadd7b636cfc0e209052767d7df570629f79fdf98ecd5cf5d2d89be7",
    )
    assert JDK_VERSION == "21.0.12.1" and JDK_DIR_NAME == "jdk-21.0.12.1+1"
    assert JDK_LIMITS == Limits(256 * 1024**2, 1024**3, 10.0, 2_000)
    assert tc.JAR_MAX_BYTES == 128 * 1024**2


def test_every_url_passes_the_allowlist_and_only_https() -> None:
    for url in (*(a.url for a in JDK_ARCHIVES.values()), JAR.url):
        assert check_url_allowed(url, ALLOWLIST) == url
        with pytest.raises(GuardError):
            check_url_allowed(url.replace("https://", "http://"), ALLOWLIST)
    with pytest.raises(GuardError):
        check_url_allowed("https://example.com/r5.jar", ALLOWLIST)


def test_platform_key() -> None:
    assert tc.platform_key("win32") == "windows"
    assert tc.platform_key("linux") == "linux"
    with pytest.raises(ToolchainError):
        tc.platform_key("darwin")


def test_default_home_is_the_project_directory() -> None:
    home = tc.default_home()
    assert (home / "pyproject.toml").is_file() and home.name == "phillysim"


# --- install -----------------------------------------------------------------------------


def test_install_from_crafted_archives_lands_only_in_the_two_directories(
    tmp_path: Path, crafted, monkeypatch: pytest.MonkeyPatch
) -> None:
    jdk, jar, opener, pins = crafted
    path_before = os.environ.get("PATH")
    chain, record = install(tmp_path, opener, pins)
    assert os.environ.get("PATH") == path_before
    with zipfile.ZipFile(io.BytesIO(jdk)) as zf:
        assert chain.java.read_bytes() == zf.read(f"{JDK_DIR_NAME}/bin/java.exe")
    assert chain.jar.read_bytes() == jar
    assert sorted(p.name for p in tmp_path.iterdir()) == [".jdk", ".r5", RECORD_NAME]
    assert [p.name for p in chain.jdk_root.iterdir()] == [JDK_DIR_NAME]  # no scratch left
    assert [p.name for p in (tmp_path / ".r5").iterdir()] == [JAR.file_name]  # no .part
    assert opener.calls == [JDK_ARCHIVES["windows"].url, JAR.url]
    text = chain.record_path.read_text("utf-8")
    saved = json.loads(text)
    assert saved == record
    assert saved["jdk"]["dir"] == f".jdk/{JDK_DIR_NAME}"
    assert saved["jar"]["path"] == f".r5/{JAR.file_name}"
    assert saved["jdk"]["java_version"].startswith('openjdk version "21.0.12.1"')
    assert saved["jdk"]["sha256"] == JDK_ARCHIVES["windows"].sha256  # the pin, as ADR-0008
    assert saved["jar"]["sha256"] == JAR_SHA256
    assert str(tmp_path) not in text and tmp_path.as_posix() not in text
    assert saved["platform"] == "windows" and saved["schema_version"] == 1
    assert set(saved["python"]) == {"r5py", "jpype1", "psutil"}


def test_install_is_idempotent_and_downloads_nothing_twice(tmp_path: Path, crafted) -> None:
    _jdk, _jar, opener, pins = crafted
    chain, first = install(tmp_path, opener, pins)
    opener.calls.clear()
    second = tc.install(chain, opener=opener, pins=pins, java_version=good_probe)
    assert opener.calls == []
    assert second["jdk"]["downloaded"] is False and second["jar"]["downloaded"] is False
    assert first["jdk"]["downloaded"] is True and first["jar"]["downloaded"] is True


def test_wrong_jar_digest_is_refused_and_the_download_deleted(tmp_path: Path, crafted) -> None:
    jdk, jar, _opener, pins = crafted
    tampered = FakeOpener({JDK_ARCHIVES["windows"].url: jdk, JAR.url: jar[:-1] + b"\0"})
    with pytest.raises(ToolchainError, match="the pin is"):
        install(tmp_path, tampered, pins)
    assert not (tmp_path / ".r5").exists() or list((tmp_path / ".r5").iterdir()) == []
    assert not (tmp_path / RECORD_NAME).exists()
    assert Toolchain(tmp_path, "windows").java.is_file()  # the JDK, verified, stayed


def test_wrong_jdk_digest_installs_nothing(tmp_path: Path, crafted) -> None:
    jdk, jar, _opener, pins = crafted
    tampered = FakeOpener({JDK_ARCHIVES["windows"].url: jdk + b"x", JAR.url: jar})
    with pytest.raises(ToolchainError, match="the download was deleted"):
        install(tmp_path, tampered, pins)
    assert not Toolchain(tmp_path, "windows").jdk_dir.exists()
    assert not list((tmp_path / ".jdk").rglob("*")) if (tmp_path / ".jdk").exists() else True
    assert not (tmp_path / ".r5").exists()  # the jar is fetched only after the JDK


def test_short_download_is_a_byte_count_mismatch(tmp_path: Path, crafted) -> None:
    jdk, jar, _opener, pins = crafted
    short = FakeOpener({JDK_ARCHIVES["windows"].url: jdk, JAR.url: jar[:-10]})
    with pytest.raises(ToolchainError, match="delivered 19990 bytes"):
        install(tmp_path, short, pins)


def test_zip_slip_member_is_refused(tmp_path: Path, crafted) -> None:
    _jdk, jar, _opener, _pins = crafted
    evil = zip_bytes({**jdk_members(), "../evil.txt": b"boom"})
    opener = FakeOpener({JDK_ARCHIVES["windows"].url: evil, JAR.url: jar})
    with pytest.raises(ToolchainError, match="zip_slip"):
        install(tmp_path, opener, pins_for(evil, jar))
    assert not (tmp_path.parent / "evil.txt").exists()
    assert not Toolchain(tmp_path, "windows").jdk_dir.exists()
    assert not (tmp_path / ".jdk" / ".extract").exists()
    assert not (tmp_path / ".jdk" / ".download").exists()


def test_bomb_is_refused_before_extraction(tmp_path: Path, crafted) -> None:
    _jdk, jar, _opener, _pins = crafted
    bomb = zip_bytes({**jdk_members(), f"{JDK_DIR_NAME}/lib/zeros": bytes(4 * 1024**2)})
    opener = FakeOpener({JDK_ARCHIVES["windows"].url: bomb, JAR.url: jar})
    with pytest.raises(ToolchainError, match="compression ratio"):
        install(tmp_path, opener, pins_for(bomb, jar))
    assert not Toolchain(tmp_path, "windows").jdk_dir.exists()


def test_wrong_java_version_is_refused(tmp_path: Path, crafted) -> None:
    _jdk, _jar, opener, pins = crafted
    with pytest.raises(ToolchainError, match="not 21.0.12.1"):
        install(tmp_path, opener, pins, probe=old_probe)
    assert not Toolchain(tmp_path, "windows").jdk_dir.exists()


def test_two_jdk_roots_in_one_archive_are_refused(tmp_path: Path, crafted) -> None:
    _jdk, jar, _opener, _pins = crafted
    twins = zip_bytes({**jdk_members(), **jdk_members("other-jdk")})
    opener = FakeOpener({JDK_ARCHIVES["windows"].url: twins, JAR.url: jar})
    with pytest.raises(ToolchainError, match="2 JDK root"):
        install(tmp_path, opener, pins_for(twins, jar))


def test_existing_jdk_with_another_version_is_not_replaced(tmp_path: Path, crafted) -> None:
    _jdk, _jar, opener, pins = crafted
    chain = Toolchain(tmp_path, "windows")
    chain.java.parent.mkdir(parents=True)
    chain.java.write_bytes(b"stale")
    with pytest.raises(ToolchainError, match="delete it by hand"):
        tc.install(chain, opener=opener, pins=pins, java_version=old_probe)
    assert chain.java.read_bytes() == b"stale" and opener.calls == []


# --- the Linux tarball path ----------------------------------------------------------------


def tar_gz_bytes(members: dict[str, bytes | str]) -> bytes:
    """``str`` values are symlink targets."""
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w") as tf:
        for name, data in members.items():
            info = tarfile.TarInfo(name)
            if isinstance(data, str):
                info.type = tarfile.SYMTYPE
                info.linkname = data
                tf.addfile(info)
            else:
                info.size = len(data)
                info.mode = 0o755 if name.endswith("/java") else 0o644
                tf.addfile(info, io.BytesIO(data))
    return gzip.compress(raw.getvalue(), mtime=0)


def linux_members(root: str = JDK_DIR_NAME) -> dict[str, bytes | str]:
    return {
        f"{root}/bin/java": os.urandom(4096),
        f"{root}/lib/libjsig.so": os.urandom(2048),
        f"{root}/lib/server/libjvm.so": os.urandom(4096),
        f"{root}/lib/server/libjsig.so": "../libjsig.so",  # Temurin ships this symlink
        f"{root}/release": b'JAVA_VERSION="21.0.12.1"\n',
    }


def test_linux_tarball_installs_with_its_in_root_symlink(tmp_path: Path) -> None:
    jdk = tar_gz_bytes(linux_members())
    jar = os.urandom(10_000)
    opener = FakeOpener({JDK_ARCHIVES["linux"].url: jdk, JAR.url: jar})
    chain, record = install(tmp_path, opener, pins_for(jdk, jar, "linux"), platform="linux")
    assert chain.java.is_file()
    link = chain.jdk_dir / "lib" / "server" / "libjsig.so"
    assert link.exists()  # a symlink, or a copy where the platform refuses symlinks
    assert link.read_bytes() == (chain.jdk_dir / "lib" / "libjsig.so").read_bytes()
    assert record["jdk"]["archive"].endswith(".tar.gz") and record["platform"] == "linux"


def test_tar_symlink_escaping_the_root_is_refused(tmp_path: Path) -> None:
    evil = tar_gz_bytes({**linux_members(), f"{JDK_DIR_NAME}/lib/etc": "../../../../etc"})
    archive = tmp_path / "evil.tar.gz"
    archive.write_bytes(evil)
    with pytest.raises(GuardError, match="escapes the root"):
        extract_tar(archive, tmp_path / "out", JDK_LIMITS)
    assert not (tmp_path / "out" / JDK_DIR_NAME / "lib" / "etc").exists()


def test_tar_absolute_member_hard_link_and_bomb_are_refused(tmp_path: Path) -> None:
    absolute = tar_gz_bytes({"/etc/passwd": b"x", **linux_members()})
    (tmp_path / "a.tar.gz").write_bytes(absolute)
    with pytest.raises(GuardError, match="absolute path"):
        extract_tar(tmp_path / "a.tar.gz", tmp_path / "out", JDK_LIMITS)
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w") as tf:
        info = tarfile.TarInfo(f"{JDK_DIR_NAME}/bin/java")
        info.size = 4
        tf.addfile(info, io.BytesIO(b"java"))
        link = tarfile.TarInfo(f"{JDK_DIR_NAME}/bin/hard")
        link.type = tarfile.LNKTYPE
        link.linkname = f"{JDK_DIR_NAME}/bin/java"
        tf.addfile(link)
    (tmp_path / "h.tar.gz").write_bytes(gzip.compress(raw.getvalue()))
    with pytest.raises(GuardError, match="only files, directories, and symlinks"):
        inspect_tar(tmp_path / "h.tar.gz", JDK_LIMITS)
    bomb = tar_gz_bytes({**linux_members(), f"{JDK_DIR_NAME}/lib/zeros": bytes(4 * 1024**2)})
    (tmp_path / "b.tar.gz").write_bytes(bomb)
    with pytest.raises(GuardError, match="compression ratio"):
        inspect_tar(tmp_path / "b.tar.gz", JDK_LIMITS)
    (tmp_path / "not.tar.gz").write_bytes(b"not a tar at all")
    with pytest.raises(GuardError, match="not a tar archive"):
        inspect_tar(tmp_path / "not.tar.gz", JDK_LIMITS)


# --- check -------------------------------------------------------------------------------


def test_check_reports_every_component(tmp_path: Path, crafted) -> None:
    _jdk, _jar, opener, pins = crafted
    chain = Toolchain(tmp_path, "windows")
    missing = tc.check(chain, java_version=good_probe, package_version=lambda n: "1")
    assert not missing.ok
    assert [c.name for c in missing.checks] == ["jdk", "jar", "record", "routing"]
    assert [c.ok for c in missing.checks] == [False, False, False, True]
    assert "toolchain install" in missing.checks[0].detail
    assert missing.lines()[-1] == "toolchain: not usable"

    tc.install(chain, opener=opener, pins=pins, java_version=good_probe)
    # The crafted jar is not the pinned jar, so `check` (which compares against ADR-0008's
    # digest, never against a test pin) must say so; the JDK and record checks pass.
    report = tc.check(chain, java_version=good_probe, package_version=lambda n: None)
    by_name = {c.name: c for c in report.checks}
    assert by_name["jdk"].ok and "21.0.12.1" in by_name["jdk"].detail
    assert not by_name["jar"].ok and JAR_SHA256 in by_name["jar"].detail
    assert by_name["record"].ok
    assert (
        not by_name["routing"].ok
        and "uv sync --locked --group routing" in by_name["routing"].detail
    )

    old = tc.check(chain, java_version=old_probe, package_version=lambda n: "1")
    assert not {c.name: c for c in old.checks}["jdk"].ok


def test_cli_check_and_install_report(tmp_path: Path, monkeypatch) -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["toolchain", "check", "--home", str(tmp_path)])
    assert result.exit_code == 1, result.output
    assert "FAIL jdk" in result.output and "FAIL jar" in result.output
    assert "toolchain: not usable" in result.output

    # The CLI installs for the platform it runs on: craft that platform's archive.
    platform = tc.platform_key()
    jdk = zip_bytes(jdk_members()) if platform == "windows" else tar_gz_bytes(linux_members())
    jar = os.urandom(10_000)
    pins = pins_for(jdk, jar, platform)
    opener = FakeOpener({JDK_ARCHIVES[platform].url: jdk, JAR.url: jar})
    monkeypatch.setattr(tc, "urllib_open", opener)
    monkeypatch.setattr(tc, "java_version_string", good_probe)
    monkeypatch.setattr(tc, "JAR", pins[JAR.file_name])
    monkeypatch.setitem(tc.JDK_ARCHIVES, platform, pins[JDK_ARCHIVES[platform].file_name])
    result = runner.invoke(
        app, ["toolchain", "install", "--home", str(tmp_path)], catch_exceptions=False
    )
    assert "verified against the pin" in result.output, result.output
    assert Toolchain(tmp_path, platform).java.is_file()
    # The post-install check compares the jar against ADR-0008's digest, never a test pin,
    # so the crafted jar is reported as not the pinned one.
    assert "ok   jdk" in result.output and "FAIL jar" in result.output, result.output
