HotS-Willie-Module
==================

A module for Willie The IRC Bot to be used on the #heroesofthestorm channel on quakenet, this is also my first real go at Python. I never intended to share the code, but someone somewhere might find it useful. Therefore the code will be ugly as hell and I might or might not refactor :)

## Running

* Install [Willie](http://willie.dftba.net/) the python IRC bot
* Get the HotS module: `curl -sSL https://raw.githubusercontent.com/Wobbley/HotS-Willie-Module/master/hots.py -o ~/.willie/modules/hots.py`
* Get the parameters file and then edit it to set the correct path to the database file:  `curl -sSL https://raw.githubusercontent.com/Wobbley/HotS-Willie-Module/master/hots_parameters.yml.dist -o $HOME/.willie/hots_parameters.yml; vim $HOME/.willie/hots_parameters.yml`
* Run willie: `willie`

## Contributing

* Clone the repo
* Run `pip install -r requirements.txt`
* Edit things
* Test by running willie:
  * `cp default.cfg.dist $HOME/.willie/default.cfg` and edit the path to the database file
  * `cp hots_parameters.yml.dist $HOME/.willie/hots_parameters.yml` and edit the path to the database file 
  * Configure your local willie (in `~/.willie`)
  * `ln -s $(pwd)/hots.py ~/.willie/modules/`
  * `willie`
