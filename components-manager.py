#!/usr/bin/python3

import os
import sys
import json
import argparse

from jinja2 import Template

from lib.component import QubesComponent
from lib.dist import QubesDist

AVAILABLE_FORMAT_ITEMS = [
    "component", "qubes_release", "package_set", "dist", "packages"]


class QubesComponentsManagerException(Exception):
    pass


class ComponentsManagerCli:
    def __init__(self, releasefile, components_folder, qubes_src):
        self.releasefile = releasefile
        self.components_folder = components_folder
        self.qubes_src = qubes_src

        self.data = {}
        self.releases = {}
        self.dom0 = {}
        self.vm = {}
        self.components = []

    def init(self):
        with open(self.releasefile) as fd:
            self.data = json.loads(fd.read())

        self.data["components_list"] = self.data["components"]
        self.data["components"] = {}
        self.releases = self.data["releases"].keys()

        for rel_key, rel_val in self.data["releases"].items():
            # dom0 dist
            self.dom0[rel_key] = []
            for dist in rel_val["dom0"]:
                self.dom0[rel_key].append(QubesDist(dist))

            # vms dist
            self.vm[rel_key] = []
            for dist in rel_val["vm"]:
                self.vm[rel_key].append(QubesDist(dist))

        # qubes components
        for component in self.data["components_list"]:
            try:
                component_file = os.path.join(
                    self.components_folder, '%s.json' % component)
                orig_src = os.path.join(self.qubes_src, component)
                with open(component_file) as fd:
                    component_data = json.loads(fd.read()).get(component, {})
                self.data["components"][component] = component_data
                kwargs = component_data
                self.components.append(QubesComponent(
                    name=component,
                    orig_src=orig_src,
                    **kwargs)
                )
            except FileNotFoundError:
                pass

    def is_devel_version(self, release):
        return self.data["releases"][release].get("devel", 0)

    def get_dom0(self, release):
        return self.dom0[release]

    def get_vm(self, release):
        return self.vm[release]

    def get_branches_conf(self, release):
        branches = []
        for component in self.components:
            if release not in component.releases:
                continue
            if component.branch[release] != "release%s" % release:
                if component.branch[release] == "master" and \
                        self.is_devel_version(release) == 1:
                    continue
                branches.append(
                    'BRANCH_%s = %s' % (component.name.replace('-', '_'),
                                        component.branch[release]))

        return branches

    def get_maintainers_conf(self, release):
        maintainers = {}
        for component in self.components:
            if release not in component.releases:
                continue
            for maintainer in component.get_maintainers():
                if not maintainers.get(maintainer, None):
                    maintainers[maintainer] = []
                maintainers[maintainer].append(component.name)

        maintainers_conf = []
        for key, val in maintainers.items():
            maintainers_conf.append(
                'ALLOWED_COMPONENTS_%s = %s' % (key, ' '.join(val)))

        return maintainers_conf

    def get_template_labels_conf(self, release):
        template_labels = []
        for dist in self.get_dom0(release) + self.get_vm(release):
            template_labels += dist.get_labels()

        return template_labels

    def get_template_alias_conf(self, release):
        template_aliases = []
        for dist in self.get_vm(release):
            template_aliases += dist.get_alias()

        return template_aliases

    def generate_conf(self, release, conf_file):
        builder_plugins = []
        iso_components = []
        windows_components = []
        filtered_components = []
        for component in self.components:
            if release not in component.releases:
                continue
            if component.is_plugin_type():
                builder_plugins.append(component)
            if component.is_iso_component():
                iso_components.append(component)
            if component.is_windows_type():
                windows_components.append(component)

            if component not in builder_plugins + iso_components + \
                    windows_components:
                filtered_components.append(component)

        with open('template.conf.jinja', 'r') as template_fd:
            template = Template(template_fd.read())

        conf = {
            "devel": self.is_devel_version(release),
            "release": release,
            "dist_dom0": self.get_dom0(release),
            "dists_vm": self.get_vm(release),
            "builder_plugins": builder_plugins,
            "iso_components": iso_components,
            "windows_components": windows_components,
            "components": filtered_components,
            "template_labels": self.get_template_labels_conf(release),
            "template_aliases": self.get_template_alias_conf(release),
            "branches": self.get_branches_conf(release),
            "maintainers": self.get_maintainers_conf(release)
        }

        generated_conf = template.render(**conf)
        with open(conf_file, 'w') as fd:
            fd.write(generated_conf)

    def get_component(self, name):
        for component in self.components:
            if component.name == name:
                return component

    def get_components_list(self):
        components = [component.name for component in self.components]
        return components

    def get_components(self):
        return self.components

    def get_components_from_name(self, components):
        output = []
        if 'all' in components:
            return self.components
        for component in components:
            component = self.get_component(component)
            if component:
                output.append(component)
        return output

    # release.json (order + release info) + components/*.json -> distfile.json
    def create_distfile(self, distfile):
        with open(self.releasefile) as fd:
            data = json.loads(fd.read())
            data["components"] = {}
        for component in self.data["components"]:
            try:
                component_file = os.path.join(
                    self.components_folder, '%s.json' % component)
                with open(component_file) as fd:
                    data["components"][component] = \
                        json.loads(fd.read()).get(component, {})
            except FileNotFoundError:
                pass
        with open(distfile, 'w') as fd:
            fd.write(json.dumps(data, indent=4))

    def add_component(self, name):
        content = {
            name: {
                "releases": {},
            }
        }
        for release in self.data["releases"].keys():
            if self.data["releases"][release].get("devel", 0):
                branch = 'master'
            else:
                branch = 'release%s' % release
            content[name]["releases"][release] = {
                "branch": branch,
                "dom0": {},
                "vm": {}
            }
        component_file = os.path.join(self.components_folder, '%s.json' % name)
        with open(component_file, 'w') as fd:
            fd.write(json.dumps(content, indent=4))

    def update_components(self, components):
        for component in self.get_components_from_name(components):
            print("-> Updating %s" % component)
            component_file = os.path.join(
                self.components_folder, '%s.json' % component.name)

            for qubes_release in component.releases:
                component.update(qubes_release, self.dom0[qubes_release][0],
                                 self.vm[qubes_release])

            with open(component_file, 'w') as fd:
                fd.write(json.dumps(component.to_dict(), indent=4))

    @staticmethod
    def get_packages_list(component, qubes_release, with_nvr=False):
        if with_nvr:
            packages_list = component.get_nvr_packages_list(qubes_release)
        else:
            packages_list = component.get_packages_list(qubes_release)
        return packages_list

    def get_components_packages_list(self, components, req_dist=None, raw=False,
                                     req_package_set=None, with_nvr=False,
                                     req_format=None, skip_empty=False,
                                     req_release=None):
        pkgs = {}
        pkgs_with_format = []

        if raw and not req_format:
            req_format = ["packages"]

        for component in self.get_components_from_name(components):
            pkgs[component.name] = {}
            for qubes_release in component.releases:
                if req_release and qubes_release != req_release:
                    continue
                packages_list = self.get_packages_list(
                    component, qubes_release, with_nvr)
                if raw:
                    requested_format = ':'.join('{%s}' % f for f in req_format)
                    for package_set in packages_list.keys():
                        if req_package_set and package_set != req_package_set:
                            continue
                        for dist in packages_list[package_set].keys():
                            if req_dist and dist not in req_dist:
                                continue
                            component_packages_list = \
                                packages_list[package_set][dist]
                            if skip_empty and not component_packages_list:
                                continue
                            pkgs_with_format.append(
                                requested_format.format(
                                    component=component.name,
                                    qubes_release=qubes_release,
                                    package_set=package_set,
                                    dist=dist,
                                    packages=' '.join(component_packages_list)
                                )
                            )
                if req_package_set:
                    if req_package_set == "dom0":
                        del packages_list["vm"]
                    else:
                        del packages_list["dom0"]
                pkgs[component.name][qubes_release] = {}
                for package_set in packages_list.keys():
                    filtered_list = {}
                    for k, v in packages_list[package_set].items():
                        if req_dist and k not in req_dist:
                            continue
                        if skip_empty and not v:
                            continue
                        filtered_list[k] = v
                    if filtered_list:
                        pkgs[component.name][qubes_release][package_set] = \
                            filtered_list
        if raw:
            output = pkgs_with_format
        else:
            output = pkgs
        return output


