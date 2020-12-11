import os
import re

from lib.common import get_version, get_release


class DEBParserException(Exception):
    pass


class DEBParser:

    def __init__(self, orig_src, control):
        self.orig_src = orig_src
        self.control = os.path.join(orig_src, control)
        self.packages = []

    def get_verrel_from_changelog(self):
        # python-hid is in this case
        changelog = os.path.join(os.path.dirname(self.control), 'changelog')
        with open(changelog, "r") as fd:
            content = fd.read().strip()
        first_line = content.split('\n')[0]
        if re.match('.*\((.*)\).*', first_line):
            verrel = re.match('.*\((.*)\).*', first_line).group(1)
        else:
            raise DEBParserException(
                'Cannot determine version and release from changelog')
        return verrel

    def get_packages(self):
        self.parse()
        return self.packages

    def parse(self):
        if os.path.exists(self.control):
            with open(self.control, "r") as fd:
                content = fd.read().strip()
            packages = content.split("\n\n")
            if packages[0]:
                raw_pkg_info = [self.get_raw_info(pkg) for pkg in packages]
                for pkg in raw_pkg_info:
                    pkg_info = self.get_info(pkg)
                    if pkg_info:
                        self.packages.append(pkg_info)

    @staticmethod
    def get_raw_info(text):
        split_regex = re.compile(r"^[A-Za-z-]+:\s", flags=re.MULTILINE)
        keys = [key[:-2].lower() for key in split_regex.findall(text)]
        values = [value.strip() for value in re.split(split_regex, text)[1:]]

        if values:
            pkg_details = dict(zip(keys, values))
            return pkg_details

    def get_info(self, raw_info, filtered_arches=None):
        pkg = None
        name = raw_info.get("package")
        arch = raw_info.get("architecture")

        version = get_version(self.orig_src)
        release = get_release(self.orig_src)
        verrel = self.get_verrel_from_changelog()
        if not version or not release:
            verrel = verrel.split('-')
            version = verrel[0]
            # linux-utils does not have release
            if len(verrel) == 2:
                release = verrel[1]

        if name and arch:
            arch = arch.split()
            if not filtered_arches:
                filtered_arches = {'any', 'all', 'amd64'}
            available_arches = list(set(arch).intersection(filtered_arches))
            if available_arches:
                available_arches = [arch.replace('any', 'amd64') for arch in
                                    available_arches]
                pkg = {
                    "name": name,
                    "version": version,
                    "release": release,
                    "arch": available_arches
                }
            return pkg
