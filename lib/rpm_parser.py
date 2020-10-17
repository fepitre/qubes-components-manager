import os
import subprocess
import tempfile
import json


class RPMParser:

    def __init__(self, spec):
        self.spec = os.path.abspath(spec)
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
                if os.environ.get('DEBUG') == 1:
                    cmd = "/usr/bin/rpmspec -q --qf '\{\"name\": \"%{name}\",\"arch\": \"%{arch}\"\}\n' " + spec
                else:
                    cmd = "/usr/bin/rpmspec -q --qf '\{\"name\": \"%{name}\",\"arch\": \"%{arch}\"\}\n' " + spec + " 2>/dev/null"
                output = subprocess.check_output([cmd], cwd=curr_dir,
                                                 shell=True,
                                                 text=True).rstrip('\n')
                return output.split('\n')

    @staticmethod
    def get_info(raw_info, filtered_arches=None):
        raw_info = json.loads(raw_info)
        pkg = None
        name = raw_info["name"]
        arch = raw_info.get("arch", None)

        if not filtered_arches:
            filtered_arches = ['noarch', 'x86_64']

        if arch in filtered_arches:
            pkg = {
                "name": name,
                "arch": [arch]
            }
        return pkg

    @staticmethod
    def get_rendered_spec(content):
        content = content.replace('@VERSION@', '1.0.0')
        for i in range(1, 8):
            content = content.replace('@VERSION%d@' % i, '1.0.0')
        content = content.replace('@REL@', '1')
        for i in range(1, 8):
            content = content.replace('@REL%d@' % i, '1')
        content = content.replace('@CHANGELOG@', '')
        content = content.replace('@BACKEND_VMM@', 'xen')
        return content
