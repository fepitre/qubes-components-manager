import os
import tempfile
import subprocess


def get_makefile_value(makefile, var, env=None):
    # Very simple implementation of getting makefile variables values
    value = ''
    if os.path.exists(os.path.dirname(makefile)):
        curr_dir = os.path.dirname(makefile)
        with tempfile.NamedTemporaryFile(dir=curr_dir) as fd:
            content = """
ORIG_SRC ?= {orig_src}
include {orig_src}/../mgmt-salt/Makefile.builder
include {makefile}

print-%  : ; @echo $($*)
""".format(orig_src=os.path.dirname(makefile), makefile=makefile)
            fd.write(content.encode('utf-8'))
            fd.seek(0)
            cmd = "make -f %s print-%s" % (fd.name, var)
            output = subprocess.check_output([cmd], cwd=curr_dir, shell=True, text=True, env=env)
            value = output.rstrip('\n')

    return value


def get_rpm_spec_files(component_path, dom0=None, vm=None):
    makefile_path = os.path.join(component_path, 'Makefile.builder')
    env = None
    if dom0:
        env = {'PACKAGE_SET': 'dom0', 'DIST': dom0}
    if vm:
        env = {'PACKAGE_SET': 'vm', 'DIST': vm}

    specs = get_makefile_value(makefile_path, 'RPM_SPEC_FILES', env)
    return specs.split()


def get_deb_control_file(component_path, vm):
    makefile_path = os.path.join(component_path, 'Makefile.builder')
    env = os.environ.copy()
    env.update({'PACKAGE_SET': 'vm', 'DISTRIBUTION': 'debian', 'DIST': vm})
    debian_build_dirs = get_makefile_value(makefile_path, 'DEBIAN_BUILD_DIRS',
                                           env)
    control = None
    if debian_build_dirs:
        control = os.path.join(debian_build_dirs, 'control')
    return control
