import os
import subprocess
import tempfile
import json

from lib.common import get_version, get_release

class RPMParserException(Exception):
    pass


class RPMParser:

    def __init__(self, orig_src, spec):
        self.orig_src = orig_src
        self.spec = os.path.join(orig_src, spec)
        self.packages = []

    def get_packages(self):
        self.parse()
        return self.packages

    def parse(self):
        filespec = self.spec
        if os.path.exists(self.spec + '.in'):
            filespec = self.spec + '.in'
        raw_pkg_infos = self.get_raw_infos(filespec)
        if raw_pkg_infos:
            for raw_info in raw_pkg_infos:
                pkg_info = self.get_info(raw_info)
                if pkg_info:
                    self.packages.append(pkg_info)

    def get_raw_infos(self, filespec):
        if os.path.exists(filespec):
            with open(filespec, "r") as fd:
                content = self.get_rendered_spec(fd.read().strip())
            curr_dir = os.path.dirname(filespec)
            with tempfile.NamedTemporaryFile(dir=curr_dir) as fd_spec:
                fd_spec.write(content.encode('utf-8'))
                fd_spec.seek(0)
                spec = fd_spec.name
                cmd = ["/usr/bin/rpmspec", "--builtrpms", "-q", "--qf",
                       '\{"name": "%{name}", "version": "%{version}", "release": "%{release}", "arch": "%{arch}"\}\n', spec]
                kwargs = {
                    "cwd": curr_dir,
                    "text": True
                }
                if os.environ.get('DEBUG') != 1:
                    kwargs["stderr"] = subprocess.DEVNULL
                output = subprocess.check_output(cmd, **kwargs).rstrip('\n')
                return output.split('\n')

    @staticmethod
    def get_info(raw_info, filtered_arches=None):
        raw_info = json.loads(raw_info)
        pkg = None
        name = raw_info["name"]
        version = raw_info["version"]
        release = raw_info["release"]
        arch = raw_info.get("arch", None)

        if not version:
            raise RPMParserException('Cannot determine version')
        if not release:
            raise RPMParserException('Cannot determine release')
        if not filtered_arches:
            filtered_arches = ['noarch', 'x86_64']

        if arch in filtered_arches:
            pkg = {
                "name": name,
                "version": version,
                "release": release,
                "arch": [arch]
            }
        return pkg

    def get_rendered_spec(self, content):
        version = get_version(self.orig_src)
        release = get_release(self.orig_src)
        if not version:
            version = ''
        if not release:
            release = ''
        content = content.replace('@VERSION@', version)
        for i in range(1, 8):
            content = content.replace('@VERSION%d@' % i, version)
        content = content.replace('@REL@', release)
        for i in range(1, 8):
            content = content.replace('@REL%d@' % i, release)
        content = content.replace('@CHANGELOG@', '')
        content = content.replace('@BACKEND_VMM@', 'xen')
        return content
