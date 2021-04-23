"""A simple configuration manager.

A configuration file is in the TOML format. It lives either in the current
working directory or in ~/.config/, with the former overriding the latter.
Configuration files do not merge: it uses the first one it finds.

For example, this config file might be named "$HOME/.config/myapp.toml":

    name = "Mr. Chips"
    timeout_seconds = 60

    [network]
    ip_addr = "10.0.0.1"

Config allows for overriding configuration parameters on the command line.
To enable this, register expected parameters with ConfigParser, then request
the ArgumentParser to set non-config parameters:

    from . import config

    cfgparser = config.ConfigParser('myapp.toml')
    cfgparser.add_parameter('name', type=str, --help='...')
    cfgparser.add_parameter('timeout-seconds', type=int, --help='...')
    cfgparser.add_parameter('network.ip-addr', type=str, --help='...')
    cfgparser.add_parameter('verbose-log', type=bool, --help='...')

    # Set non-config arguments on the ArgumentParser. Technically Config will
    # see these arguments too, so avoid using a config parameter whose name
    # matches an optional argument's metavar.
    argparser = cfgparser.get_argument_parser()
    argparser.add_argument('filename', --help='...')

    cfg = cfgparser.parse_cfg()

    # This is either the "--name" argument if specified, or the top-level
    # "name" parameter in the config file.
    name = cfg.name

    # Argparse converts hyphens in argument names to underscores. This must
    # appear with an underscore in the config file, e.g. "timeout_seconds".
    timeout_secs = cfg.timeout_seconds

    # Command line arguments can override arguments in TOML sections using
    # a dot-delimited path.
    ip_address = cfg.network.ip_addr

    # If type=bool, the parameter supports TOML true and false values. On the
    # command line, the parameter can be set or overriden using flag syntax,
    # e.g. --verbose-log or --no-verbose-log.
    do_verbose_logging = cfg.verbose_log

    # Use the argparse Namespace directly to access positional command line
    # arguments.
    args = argparser.parse_args()
    filename = args.filename

Config can access all values in the TOML file, not just those registered with
add_parameter(). Only items with add_parameter() can be overriden on the
command line. Only simple types are supported on the command line. Structures
like lists are supported in TOML, but not supported on the command line.

For more information on the TOML file format:
    https://en.wikipedia.org/wiki/TOML
"""

import argparse
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
            rest = path[dot_i + 1:]
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


class ConfigParameter:
    def __init__(self, name, is_flag=False, default=None):
        self.name = name
        self.is_flag = is_flag
        self.default = default


class ConfigParser:
    def __init__(
            self,
            config_fname,
            config_dirs=CONFIG_DIRS,
            *args,
            **kwargs):
        """Initializes the configuration manager.

        Args:
            config_fname: The TOML filename of the config file.
            config_dirs: The config file search path, as a list of directory
                paths. Default is current working directory (.), then
                ~/.config.
            *args: Remaining positional arguments are passed to
                argparse.ArgumentParser.
            **kwargs: Remaining keyword arguments are passed to
                argparse.ArgumentParser.
        """
        self.config_fname = config_fname
        self.config_dirs = config_dirs

        self._argparser = argparse.ArgumentParser(*args, **kwargs)
        self._params = []

    def add_parameter(
            self,
            name,
            default=None,
            type=str,
            help=None):
        """Registers a config parameter as overrideable on the command line.

        Args:
            name: The TOML path name of the parameter. Hyphens will be
                treated as hyphens for the command line and as underscores
                for the TOML file. Dots indicate TOML sections.
            default: The default value if not specified on either the command
                line or in the TOML file.
            type: The type of the value: str, int, or bool.
            help: A description of the option for argparse's help messages.
        """
        if type == bool:
            self._params.append(
                ConfigParameter(
                    name,
                    is_flag=True,
                    default=default))
            self._argparser.add_argument(
                '--' + name,
                action='store_true',
                required=False,
                help=help)
            self._argparser.add_argument(
                '--no-' + name,
                action='store_false',
                required=False,
                help=help)
        else:
            self._params.append(ConfigParameter(name, default=default))
            self._argparser.add_argument(
                '--' + name,
                type=type,
                required=False,
                help=help)

    def get_argument_parser(self):
        return self._argparser

    def parse_cfg(self, args=None):
        """Parses the config file and command line arguments.

        Args:
            args: A list of strings to parse as command line arguments.
                The default is taken from sys.argv.

        Returns:
            The results object.
        """
        namespace = ConfigNamespace()

        for dpath in self.config_dirs:
            cfgpath = os.path.normpath(
                os.path.expanduser(
                    os.path.join(dpath, self.config_fname)))
            if not os.path.isfile(cfgpath):
                continue
            with open(cfgpath) as infh:
                namespace._merge(toml.loads(infh.read()))

            # It wouldn't be difficult to merge multiple config files, but
            # this isn't typically expected behavior. Use only the first
            # file on the lookup path.
            break

        args = self._argparser.parse_args(args=args)
        if args is not None:
            args_dict = dict([
                i for i in vars(args).items()
                if i[1] is not None])

            for param in self._params:
                if param.is_flag:
                    if 'no_' + param.name in args_dict:
                        args_dict[param.name] = False
                        del args_dict['no_' + param.name]

            namespace._merge(args_dict)

        for param in self._params:
            if (getattr(namespace, param.name) is None and
                    param.default is not None):
                namespace._set(param.name, param.default)

        return namespace
