# meaningful-lobster
## Setup
Create a virtual environment
```
virtualenv --prompt="(lobster)" .pyenv
source .pyenv/bin/activate
```

Install a bunch of stuff
```
xcode-select --install
pip install -r requirements.txt
```

To be able to import from other modules, run `export PYTHONPATH=$(pwd)`

## Adding things
* Whenever we install a new library, we should update the requirements file.
* Every new folder that contains Python code (or folders that contain code) needs to have a `__init__.py` file in it. This allows us to treat folders like modules and do things like `from common.scripts import blah`.
