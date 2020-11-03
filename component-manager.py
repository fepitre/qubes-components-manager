#!/usr/bin/python3

import argparse
import os
import sys
import json

from jinja2 import Template

from lib.component import QubesComponent
from lib.dist import QubesDist


def get_args():
    parser = argparse.ArgumentParser()

    # mandatory arguments
    parser.add_argument(
        "--release",
        default="4.1"
    )
    parser.add_argument(
        "--distfile",
        required=False,
        default='distfile.json',
        help="Input distribution file ('distfile.json')."
    )
    parser.add_argument(
        "--components-folder",
        required=False,
        default=os.path.join(os.getcwd(), 'components'),
        help="Input components folder ('components/*.json')."
    )
    parser.add_argument(
        "--qubes-src",
        required=True,
        help="Local path of Qubes sources corresponding to the requested "
             "release."
    )
    parser.add_argument(
        "--components",
        required=False,
        default='all',
        nargs='+',
        help="List of components to process for all distributions. For "
             "processing all components use value 'all'. "
    )

    # content generation
    parser.add_argument(
        "--update-distfile",
        required=False,
        action="store_true",
        help="Update distfile."
    )
    parser.add_argument(
        "--update-pkg-list",
        required=False,
        action="store_true",
        help="Update packages list."
    )
    parser.add_argument(
        "--generate-conf",
        required=False,
        help="Destination file for generating qubes-builder configuration file."
    )
    parser.add_argument(
        "--add-component",
        required=False,
        help="Add a skeleton component file in components folder."
    )

    # content information
    parser.add_argument(
        "--get-packages",
        required=False,
        action='store_true',
        help="Show packages names for dom0 and VMs."
    )
    parser.add_argument(
        "--get-packages-dom0",
        required=False,
        action='store_true',
        help="Show packages names for dom0. To be used with --dist."
    )
    parser.add_argument(
        "--get-packages-vms",
        required=False,
        action='store_true',
        help="Show packages names for VMs. To be used with --dist."
    )
    parser.add_argument(
        "--dist",
        required=False,
        help="Filter for a given distribution."
    )

    return parser.parse_args()


