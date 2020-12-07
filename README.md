qubes-components-manager
===

```
usage: Qubes Components Manager [-h] [--releasefile RELEASEFILE] [--components-folder COMPONENTS_FOLDER] [--qubes-src QUBES_SRC]
                               {update,generate,get} ...

positional arguments:
  {update,generate,get}
    update              Update
    generate            Generate
    get                 Get

optional arguments:
  -h, --help            show this help message and exit
  --releasefile RELEASEFILE
                        Input release file ('release.json').
  --components-folder COMPONENTS_FOLDER
                        Input components folder ('components/*.json').
  --qubes-src QUBES_SRC
                        Local path of Qubes sources.
```

### Examples:

All of this examples assume that `qubes-builder` is in current repository where `make get-sources` has been executed with a builder configuration pulling all Qubes components sources.

* Update packages list for all components:
```
./components-manager.py update --packages-list all
```
* Update packages list for given components
```
./components-manager.py update --packages-list gui-agent-linux app-linux-split-gpg
```

* Get packages list for given components:
```
./components-manager.py get --packages-list gui-agent-linux app-linux-split-gpg
```
* Get packages list for given components with resulting build suffix (version, release, arch and package extension):
```
./components-manager.py get --packages-list gui-agent-linux app-linux-split-gpg --with-nvr
```

* Generate distribution file:
```
./components-manager.py generate --distfile distfile.json
```

* Generate Qubes builder configuration for `R4.0`:
```
./components-manager.py generate --builder-conf example-configs/qubes-os-r4.0.conf --release 4.0
```

* Generate a new Qubes component `my-new-component` located in `components` folder as JSON:
```
./components-manager.py generate --component-skeleton my-new-component
```