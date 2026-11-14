"""TOML support on Python 3.9 and newer."""
try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib
