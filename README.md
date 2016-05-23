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