def get_args():
    parser = argparse.ArgumentParser('Qubes Components Manager')
    parser.add_argument(
        "--releasefile",
        help="Input release file ('release.json').",
        default='release.json',
    )
    parser.add_argument(
        "--components-folder",
        help="Input components folder ('components/*.json').",
        default=os.path.join(os.getcwd(), 'components')
    )
    parser.add_argument(
        "--qubes-src",
        help="Local path of Qubes sources.",
        default=os.path.join(os.getcwd(), 'qubes-builder/qubes-src')
    )

    subparser = parser.add_subparsers(dest='command')

    update_parser = subparser.add_parser('update', help='Update')
    update_parser.add_argument(
        "--packages-list",
        default='all',
        nargs='+',
        help="Update packages list for given components. 'all' is accepted."
    )

    generate_parser = subparser.add_parser('generate', help='Generate')
    generate_parser.add_argument(
        "--builder-conf",
        help="Destination file for generating qubes-builder configuration file."
    )
    generate_parser.add_argument(
        "--release",
        help="Qubes release to work with.",
        default="4.1"
    )
    generate_parser.add_argument(
        "--component-skeleton",
        help="Add a component skeleton file in components folder."
    )
    generate_parser.add_argument(
        "--distfile",
        help="Create a distribution file with all the Qubes components info."
    )

    get_parser = subparser.add_parser('get', help='Get')
    get_parser.add_argument(
        "--packages-list",
        default='all',
        nargs='+',
        help="Show packages list for given components. 'all' is accepted."
    )
    get_parser.add_argument(
        "--with-nvr",
        action="store_true",
        help="Output with version and release build tag."
    )
    get_parser.add_argument(
        "--raw",
        action="store_true",
        help="Raw output. Format can be specified. See --format"
    )
    get_parser.add_argument(
        "--format",
        help="Provide format as colon separated fields. "
             "Available fields: component, qubes_release, package_set, dist, packages."
    )
    get_parser.add_argument(
        "--skip-empty",
        action="store_true",
        help="Skip output of empty packages list"
    )
    get_parser.add_argument(
        "--dist",
        nargs='+',
        help="Filter distributions."
    )
    get_parser.add_argument(
        "--package-set",
        help="Filter package set."
    )
    get_parser.add_argument(
        "--release",
        help="Filter Qubes release."
    )
    return parser.parse_args()


