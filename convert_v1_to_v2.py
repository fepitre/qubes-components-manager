#!/usr/bin/python3
import pathlib

import yaml
import urllib.parse
from pathlib import Path
from lib.common import get_rpm_spec_files, get_deb_build_dirs, get_arch_build_dirs, get_src_files, get_deb_patch_serie

SRC_DIR = Path("/home/user/builder-updatev2/qubes-src")

components = [
    "lvm2",
    "vmm-xen",
    "core-libvirt",
    "core-vchan-xen",
    "core-qubesdb",
    "core-qrexec",
    "linux-utils",
    "python-cffi",
    "python-xcffib",
    "python-objgraph",
    "python-hid",
    "python-u2flib-host",
    "python-qasync",
    "python-panflute",
    "rpm-oxide",
    "core-admin",
    "core-admin-client",
    "core-admin-addon-whonix",
    "core-admin-linux",
    "core-agent-linux",
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
    "desktop-linux-xfce4-xfwm4",
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

    r_10 = [d.replace("debian-pkg/debian", "debian").replace("debian-vm/debian", "debian") for d in get_deb_build_dirs(str(SRC_DIR / c), "buster")]
    r_11 = [d.replace("debian-pkg/debian", "debian").replace("debian-vm/debian", "debian") for d in get_deb_build_dirs(str(SRC_DIR / c), "bullseye")]
    r_12 = [d.replace("debian-pkg/debian", "debian").replace("debian-vm/debian", "debian") for d in get_deb_build_dirs(str(SRC_DIR / c), "bookworm")]
    if not all([r_10, r_11, r_12]):
        if r_10 and not r_11:
            result[c].setdefault("vm-buster", {}).setdefault("deb", {})["build"] = r_10
            if s_10:
                result[c]["vm-buster"]["deb"].setdefault("source", {})
                result[c]["vm-buster"]["deb"]["source"].setdefault("commands", []).append(f"@PLUGINS_DIR@/source_deb/scripts/debian-quilt @SOURCE_DIR@/{s_10} @BUILD_DIR@/debian/patches")
        elif r_10 and r_11 and not r_12:
            result[c].setdefault("vm-buster", {}).setdefault("deb", {})["build"] = r_10
            if s_10:
                result[c]["vm-buster"]["deb"].setdefault("source", {})
                result[c]["vm-buster"]["deb"]["source"].setdefault("commands", []).append(f"@PLUGINS_DIR@/source_deb/scripts/debian-quilt @SOURCE_DIR@/{s_11} @BUILD_DIR@/debian/patches")
            result[c].setdefault("vm-bullseye", {}).setdefault("deb", {})["build"] = r_11
            if s_11:
                result[c]["vm-bullseye"]["deb"].setdefault("source", {})
                result[c]["vm-bullseye"]["deb"]["source"].setdefault("commands", []).append(f"@PLUGINS_DIR@/source_deb/scripts/debian-quilt @SOURCE_DIR@/{s_12} @BUILD_DIR@/debian/patches")
    else:
        result[c].setdefault("vm", {}).setdefault("deb", {})["build"] = r_12
        s = s_12 or s_11 or s_10
        if s:
            result[c]["vm"]["deb"].setdefault("source", {}).setdefault("commands", []).append(f"@PLUGINS_DIR@/source_deb/scripts/debian-quilt @SOURCE_DIR@/{s} @BUILD_DIR@/debian/patches")

    r = get_arch_build_dirs(str(SRC_DIR/c), "archlinux")
    if r:
        result[c].setdefault("vm", {}).setdefault("archlinux", {})["build"] = r

    all_files = get_src_files(str(SRC_DIR/c))
    if all_files:
        sigfiles = list((SRC_DIR / c).glob("*.sig")) + list((SRC_DIR / c).glob("*.asc"))
        sha256 = list((SRC_DIR / c).glob("*.sha256"))
        sha512 = list((SRC_DIR / c).glob("*.sha512"))

        files = {}
        files_sig = {}
        files_nosig = {}

        for f in all_files:
            parsed_f = urllib.parse.urlparse(f)
            fname = Path(parsed_f.path).name
            files[fname] = parsed_f.geturl()

            if fname.endswith(".sig") or fname.endswith(".asc"):
                files_sig[fname] = parsed_f.geturl()
            else:
                files_nosig[fname] = parsed_f.geturl()

        pubkeys = []
        if sigfiles:
            for p in sigfiles.copy():
                if not p.with_suffix("").exists():
                    pubkeys.append(p.name)
                    sigfiles.remove(p)
                elif p.name not in files_sig:
                    files_sig[p.name] = p

        if files:
            result[c].setdefault("source", {"files": []})

        for p in files_nosig:
            url = None
            sig = None
            for q in files_sig:
                if Path(p).with_suffix("") == Path(q).with_suffix("") or p == Path(q).with_suffix("").name or len(files_nosig) == len(files_sig) == 1:
                    url = files_nosig[p]
                    sig = files_sig[q]
                    if isinstance(sig, pathlib.Path):
                        sig = sig.name
            if not url and not sig:
                if not pubkeys:
                    continue
                else:
                    raise Exception
            result[c]["source"]["files"].append(
                {
                    "url": url,
                    "signature": sig,
                    "pubkeys": pubkeys
                }
            )

        if sha256:
            result[c].setdefault("source", {"files": []})
            for s in sha256:
                result[c]["source"]["files"].append(
                    {
                        "url": files[s.with_suffix("").name],
                        "sha256": s.name
                    }
                )

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
    qb.write_text(yaml.safe_dump(result[c], sort_keys=False, width=1000))

    gitlabci = SRC_DIR / c / ".gitlab-ci.yml"
    if gitlabci.exists():
        gci = yaml.safe_load(gitlabci.read_text())
        final_gci = gci.copy()
        include = gci.get("include", []).copy()
        for inc in include:
            new_inc = inc.copy()
            if "r4.2" in new_inc["file"]:
                continue
            new_inc["file"] = new_inc["file"].replace("r4.1", "r4.2").replace("dom0", "host")
            final_gci["include"].append(new_inc)
        final_gci["include"] = sorted([dict(t) for t in {tuple(d.items()) for d in final_gci["include"]}], key=lambda x: x["file"])
        gitlabci.write_text(yaml.safe_dump(final_gci))
