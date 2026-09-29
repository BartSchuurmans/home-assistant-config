"""Check that each blueprint has the required keys and a correct source_url."""
import glob
import sys

import yaml

REPO_URL = "https://github.com/BartSchuurmans/home-assistant-config/blob/main"


class Loader(yaml.SafeLoader):
    pass


Loader.add_constructor("!input", lambda loader, node: loader.construct_scalar(node))

errors = []
for path in sorted(glob.glob("blueprints/**/*.yaml", recursive=True)):
    with open(path) as f:
        blueprint = (yaml.load(f, Loader) or {}).get("blueprint")
    if not isinstance(blueprint, dict):
        errors.append(f"{path}: missing 'blueprint' section")
        continue
    for key in ("name", "domain", "input"):
        if key not in blueprint:
            errors.append(f"{path}: missing 'blueprint.{key}'")
    expected = f"{REPO_URL}/{path}"
    if blueprint.get("source_url") != expected:
        errors.append(f"{path}: source_url is {blueprint.get('source_url')!r}, expected {expected!r}")

for error in errors:
    print(error)
sys.exit(1 if errors else 0)
