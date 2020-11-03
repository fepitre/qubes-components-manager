qubes-component-manager
===
```
# get all built packages
./component-manager.py --release 4.1 --qubes-src ../qubes-builder-4.1/qubes-src/ --get-packages

# get built packages dom0 names
./component-manager.py --release 4.0 --qubes-src ../qubes-builder-4.0/qubes-src/ --components core-admin --dist fc25 --get-packages-dom0
./component-manager.py --release 4.1 --qubes-src ../qubes-builder-4.1/qubes-src/ --components all --dist fc32 --get-packages-dom0

# get built packages vms names
./component-manager.py --release 4.1 --qubes-src ../qubes-builder-4.1/qubes-src/ --components all --dist bullseye --get-packages-vms
./component-manager.py --release 4.1 --qubes-src ../qubes-builder-4.1/qubes-src/ --components core-agent-linux core-qubesdb --dist centos8 --get-packages-vms

# update components/*.json available basename packages list
./component-manager.py --release 4.1 --qubes-src ../qubes-builder-4.1/qubes-src/ --distfile distfile.json --components all --update-pkg-list

# generate conf
./component-manager.py --release 4.0 --qubes-src ../qubes-builder-4.0/qubes-src/ --components all --generate-conf qubes-os-r4.0.conf
```
