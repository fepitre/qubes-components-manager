import os

from lib.common import get_rpm_spec_files, get_deb_control_file
from lib.dist import DEBIAN
from lib.rpm_parser import RPMParser
from lib.deb_parser import DEBParser


class QubesComponent:
    def __init__(self, name, branch, orig_src, **kwargs):
        self.name = name
        self.branch = branch
        self.orig_src = orig_src
        self.opts = kwargs

        self.dom0 = {}
        self.vms = {}

        self.version = None
        self.release = None

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return self.name

    def get_version(self):
        if not self.version:
            try:
                with open(os.path.join(self.orig_src, 'version')) as fd:
                    version = fd.read().split('\n')[0]
                self.version = version
            except FileNotFoundError:
                pass
        return self.version

    def get_release(self):
        if not self.release:
            try:
                with open(os.path.join(self.orig_src, 'rel')) as fd:
                    release = fd.read().split('\n')[0]
            except FileNotFoundError:
                pass
        return self.release

    def get_maintainers(self):
        return self.opts.get('maintainers', [])

    def is_plugin_type(self):
        return self.opts.get('plugin', 0) == 1

    def is_iso_component(self):
        return self.opts.get('iso-component', 0) == 1

    def is_windows_type(self):
        return 'windows' in self.name

    def get_nvr_rpm(self, name, dist, arch):
        version = self.get_version()
        release = self.get_release()
        if not release:
            release = 1
        rpm = None
        if version:
            rpm = "{name}-{version}-{release}.{dist}.{arch}.rpm".format(
                name=name, version=version, release=release, dist=dist,
                arch=arch)
        return rpm

    def get_nvr_deb(self, name, dist, arch, update=1):
        debian_ver = DEBIAN[dist].split('-')[1]
        version = self.get_version()
        release = self.get_release()
        deb = None
        if version:
            if release:
                deb = "{name}_{version}-{release}+deb{debian_ver}u{update}_{arch}.deb".format(
                    name=name, version=version, release=release,
                    debian_ver=debian_ver, arch=arch, update=update)
            else:
                deb = "{name}_{version}+deb{debian_ver}u{update}_{arch}.deb".format(
                    name=name, version=version, debian_ver=debian_ver,
                    arch=arch, update=update)
        return deb

    # WIP: Refactor below
    def fetch_component_packages_dom0(self, dist):
        packages_list = []
        specs = get_rpm_spec_files(self.orig_src, dom0=dist.name)
        for spec in specs:
            rpm_parser = RPMParser(os.path.join(self.orig_src, spec))
            packages_list += rpm_parser.get_packages()

        return packages_list

    def fetch_component_packages_vm(self, dist):
        packages_list = []
        if dist.name.startswith('fc') or dist.name.startswith('centos'):
            specs = get_rpm_spec_files(self.orig_src, vm=dist.name)
            for spec in specs:
                rpm_parser = RPMParser(os.path.join(self.orig_src, spec))
                packages_list += rpm_parser.get_packages()
        elif DEBIAN.get(dist.name, None):
            control = get_deb_control_file(self.orig_src, dist.name)
            if control:
                control = os.path.join(self.orig_src, control)
                deb_parser = DEBParser(control)
                packages_list = deb_parser.get_packages()

        return packages_list

    def fetch_packages_dom0(self, dists):
        for dist in dists:
            self.dom0[dist.name] = self.fetch_component_packages_dom0(dist)

    def fetch_packages_vms(self, dists):
        for dist in dists:
            self.vms[dist.name] = self.fetch_component_packages_vm(dist)

    def fetch_all_packages(self, dom0, vms):
        self.fetch_packages_dom0(dom0)
        self.fetch_packages_vms(vms)

    def get_packages_names_dom0(self, dists):
        packages_names = {}
        for dist in dists:
            packages_names[dist.name] = [pkg["name"] for pkg in
                                         self.dom0.get(dist.name, [])]

        return packages_names

    def get_packages_names_vms(self, dists):
        packages_names = {}
        for dist in dists:
            packages_names[dist.name] = [pkg["name"] for pkg in
                                         self.vms.get(dist.name, [])]

        return packages_names

    def get_packages(self, dist, components):
        pkgs = []
        for component in components.get(dist.name, []):
            pkg = None
            if dist.is_rpm():
                pkg = self.get_nvr_rpm(component['name'], dist.name,
                                       component['arch'][0])
            if dist.is_deb():
                pkg = self.get_nvr_deb(component['name'], dist.name,
                                       component['arch'][0])
            if pkg:
                pkgs.append(pkg)
        return pkgs

    def get_packages_dom0(self, dist):
        return self.get_packages(dist, self.dom0)

    def get_packages_vms(self, dist):
        return self.get_packages(dist, self.vms)
