#!/usr/bin/env python3

import os
import pathlib

import requests

try:
    from packaging.version import parse
except ImportError:
    from pip._vendor.packaging.version import parse


REQUIREMENTS_FILE = os.path.join(pathlib.Path(os.path.dirname(os.path.realpath(__file__))).parent, "requirements.txt")


def get_version(package):
    r = requests.get(f"https://pypi.python.org/pypi/{package}/json")
    version = parse("0")
    if r.status_code == 200:
        response = r.json()
        releases = response.get("releases", [])
        for release in releases:
            ver = parse(release)
            if not ver.is_prerelease:
                version = max(version, ver)
    return version


def get_requirements_packages():
    packages = []
    with open(REQUIREMENTS_FILE, "r") as f:
        for line in f:
            if line:
                package = line[: line.find("==")]
                version = line[line.find("==") + 2 :].rstrip()
                if "[" in package:
                    package = package[: package.find("[")]
                packages.append((package, version))
    return packages


if __name__ == "__main__":
    for package in get_requirements_packages():
        latest_version = str(get_version(package[0]))
        if latest_version != package[1]:
            print(f"Newer stable version of {package[0]}: {latest_version}")
