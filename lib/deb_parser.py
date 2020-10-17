import os
import re


class DEBParser:

    def __init__(self, control):
        self.control = os.path.abspath(control)
        self.packages = []

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

    @staticmethod
    def get_info(raw_info, filtered_arches=None):
        pkg = None
        name = raw_info.get("package")
        arch = raw_info.get("architecture")
        if name and arch:
            arch = arch.split()
            if not filtered_arches:
                filtered_arches = {'any', 'all', 'amd64'}
            available_arches = list(set(arch).intersection(filtered_arches))
            if available_arches:
                available_arches = [arch.replace('all', 'any') for arch in
                                    available_arches]
                pkg = {
                    "name": name,
                    "arch": available_arches
                }
            return pkg
