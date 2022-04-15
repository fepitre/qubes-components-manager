#!/usr/bin/python3

import yaml
import urllib.parse
from pathlib import Path
from lib.common import get_rpm_spec_files, get_deb_build_dirs, get_arch_build_dirs, get_src_files, get_deb_patch_serie

SRC_DIR = Path("/home/user/builder-dev/qubes-src")

components = [
    "lvm2",
    # "vmm-xen",
    # "core-libvirt",
    # "core-vchan-xen",
    # "core-qubesdb",
    # "core-qrexec",
    "linux-utils",
    "python-cffi",
    "python-xcffib",
    "python-objgraph",
    "python-hid",
    "python-u2flib-host",
    # "python-qasync",
    "python-panflute",
    "rpm-oxide",
    # "core-admin",
    # "core-admin-client",
    "core-admin-addon-whonix",
    "core-admin-linux",
    # "core-agent-linux",
    "intel-microcode",
    "linux-firmware",
    "linux-kernel",
    "artwork",
    "grub2-theme",
    "gui-common",
    "gui-daemon",
    "gui-agent-linux",
    "gui-agent-xen-hvm-stubdom",
    "seabios",
    "app-linux-split-gpg",
    "app-thunderbird",
    "app-linux-pdf-converter",
    "app-linux-img-converter",
    "app-linux-input-proxy",
    "app-linux-usb-proxy",
    "app-linux-snapd-helper",
    "app-shutdown-idle",
    "app-yubikey",
    "app-u2f",
    "screenshot-helper",
    "repo-templates",
    "meta-packages",
    "manager",
    "desktop-linux-common",
    "desktop-linux-kde",
    "desktop-linux-xfce4",
    # "desktop-linux-xfce4-xfwm4",
    "desktop-linux-i3",
    "desktop-linux-i3-settings-qubes",
    "desktop-linux-awesome",
    "desktop-linux-manager",
    "grubby-dummy",
    "dummy-psu",
    "dummy-backlight",
    "xorg-x11-drv-intel",
    "linux-gbulb",
    "linux-scrypt",
    "qubes-release",
    "pykickstart",
    "blivet",
    "lorax",
    "lorax-templates",
    "anaconda",
    "anaconda-addon",
    "tpm-extra",
    "trousers-changer",
    "antievilmaid",
    "xscreensaver",
    "remote-support",
    "xdotool",
]

result = {}

for c in components:
    result.setdefault(c, {})

    # host
    r = get_rpm_spec_files(str(SRC_DIR/c), "fc32", "dom0")
    if r:
        result[c].setdefault("host", {}).setdefault("rpm", {})["spec"] = r
    # vm
    r = get_rpm_spec_files(str(SRC_DIR/c), "fc34", "vm")
    if r:
        result[c].setdefault("vm", {}).setdefault("rpm", {})["spec"] = r

    s_10 = get_deb_patch_serie(str(SRC_DIR / c), "buster")
    s_11 = get_deb_patch_serie(str(SRC_DIR / c), "bullseye")
    s_12 = get_deb_patch_serie(str(SRC_DIR / c), "bookworm")

    r_10 = [d.replace("debian-pkg/debian", "debian") for d in get_deb_build_dirs(str(SRC_DIR / c), "buster")]
    r_11 = [d.replace("debian-pkg/debian", "debian") for d in get_deb_build_dirs(str(SRC_DIR / c), "bullseye")]
    r_12 = [d.replace("debian-pkg/debian", "debian") for d in get_deb_build_dirs(str(SRC_DIR / c), "bookworm")]
    if not all([r_10, r_11, r_12]):
        if r_10 and not r_11:
            result[c].setdefault("vm-buster", {}).setdefault("deb", {})["build"] = r_10
            if s_10:
                result[c]["vm-buster"]["source"].setdefault("commands", []).append(f"@PLUGINS_DIR@/source_deb/scripts/debian-quilt @SOURCE_DIR@/series-debian-vm.conf @BUILD_DIR@/debian/patches")
        elif r_10 and r_11 and not r_12:
            result[c].setdefault("vm-buster", {}).setdefault("deb", {})["build"] = r_10
            if s_10:
                result[c]["vm-buster"]["source"].setdefault("commands", []).append(f"@PLUGINS_DIR@/source_deb/scripts/debian-quilt @SOURCE_DIR@/series-debian-vm.conf @BUILD_DIR@/debian/patches")
            result[c].setdefault("vm-bullseye", {}).setdefault("deb", {})["build"] = r_11
            if s_11:
                result[c]["vm-bullseye"]["source"].setdefault("commands", []).append(f"@PLUGINS_DIR@/source_deb/scripts/debian-quilt @SOURCE_DIR@/series-debian-vm.conf @BUILD_DIR@/debian/patches")
    else:
        result[c].setdefault("vm", {}).setdefault("deb", {})["build"] = r_12

    r = get_arch_build_dirs(str(SRC_DIR/c), "archlinux")
    if r:
        result[c].setdefault("vm", {}).setdefault("archlinux", {})["build"] = r

    all_files = get_src_files(str(SRC_DIR/c))
    if all_files:
        files = {}
        for f in all_files:
            parsed_f = urllib.parse.urlparse(f)
            files[Path(parsed_f.path).name] = parsed_f.geturl()

        ascfiles = list((SRC_DIR / c).glob("*.asc"))
        if ascfiles:
            pubkeys = []
            for p in ascfiles.copy():
                if not p.with_suffix("").exists():
                    pubkeys.append(p.name)
                    ascfiles.remove(p)
            result[c].setdefault("source", {"files": []})
            for p in ascfiles:
                result[c]["source"]["files"].append(
                    {
                        "url": files[p.with_suffix("").name],
                        "signature": files[p.name],
                        "pubkeys": pubkeys
                    }
                )

        sha256 = list((SRC_DIR / c).glob("*.sha256"))
        if sha256:
            result[c].setdefault("source", {"files": []})
            for s in sha256:
                result[c]["source"]["files"].append(
                    {
                        "url": files[s.with_suffix("").name],
                        "sha256": s.name
                    }
                )

        sha512 = list((SRC_DIR / c).glob("*.sha512"))
        if sha512:
            result[c].setdefault("source", {"files": []})
            for s in sha512:
                result[c]["source"]["files"].append(
                    {
                        "url": files[s.with_suffix("").name],
                        "sha512": s.name
                    }
                )

    qb = SRC_DIR / c / ".qubesbuilder"
    qb.write_text(yaml.safe_dump(result[c], indent=2))
