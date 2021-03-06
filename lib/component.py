import os
import subprocess

from lib.common import get_rpm_spec_files, get_deb_control_file
from lib.dist import QubesDist
from lib.rpm_parser import RPMParser
from lib.deb_parser import DEBParser


class QubesComponentException(Exception):
    pass


class QubesComponent:
    def __init__(self, name, orig_src, **kwargs):
        self.name = name
        self.orig_src = orig_src
        self.opts = kwargs

        self.releases = []
        self.branch = {}
        self.version = {}
        self.release = {}
        self.raw_packages_list = {}
        self.nvr_packages_list = {}

        # releases is the components/*.json "releases" key
        if "releases" in kwargs:
            for qubes_release, data in kwargs["releases"].items():
                self.releases.append(qubes_release)
                self.branch[qubes_release] = data.get("branch", 'master')
                self.raw_packages_list[qubes_release] = {
                    "dom0": data["dom0"],
                    "vm": data["vm"]
                }
            del kwargs["releases"]

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return self.name

    def to_dict(self):
        releases = {}
        for qubes_release in self.releases:
            data = self.raw_packages_list[qubes_release]
            releases[qubes_release] = {
                "branch": self.branch[qubes_release],
                "dom0": data["dom0"],
                "vm": data["vm"]
            }
        output = {
            self.name: {
                **self.opts,
                "releases": releases
            }
        }
        return output

    def _checkout(self, branch):
        cmd = 'git checkout -q {branch}'.format(branch=branch)
        subprocess.run(cmd, shell=True, cwd=self.orig_src, check=True,
                       stderr=subprocess.DEVNULL)

    def get_maintainers(self):
        return self.opts.get('maintainers', [])

    def is_plugin_type(self):
        return self.opts.get('plugin', 0) == 1

    def is_iso_component(self):
        return self.opts.get('iso-component', 0) == 1

    def is_windows_type(self):
        return 'windows' in self.name

    @staticmethod
    def get_nvr_rpm(name, version, release, arch):
        rpm = "{name}-{version}-{release}.{arch}.rpm".format(
                name=name, version=version, release=release, arch=arch)
        return rpm

    def get_nvr_deb(self, dist, name, version, release, arch, update=1):
        debian_ver = dist.get_version()
        if release:
            deb = "{name}_{version}-{release}+deb{debian_ver}u{update}_{arch}.deb".format(
                name=name, version=version, release=release,
                debian_ver=debian_ver, arch=arch, update=update)
        else:
            deb = "{name}_{version}+deb{debian_ver}u{update}_{arch}.deb".format(
                name=name, version=version, debian_ver=debian_ver,
                arch=arch, update=update)
        return deb

    def update(self, qubes_release, dist_dom0, dists_vm, branch=None):
        if not branch:
            branch = self.branch.get(qubes_release, 'master')
        try:
            self._checkout(branch)
        except subprocess.CalledProcessError:
            return
        self.branch[qubes_release] = branch

        self.raw_packages_list[qubes_release] = {"dom0": {}, "vm": {}}
        self.nvr_packages_list[qubes_release] = {"dom0": {}, "vm": {}}

        if self.name == "linux-template-builder":
            return

        # dom0
        if type(dist_dom0) == str:
            dist_dom0 = QubesDist(dist_dom0)
        packages_list = []
        specs = get_rpm_spec_files(self.orig_src, dist_dom0.name, "dom0")
        for spec in specs:
            rpm_parser = RPMParser(self.orig_src, spec)
            packages_list += rpm_parser.get_packages()
        self.raw_packages_list[qubes_release]["dom0"][dist_dom0.name] = []
        self.nvr_packages_list[qubes_release]["dom0"][dist_dom0.name] = []
        for pkg in packages_list:
            self.raw_packages_list[qubes_release]["dom0"][dist_dom0.name].append(pkg['name'])
            nvr_pkg = self.get_nvr_rpm(pkg['name'], pkg["version"], pkg["release"], pkg['arch'][0])
            self.nvr_packages_list[qubes_release]["dom0"][dist_dom0.name].append(nvr_pkg)

        # vm
        for dist in dists_vm:
            packages_list = []
            if type(dist) == str:
                dist = QubesDist(dist)
            if dist.is_rpm():
                specs = get_rpm_spec_files(self.orig_src, dist.name, "vm")
                for spec in specs:
                    rpm_parser = RPMParser(self.orig_src, spec)
                    packages_list += rpm_parser.get_packages()
            elif dist.is_deb():
                control = get_deb_control_file(self.orig_src, dist.name)
                if control:
                    control = os.path.join(self.orig_src, control)
                    deb_parser = DEBParser(self.orig_src, control)
                    packages_list = deb_parser.get_packages()
            self.raw_packages_list[qubes_release]["vm"][dist.name] = []
            self.nvr_packages_list[qubes_release]["vm"][dist.name] = []
            for pkg in packages_list:
                self.raw_packages_list[qubes_release]["vm"][dist.name].append(pkg['name'])
                if dist.is_rpm():
                    nvr_pkg = self.get_nvr_rpm(pkg['name'], pkg["version"], pkg["release"], pkg['arch'][0])
                elif dist.is_deb():
                    nvr_pkg = self.get_nvr_deb(dist, pkg['name'], pkg["version"], pkg["release"], pkg['arch'][0])
                else:
                    continue
                self.nvr_packages_list[qubes_release]["vm"][dist.name].append(nvr_pkg)

    def get_nvr_packages_list(self, qubes_release):
        packages_list = self.nvr_packages_list[qubes_release]
        return packages_list

    def get_packages_list(self, qubes_release):
        packages_list = self.raw_packages_list[qubes_release]
        return packages_list
