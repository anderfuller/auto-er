Note: This branch contains the refined code that will be used in the ML runs

# Autonomous Electrorefining

Developed by Anderson Fuller: [af383@byu.edu](docs/mailto:af383@byu.edu)

## Usage

In the top level directory, there are 2 important files:

* `main.py`: Main script that drives the whole ER process
* `power_supplies.py`: Specific to our Keysight programmable DC power supply and Keysight multimeters, can be refactored for other devices/communication protocols

To use this project, clone the repo or download the above files, navigate to the directory containing those files and run: `$ python ./main.py`