class ComponentManagerCli:
    def __init__(self, release, qubes_src, distfile, components,
                 components_folder):
        self.release = release

        self.data = {}
        self.builder_plugins = []
        self.iso_components = []
        self.windows_components = []
        self.filtered_components = []

        self.qubes_src = qubes_src
        self.distfile = distfile
        self.components = components
        self.components_folder = components_folder

        self.components = []
        self.dom0 = []
        self.vms = []

    def load_components(self):
        with open(self.distfile) as fd:
            self.data = json.loads(fd.read())

        # dom0 dist
        for dist in self.data["releases"][self.release]["dom0"]:
            self.dom0.append(QubesDist(dist))

        # vms dist
        for dist in self.data["releases"][self.release]["vms"]:
            self.vms.append(QubesDist(dist))

        # qubes components
        for name in self.data["components"].keys():
            release = self.data["components"][name]["releases"].get(
                self.release, None)
            if release:
                branch = release.get("branch", None)
                if branch:
                    orig_src = os.path.join(self.qubes_src, name)
                    kwargs = self.data["components"][name]
                    del kwargs["releases"]
                    self.components.append(
                        QubesComponent(name, branch, orig_src, **kwargs)
                    )

        # filter components for conf
        self.filter_components()

    def filter_components(self):
        for component in self.components:
            if component.is_plugin_type():
                self.builder_plugins.append(component)
            if component.is_iso_component():
                self.iso_components.append(component)
            if component.is_windows_type():
                self.windows_components.append(component)

            if component not in self.builder_plugins + self.iso_components + \
                    self.windows_components:
                self.filtered_components.append(component)

    def is_devel_version(self):
        return self.data["releases"][self.release].get("devel", 0)

    def get_dom0(self):
        return self.dom0

    def get_vms(self):
        return self.vms

    def get_component(self, name):
        for component in self.components:
            if component.name == name:
                return component

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

    def fetch_packages(self, components):
        for component in self.get_components_from_name(components):
            if component.name == 'linux-template-builder':
                continue
            component.fetch_all_packages(self.dom0, self.vms)

    def dump_components(self, components):
        for component in self.get_components_from_name(components):
            component_file = os.path.join(
                self.components_folder, '%s.json' % component.name)
            with open(component_file) as fd:
                content = json.loads(fd.read())

            if content[component.name]["releases"].get(self.release, None):
                content[component.name]["releases"][self.release]["dom0"] = \
                    component.get_packages_names_dom0(self.dom0)
                content[component.name]["releases"][self.release]["vms"] = \
                    component.get_packages_names_vms(self.vms)

            with open(component_file, 'w') as fd:
                fd.write(json.dumps(content, indent=4))

    def get_branches_conf(self):
        branches = []
        for component in self.components:
            if component.branch != "release%s" % self.release:
                if component.branch == "master" and \
                        self.is_devel_version() == 1:
                    continue
                branches.append(
                    'BRANCH_%s = %s' % (component.name.replace('-', '_'),
                                        component.branch))

        return branches

    def get_maintainers_conf(self):
        maintainers = {}
        for component in self.components:
            for maintainer in component.get_maintainers():
                if not maintainers.get(maintainer, None):
                    maintainers[maintainer] = []
                maintainers[maintainer].append(component.name)

        maintainers_conf = []
        for key, val in maintainers.items():
            maintainers_conf.append(
                'ALLOWED_COMPONENTS_%s = %s' % (key, ' '.join(val)))

        return maintainers_conf

    def get_template_labels_conf(self):
        template_labels = []
        for dist in self.dom0 + self.vms:
            template_labels += dist.get_labels()

        return template_labels

    def get_template_alias_conf(self):
        template_aliases = []
        for dist in self.vms:
            template_aliases += dist.get_alias()

        return template_aliases

    def generate_conf(self, conf_file):
        with open('template.conf.jinja', 'r') as template_fd:
            template = Template(template_fd.read())

        conf = {
            "devel": self.is_devel_version(),
            "release": self.release,
            "dist_dom0": self.get_dom0(),
            "dists_vm": self.get_vms(),
            "builder_plugins": self.builder_plugins,
            "iso_components": self.iso_components,
            "windows_components": self.windows_components,
            "components": self.filtered_components,
            "template_labels": self.get_template_labels_conf(),
            "template_aliases": self.get_template_alias_conf(),
            "branches": self.get_branches_conf(),
            "maintainers": self.get_maintainers_conf()
        }

        generated_conf = template.render(**conf)
        with open(conf_file, 'w') as fd:
            fd.write(generated_conf)

    # distfile.json (packages order + releases information) + components/*.json -> distfile.json
    def update_distfile(self):
        with open(self.distfile) as fd:
            data = json.loads(fd.read())

        for component in data["components"]:
            # if json is missing we have at least content from distfile
            try:
                component_file = os.path.join(
                    self.components_folder, '%s.json' % component)
                with open(component_file) as fd:
                    data_component = json.loads(fd.read())
                    data["components"][component] = data_component[component]
            except FileNotFoundError:
                pass

        with open(self.distfile, 'w') as fd:
            fd.write(json.dumps(data, indent=4))

    def get_packages(self, components, dom0=False, vm=False, dist=None):
        pkgs = {}
        if (dom0 or vm) and dist:
            dist = QubesDist(dist)
            for component in self.get_components_from_name(components):
                if dom0:
                    pkgs[component.name] = component.get_packages_dom0(dist)
                elif vm:
                    pkgs[component.name] = component.get_packages_vms(dist)
        else:
            for component in self.get_components_from_name(components):
                pkgs[component.name] = {"dom0": {}, "vms": {}}
                for dist in self.get_dom0():
                    if not dist.name.startswith('whonix'):
                        pkgs[component.name]["dom0"][dist.name] = \
                            component.get_packages_dom0(dist)
                for dist in self.get_vms():
                    if not dist.name.startswith('whonix'):
                        pkgs[component.name]["vms"][dist.name] = \
                            component.get_packages_vms(dist)
        return pkgs

    def add_component(self, name):
        content = {
            name: {
                "releases": {},
                "dom0": {},
                "vms": {}
            }
        }
        for release in self.data["releases"].keys():
            if self.data["releases"][release].get("devel", 0):
                branch = 'master'
            else:
                branch = 'release%s' % release
            content[name]["releases"][release] = {
                "branch": branch
            }
        component_file = os.path.join(self.components_folder, '%s.json' % name)
        with open(component_file, 'w') as fd:
            fd.write(json.dumps(content, indent=4))


def main():
    args = get_args()
    cli = ComponentManagerCli(release=args.release,
                              qubes_src=os.path.abspath(args.qubes_src),
                              distfile=args.distfile,
                              components=args.components,
                              components_folder=args.components_folder
                              )

    if not os.path.exists(args.distfile):
        print("ERROR: Cannot find distfile %s" % args.distfile)
        return 1
    if not os.path.exists(args.components_folder):
        print(
            "ERROR: Cannot find components folder %s" % args.components_folder)
        return 1

    cli.load_components()
    if args.update_distfile:
        # in case of local modification in components/*.json
        cli.update_distfile()
    elif args.update_pkg_list:
        # fetch packages
        cli.fetch_packages(args.components)
        # update components/*.json
        cli.dump_components(args.components)
        # update distfile.json
        cli.update_distfile()
    elif args.generate_conf:
        cli.update_distfile()
        cli.generate_conf(args.generate_conf)
    elif args.add_component:
        cli.add_component(args.add_component)
    elif args.get_packages:
        cli.fetch_packages(args.components)
        print(json.dumps(cli.get_packages(args.components), indent=4))
    elif args.dist:
        if args.get_packages_dom0:
            cli.fetch_packages(args.components)
            print(json.dumps(
                cli.get_packages(args.components, dom0=True, dist=args.dist),
                indent=4)
            )
        elif args.get_packages_vms:
            cli.fetch_packages(args.components)
            print(json.dumps(
                cli.get_packages(args.components, vm=True, dist=args.dist),
                indent=4)
            )

    # elif args.get_pkg_list():
    #     if not args.qubes_src:
    #         print("ERROR: Please provide '--dist' to use")
    #         return 1


if __name__ == "__main__":
    sys.exit(main())
