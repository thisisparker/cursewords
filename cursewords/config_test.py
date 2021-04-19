import argparse
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


def make_args(args):
    argparser = argparse.ArgumentParser()
    argparser.add_argument('--name', type=str)
    argparser.add_argument('--timeout-seconds', type=int)
    argparser.add_argument('--network.ip-addr', type=str)
    return argparser.parse_args(args)


def test_config_uses_args(tmpdir):
    config_dirs = make_temp_dirs(tmpdir)
    args = make_args(['--timeout-seconds=999'])
    cfg = config.Config(
        CONFIG_FNAME, override_args=args, config_dirs=config_dirs)
    assert cfg.timeout_seconds == 999


def test_config_uses_file(tmpdir):
    config_dirs = make_config(tmpdir)
    args = make_args([])
    cfg = config.Config(
        CONFIG_FNAME, override_args=args, config_dirs=config_dirs)
    assert cfg.timeout_seconds == 60


def test_config_honors_lookup_path(tmpdir):
    config_dirs = make_config(tmpdir, in_cwd=False)
    with open(os.path.join(config_dirs[0], CONFIG_FNAME), 'w') as outfh:
        outfh.write(CONFIG_TEXT_ALT)
    args = make_args([])
    cfg = config.Config(
        CONFIG_FNAME, override_args=args, config_dirs=config_dirs)
    assert cfg.timeout_seconds == 20


def test_lookup_path_supports_cwd(tmpdir):
    config_dirs = make_config(tmpdir)
    os.chdir(config_dirs[0])
    config_dirs[0] = '.'
    args = make_args([])
    cfg = config.Config(
        CONFIG_FNAME, override_args=args, config_dirs=config_dirs)
    assert cfg.timeout_seconds == 60


def test_dotpath_from_arg(tmpdir):
    config_dirs = make_temp_dirs(tmpdir)
    args = make_args(['--network.ip-addr=192.168.0.1'])
    cfg = config.Config(
        CONFIG_FNAME, override_args=args, config_dirs=config_dirs)
    assert cfg.network.ip_addr == '192.168.0.1'


def test_dotpath_from_file(tmpdir):
    config_dirs = make_config(tmpdir)
    args = make_args([])
    cfg = config.Config(
        CONFIG_FNAME, override_args=args, config_dirs=config_dirs)
    assert cfg.network.ip_addr == '10.0.0.1'


def test_arg_overrides_file(tmpdir):
    config_dirs = make_config(tmpdir)
    args = make_args(['--timeout-seconds=15'])
    cfg = config.Config(
        CONFIG_FNAME, override_args=args, config_dirs=config_dirs)
    assert cfg.timeout_seconds == 15


def test_dotpath_arg_overrides_file(tmpdir):
    config_dirs = make_config(tmpdir)
    args = make_args(['--network.ip-addr=192.168.0.1'])
    cfg = config.Config(
        CONFIG_FNAME, override_args=args, config_dirs=config_dirs)
    assert cfg.network.ip_addr == '192.168.0.1'
