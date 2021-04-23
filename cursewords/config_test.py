import os

from . import config


CONFIG_FNAME = 'myapp.toml'

CONFIG_TEXT = """
name = "Mr. Chips"
timeout_seconds = 60

[network]
ip_addr = "10.0.0.1"
"""

CONFIG_TEXT_ALT = """
name = "Scooter Computer"
timeout_seconds = 20
"""


def make_temp_dirs(tmpdir):
    dirs = [os.path.join(tmpdir, x) for x in ['cwd', 'home']]
    for dpath in dirs:
        os.makedirs(dpath)
    return dirs


def make_config(tmpdir, in_cwd=True):
    dirs = make_temp_dirs(tmpdir)
    cfgpath = os.path.join(dirs[0 if in_cwd else 1], CONFIG_FNAME)
    with open(cfgpath, 'w') as outfh:
        outfh.write(CONFIG_TEXT)
    return dirs


def make_config_parser(config_dirs, config_fname=CONFIG_FNAME):
    cfgparser = config.ConfigParser(
        config_fname=config_fname,
        config_dirs=config_dirs)
    cfgparser.add_parameter('name', type=str)
    cfgparser.add_parameter('timeout-seconds', type=int)
    cfgparser.add_parameter('network.ip-addr', type=str)
    cfgparser.add_parameter('verbose-log', type=bool)
    return cfgparser


def test_config_uses_args(tmpdir):
    cfgparser = make_config_parser(make_temp_dirs(tmpdir))
    cfg = cfgparser.parse_cfg(['--timeout-seconds=999'])
    assert cfg.timeout_seconds == 999


def test_config_uses_file(tmpdir):
    cfgparser = make_config_parser(make_config(tmpdir))
    cfg = cfgparser.parse_cfg([])
    assert cfg.timeout_seconds == 60


def test_arg_overrides_file(tmpdir):
    cfgparser = make_config_parser(make_config(tmpdir))
    cfg = cfgparser.parse_cfg(['--timeout-seconds=999'])
    assert cfg.timeout_seconds == 999


def test_config_honors_lookup_path(tmpdir):
    config_dirs = make_config(tmpdir, in_cwd=False)
    cfgparser = make_config_parser(config_dirs)
    with open(os.path.join(config_dirs[0], CONFIG_FNAME), 'w') as outfh:
        outfh.write(CONFIG_TEXT_ALT)
    cfg = cfgparser.parse_cfg([])
    assert cfg.timeout_seconds == 20


def test_lookup_path_supports_cwd(tmpdir):
    config_dirs = make_config(tmpdir)
    os.chdir(config_dirs[0])
    config_dirs[0] = '.'
    cfgparser = make_config_parser(config_dirs)
    cfg = cfgparser.parse_cfg([])
    assert cfg.timeout_seconds == 60


def test_dotpath_from_arg(tmpdir):
    cfgparser = make_config_parser(make_temp_dirs(tmpdir))
    cfg = cfgparser.parse_cfg(['--network.ip-addr=192.168.0.1'])
    assert cfg.network.ip_addr == '192.168.0.1'


def test_dotpath_from_file(tmpdir):
    cfgparser = make_config_parser(make_config(tmpdir))
    cfg = cfgparser.parse_cfg([])
    assert cfg.network.ip_addr == '10.0.0.1'


def test_dotpath_args_overrides_file(tmpdir):
    cfgparser = make_config_parser(make_config(tmpdir))
    cfg = cfgparser.parse_cfg(['--network.ip-addr=192.168.0.1'])
    assert cfg.network.ip_addr == '192.168.0.1'