def main():
    args = get_args()

    # sanity checks
    if not os.path.exists(args.releasefile):
        print("ERROR: Cannot find release file %s" % args.releasefile)
        return 1
    if not os.path.exists(args.components_folder):
        print(
            "ERROR: Cannot find components folder %s" % args.components_folder)
        return 1
    if not os.path.exists(args.qubes_src):
        print("ERROR: Cannot find qubes-src folder")
        return 1
    if args.package_set and args.package_set not in ("dom0", "vm"):
        print("ERROR: Invalid package set provided")
        return 1
    requested_format = None
    if args.format:
        requested_format = args.format.split(':')
        for fmt in args.format.split(':'):
            if fmt not in AVAILABLE_FORMAT_ITEMS:
                print("ERROR: Unsupported format '%s'" % fmt)
                return 1

    cli = ComponentsManagerCli(
        releasefile=args.releasefile,
        components_folder=args.components_folder,
        qubes_src=os.path.abspath(args.qubes_src)
    )
    cli.init()

    if args.command == 'update':
        if args.packages_list:
            cli.update_components(args.packages_list)
    elif args.command == 'generate':
        if args.builder_conf and args.release:
            cli.generate_conf(args.release, args.builder_conf)
        if args.component_skeleton:
            cli.add_component(args.component_skeleton)
        if args.distfile:
            cli.create_distfile(args.distfile)
    elif args.command == 'get':
        if args.packages_list:
            if args.with_nvr:
                cli.update_components(args.packages_list)
            pkgs_list = cli.get_components_packages_list(
                args.packages_list,
                with_nvr=args.with_nvr,
                raw=args.raw,
                skip_empty=args.skip_empty,
                req_format=requested_format,
                req_dist=args.dist,
                req_package_set=args.package_set,
                req_release=args.release,
            )
            if not args.raw:
                print(json.dumps(pkgs_list, indent=4))
            else:
                print('\n'.join(pkgs_list))


if __name__ == "__main__":
    sys.exit(main())
