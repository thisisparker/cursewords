"""A simple configuration manager.

A configuration file is in the TOML format. It lives either in the current
working directory or in ~/.config/, with the former overriding the latter.
Configuration files do not merge: it uses the first one it finds.

For example, this config file might be named "~/.config/myapp.toml":

    name = "Mr. Chips"
    timeout_seconds = 60

    [network]
    ip_addr = "10.0.0.1"

You can allow command line arguments to override configuration parameters
by including an argparse Namespace. You must describe the possible
parameters to your argparse parser.

    import argparse
    from .config import Config

    argparser = argparse.ArgumentParser()
    argparser.add_argument('filename', --help='...')
    argparser.add_argument('--name', type=str, --help='...')
    argparser.add_argument('--timeout-seconds', type=int, --help='...')
    argparser.add_argument('--network.ip-addr', type=str, --help='...')
    args = argparser.parse_args()
    cfg = Config('myapp.toml', args)

    # This is either the "--name" argument if specified, or the top-level
    # "name" parameter in the config file.
    name = cfg.name

    # Argparse converts hyphens in argument names to underscores. This must
    # appear with an underscore in the config file, e.g. "timeout_seconds".
    timeout_secs = cfg.timeout_seconds

    # Command line arguments can override arguments in TOML sections using
    # a dot-delimited path.
    ip_address = cfg.network.ip_addr

    # Use the argparse Namespace directly to access positional command line
    # arguments. (Technically Config will see this too, so avoid using a
    # config parameter whose name matches an optional argument's metavar.)
    filename = args.filename

For more information on the TOML file format:
    https://en.wikipedia.org/wiki/TOML
"""

import collections
import os.path
import toml


# The search path for configuration files, as an ordered list of directories.
CONFIG_DIRS = ['.', '~/.config']


class ConfigNamespace:
    """Helper class to represent a sub-tree of config values.

    You won't use this directly. Access values with attribute paths of the
    Config instance.
    """
    def __init__(self):
        # A key is a str. A value is either a raw value or a ConfigNamespace
        # instance.
        self._dict = {}

    def _set(self, path, value):
        # If the key is a dot path, drill down the path.
        dot_i = path.find('.')
        if dot_i != -1:
            k = path[:dot_i]
            rest = path[dot_i+1:]
            if k not in self._dict:
                self._dict[k] = ConfigNamespace()
            self._dict[k]._set(rest, value)
            return

        # If the value is a mapping, merge values into a child namespace.
        if isinstance(value, collections.abc.Mapping):
            if path not in self._dict:
                self._dict[path] = ConfigNamespace()
            for k in value:
                self._dict[path]._set(k, value[k])
            return

        # For a simple key and value, set the value.
        self._dict[path] = value

    def _merge(self, mapping_value):
        for k in mapping_value:
            self._set(k, mapping_value[k])

    def __getattr__(self, name):
        return self._dict.get(name)

    def __repr__(self):
        return '[ConfigNamespace: ' + repr(self._dict) + ']'


class Config:
    def __init__(
            self,
            config_fname,
            override_args=None,
            config_dirs=CONFIG_DIRS):
        """Initializes the configuration manager.

        Args:
            config_fname: The TOML filename of the config file.
            override_args: Parsed command line arguments, as an argparse
                Namespace.
            config_dirs: The config file search path, as a list of directory
                paths. Default is current working directory, then ~/.config.
        """
        self.config_fname = config_fname
        self.override_args = override_args
        self.config_dirs = config_dirs

        self._cache = None

    def reload(self):
        """Reloads the configuration file, if any."""
        # Actually we just empty the cache, then reload on next access.
        self._cache = None

    def __getattr__(self, *args, **kwargs):
        self._build()
        return self._cache.__getattr__(*args, **kwargs)

    def _build(self):
        # Builds the config from a TOML file (if any) and args (if any).

        # Config builds on first access, then uses cached config thereafter.
        if self._cache is not None:
            return

        self._cache = ConfigNamespace()

        for dpath in self.config_dirs:
            cfgpath = os.path.normpath(
                os.path.expanduser(
                    os.path.join(dpath, self.config_fname)))
            if not os.path.isfile(cfgpath):
                continue
            with open(cfgpath) as infh:
                self._cache._merge(toml.loads(infh.read()))

            # It wouldn't be difficult to merge multiple config files, but
            # this isn't typically expected behavior. Use only the first
            # file on the lookup path.
            break

        if self.override_args is not None:
            args_dict = dict([
                i for i in vars(self.override_args).items()
                if i[1] is not None])
            self._cache._merge(args_dict)
