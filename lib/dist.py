DEBIAN = {
    "stretch": "debian-9",
    "buster": "debian-10",
    "bullseye": "debian-11"
}

WHONIX = {
    "whonix-gateway-15": "whonix-gw-15",
    "whonix-workstation-15": "whonix-ws-15",
    "whonix-gw-15": "buster+whonix-gateway+minimal+no-recommends",
    "whonix-ws-15": "buster+whonix-workstation+minimal+no-recommends",
}


class QubesDist:
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return self.name

    def is_rpm(self):
        if self.name.startswith("fc") or self.name.startswith("centos"):
            return True

    def is_deb(self):
        if DEBIAN.get(self.name, None):
            return True

    def get_labels(self):
        labels = []
        label = None

        if self.name.startswith("fc"):
            label = self.name.replace("fc", "fedora-")
        elif self.name.startswith("centos"):
            label = self.name.replace("centos", "centos-")
        elif DEBIAN.get(self.name, None):
            label = DEBIAN[self.name]
        elif WHONIX.get(self.name, None):
            label = WHONIX[self.name]

        if label:
            if not WHONIX.get(self.name, None):
                labels += [
                    "%s:%s" % (self.name, label),
                    "%s+minimal:%s-minimal" % (self.name, label),
                    "%s+xfce:%s-xfce" % (self.name, label)
                ]

            else:
                labels += [
                    "%s:%s" % (WHONIX[label], label),
                ]

        if self.name.startswith("gentoo") or self.name.startswith("archlinux"):
            labels += [
                "%s+minimal:%s-minimal" % (self.name, self.name),
                "%s+xfce:%s-xfce" % (self.name, self.name)
            ]

        return labels

    def get_alias(self):
        alias = []
        if DEBIAN.get(self.name, None):
            alias += [
                "{dist}:{dist}+standard".format(dist=self.name),
                "{dist}+gnome:{dist}+gnome+standard".format(dist=self.name),
                "{dist}+minimal:{dist}+minimal+no-recommends".format(
                    dist=self.name)
            ]
        elif WHONIX.get(self.name, None):
            alias += [
                "{dist}:{alias}".format(dist=self.name, alias=WHONIX[self.name])
            ]

        return alias
