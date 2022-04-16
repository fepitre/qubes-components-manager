import os
import tempfile
import subprocess
import pathlib

def get_version(component_path):
    try:
        with open(os.path.join(component_path, 'version')) as fd:
            version = fd.read().split('\n')[0]
    except FileNotFoundError:
        version = None
    return version


def get_release(component_path):
    try:
        with open(os.path.join(component_path, 'rel')) as fd:
            release = fd.read().split('\n')[0]
    except FileNotFoundError:
        release = None
    return release


def get_makefile_value(makefile, var, env=None):
    # Very simple implementation of getting makefile variables values
    value = ''
    fenv = os.environ.copy()
    fenv.update(env)
    if os.path.exists(makefile):
        curr_dir = os.path.dirname(makefile)
        with tempfile.NamedTemporaryFile(dir=curr_dir) as fd:
            content = """
ORIG_SRC ?= {orig_src}
ifneq (,$(findstring mgmt-salt-,$(COMPONENT)))
include $(ORIG_SRC)/../mgmt-salt/Makefile.builder
endif
GITHUB_STATE_DIR = $(HOME)/github-notify-state
FETCH_CMD := XYZ
include {makefile_builder}
-include {makefile}

print-%  : ; @/usr/bin/echo $($*)
""".format(orig_src=curr_dir, makefile_builder=makefile, makefile=makefile.replace(".builder", ""))
            fd.write(content.encode('utf-8'))
            fd.seek(0)
            cmd = "make -f %s print-%s" % (fd.name, var)
            output = subprocess.check_output([cmd], cwd=curr_dir, shell=True, text=True, env=fenv)
            value = output.rstrip('\n')
    return value


def call_makefile(makefile, target, env=None):
    # Very simple implementation of getting makefile variables values
    value = ''
    fenv = os.environ.copy()
    fenv.update(env)
    if os.path.exists(makefile):
        curr_dir = os.path.dirname(makefile)
        with tempfile.NamedTemporaryFile(dir=curr_dir) as fd:
            content = """
ORIG_SRC ?= {orig_src}
ifneq (,$(findstring mgmt-salt-,$(COMPONENT)))
include $(ORIG_SRC)/../mgmt-salt/Makefile.builder
endif
GITHUB_STATE_DIR = $(HOME)/github-notify-state
FETCH_CMD := XYZ
.PHONY: *.asc *.sig
include {makefile_builder}
-include {makefile}

print-%  : ; @/usr/bin/echo $($*)
""".format(orig_src=curr_dir, makefile_builder=makefile, makefile=makefile.replace(".builder", ""))
            fd.write(content.encode('utf-8'))
            fd.seek(0)
            cmd = "make -f %s %s" % (fd.name, target)
            output = subprocess.run([cmd], capture_output=True, cwd=curr_dir, shell=True, text=True, env=fenv)
            value = output.stdout.rstrip('\n')
    return value


def get_src_files(component_path):
    makefile_path = os.path.join(component_path, 'Makefile.builder')
    env = {
        "COMPONENT": os.path.basename(component_path)
    }
    files = []
    output = call_makefile(makefile_path, "-n get-sources", env=env)
    for l in output.splitlines():
        parsed_line = l.split()
        if parsed_line[0] == "XYZ":
            while parsed_line and parsed_line[-1] in ("&&", "\\"):
                parsed_line = parsed_line[:-1]
            files.append(parsed_line[-1])
    # files = get_makefile_value(makefile_path, 'SRC_FILE', env).split()
    # files += get_makefile_value(makefile_path, 'SIGN_FILE', env).split()
    # files += get_makefile_value(makefile_path, 'ALL_FILES', env).split()
    return files


def get_rpm_spec_files(component_path, dist, package_set):
    makefile_path = os.path.join(component_path, 'Makefile.builder')
    env = {
        "COMPONENT": os.path.basename(component_path)
    }
    if dist.startswith('centos'):
        distribution = 'centos'
    else:
        distribution = 'fedora'
    if package_set == 'dom0':
        env.update(
            {'PACKAGE_SET': 'dom0', 'DISTRIBUTION': distribution, 'DIST': dist})
    elif package_set == 'vm':
        env.update(
            {'PACKAGE_SET': 'vm', 'DISTRIBUTION': distribution, 'DIST': dist})

    specs = get_makefile_value(makefile_path, 'RPM_SPEC_FILES', env)
    return specs.split()


def get_deb_build_dirs(component_path, vm):
    makefile_path = os.path.join(component_path, 'Makefile.builder')
    env = {
        "COMPONENT": os.path.basename(component_path)
    }
    env.update({'PACKAGE_SET': 'vm', 'DISTRIBUTION': 'debian', 'DIST': vm})
    debian_build_dirs = get_makefile_value(
        makefile_path, 'DEBIAN_BUILD_DIRS', env)
    return debian_build_dirs.split()


def get_deb_patch_serie(component_path, vm):
    serie = None
    makefile_path = os.path.join(component_path, 'Makefile.builder')
    env = {
        "COMPONENT": os.path.basename(component_path)
    }
    env.update({'PACKAGE_SET': 'vm', 'DISTRIBUTION': 'debian', 'DIST': vm})
    source_copy_in = get_makefile_value(makefile_path, 'SOURCE_COPY_IN', env)
    if source_copy_in:
        output = call_makefile(makefile_path, f"-n {source_copy_in}", env=env)
        for l in output.splitlines():
            if serie:
                break
            if "debian-quilt" in l:
                parsed_line = l.split()
                for idx, val in enumerate(parsed_line):
                    if val.endswith("debian-quilt"):
                        serie = parsed_line[idx+1].strip().rstrip('\n')
                        serie = pathlib.Path(serie).relative_to(component_path)
                        break
    return serie


def get_arch_build_dirs(component_path, vm):
    makefile_path = os.path.join(component_path, 'Makefile.builder')
    env = {
        "COMPONENT": os.path.basename(component_path)
    }
    env.update({'PACKAGE_SET': 'vm', 'DISTRIBUTION': 'archlinux', 'DIST': vm})
    debian_build_dirs = get_makefile_value(
        makefile_path, 'ARCH_BUILD_DIRS', env)
    return debian_build_dirs.split()


def get_deb_control_file(component_path, vm):
    makefile_path = os.path.join(component_path, 'Makefile.builder')
    env = {
        "COMPONENT": os.path.basename(component_path)
    }
    env.update({'PACKAGE_SET': 'vm', 'DISTRIBUTION': 'debian', 'DIST': vm})
    debian_build_dirs = get_makefile_value(
        makefile_path, 'DEBIAN_BUILD_DIRS', env)
    control = None
    if debian_build_dirs:
        control = os.path.join(debian_build_dirs, 'control')
    return control
