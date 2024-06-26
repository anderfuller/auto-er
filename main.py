#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" main.py

This is the high-level driver script for the autonomous electrorefining
process. Preferences and parameters are pulled from the prefs.yaml file found
in the same directory.

"""

# FIXMES in priority order:
# FIXME: multimeter readings
# FIXME: sweep step duration auto-optimization (delta)

import power_supply
import auto_er
import yaml
import sys
import datetime as dt
import math
import time

YAML_FILE = "prefs.yaml"


# Create your own loop inside this function.
# Useful functions:
#
#   refine(current) or refine(current, time)
#
#   sweep() or sweep(magnitude, time)
#
#   back_emf() or back_emf(print_time, time)
#
# Useful variables:
#
#   auto_er.refine_succeeded:
#       Whether or not the last refining period stopped early due to high
#       resistance
#
#   auto_er.back_emf_at_time:
#       Voltage of the last back emf period at the given print_time (ex 45s)
#
#   auto_er.max_sec_div:
#       Current where the highest second derivative of voltage w.r.t. current
#       occurs
#
#   p.refs["parameter"]:
#       Contains the specifed parameter from prefs.yaml (quotes needed)


def main():
    setup()  # Needed when starting the program

    sweep()

    starting_currents = [10, 15, 20]

    for current in starting_currents:
        refine(current=current, time=60)

        # Normal sweep
        print("Sweeping in 30s...")
        time.sleep(30)
        sweep(magnitude=1.5, time=30)

        # 30s sweep
        refine(current=current, time=2)
        print("Sweeping in 30s...")
        time.sleep(30)
        sweep(magnitude=1.5, time=10)

        # 1s sweep
        refine(current=current, time=2)
        print("Sweeping in 30s...")
        time.sleep(30)
        sweep(magnitude=1.5, time=1)

        # Instant sweep
        refine(current=current, time=2)
        print("Sweeping in 30s...")
        time.sleep(30)
        sweep(magnitude=1.5, time=0)

        refine(current=current, time=2)
        back_emf()

    # Calculate the first refining_current
    refining_current = 0.0

    if sweep_valid() and not sweep_linear():
        refining_current = (
            auto_er.max_sec_div * p.refs["operating_percantage"]
            + p.refs["operating_offset"]
        )

    elif sweep_valid() and sweep_linear():
        refining_current = 20

    elif not sweep_valid():
        refining_current = 20

    # Main loop! Will break once a refining period fails (R too high)
    while auto_er.refine_succeeded:
        refine(current=refining_current)

        print("Sweeping in 30s...")
        time.sleep(30)
        sweep()

        refine(current=refining_current, time=2)

        back_emf()

        # Calculate next refining_current if the sweep was valid
        if sweep_valid():
            if sweep_linear():
                refining_current = refining_current * 0.75

            else:
                refining_current = (
                    auto_er.max_sec_div * p.refs["operating_percantage"]
                    + p.refs["operating_offset"]
                )

        else:
            refining_current = refining_current * 0.75


def sweep_valid():
    if auto_er.min_dx < 0:
        return False

    elif auto_er.max_sec_div > auto_er.max_first_div:
        return False

    else:
        return True


def sweep_linear():
    if auto_er.max_sec_div_y <= 0.015:
        return True

    else:
        return False


##########################################################################
#                                                                        #
#                                                                        #
#                                                                        #
#                                                                        #
#                                                                        #
# HELPER FUNCTIONS BELOW. NORMAL USE SHOULD ONLY NEED THE FUNCTION ABOVE #
#                                                                        #
#                                                                        #
#                                                                        #
#                                                                        #
#                                                                        #
##########################################################################


# Creates/refreshes a dictionary of all entries from prefs.yaml
# It's named p() so that the name of the dictionary is p.refs to hopefully
# make syntax more readable since it's accessed so often. Modifying
# dictionaries during runtime is tricky, but this solution works
def p():
    file = open(YAML_FILE, "r")
    p.refs = yaml.safe_load(file)
    file.close()


p()


# Contains a few things for setting up. Most notably the Power_supply object
def setup():
    p()  # Create p.refs

    setup.psu = power_supply.Power_supply(
        ip=p.refs["psu_address"],
        port=p.refs["psu_port"],
        timeout=p.refs["psu_timeout"],
        buffer=p.refs["psu_buffer"],
        max_psu_voltage=p.refs["max_psu_voltage"],
        full_csv_path=p.refs["full_data_path"],
    )


############
## REFINE ##
############
# Refines at the given amperage for the given amount of time. All other
# parameters are pulled from prefs.yaml
def refine(current, time=p.refs["refining_period"]):
    p()  # Refresh prefs

    # "REFINING AT [X]A FOR [X] MINUTES"
    print(
        prtclrs.red
        + prtclrs.bold
        + "REFINING AT "
        + str(round(current, 2))
        + "A FOR "
        + str(round(time, 1))
        + " MINUTES"
        + prtclrs.reset
    )

    completion_time = dt.datetime.now() + dt.timedelta(minutes=time)

    # "ETA: [X]"
    print("\tETA:\t" + completion_time.strftime("%I:%M:%S %p"))

    refine_status = auto_er.refine(
        psu=setup.psu,
        refining_current=current,
        refining_period=time,
        sample_period=p.refs["sample_period"],
        resistance_tolerance=p.refs["resistance_tolerance"],
        resistance_time=p.refs["resistance_time"],
        csv_path=p.refs["data_csv_path"],
        zero_pad_data=p.refs["zero_pad_data"],
        max_refine_voltage=p.refs["max_refine_voltage"],
        max_psu_voltage=p.refs["max_psu_voltage"],
    )

    # This way it can't be changed back to True automatically
    if not refine_status:
        auto_er.refine_succeeded = False


###########
## SWEEP ##
###########
# Sweeps with the provided step duration and magnitude. All other parameters
# are pulled from prefs.yaml
def sweep(
    magnitude=p.refs["step_magnitude"],
    time=p.refs["step_duration"],
):
    p()  # Refresh Prefs

    # "STARTING SWEEP FROM [X] TO [X]"
    print(
        prtclrs.blue
        + prtclrs.bold
        + "STARTING SWEEP FROM "
        + str(round(p.refs["starting_current"], 2))
        + " TO "
        + str(round(p.refs["sweep_limit"], 2))
        + prtclrs.reset
    )

    # time_estimate = steps * step duration
    # steps = 1 + ceil(current range / step magnitude)
    current_range = p.refs["sweep_limit"] - p.refs["starting_current"]
    num_steps = 1 + math.ceil(current_range / magnitude)
    time_estimate = num_steps * time

    # Add time for measurement to help with the time_estimate's accuracy
    time_estimate += (
        num_steps * p.refs["sweep_sample_amount"] * p.refs["sample_latency"]
    )

    completion_time = dt.datetime.now() + dt.timedelta(seconds=time_estimate)

    # "ETA: [X]"
    print("\tETA:\t" + completion_time.strftime("%I:%M:%S %p"))

    auto_er.max_sec_div = auto_er.sweep(
        psu=setup.psu,
        step_duration=time,
        step_magnitude=magnitude,
        sweep_limit=p.refs["sweep_limit"],
        csv_path=p.refs["sweeps_csv_path"],
        smoothed=p.refs["smooth_sec_div"],
        starting_current=p.refs["starting_current"],
        sweep_sample_amount=p.refs["sweep_sample_amount"],
    )

    # Short print statement about sweep results
    if sweep_valid():
        if sweep_linear():
            print("\tSweep complete but was linear")

        else:
            print(
                "\tSweep complete and valid. Max sec_div of "
                + str(round(auto_er.max_sec_div_y, 2))
                + "found at "
                + str(round(auto_er.max_sec_div, 2))
                + "A"
            )
    else:
        print("\tSweep invalid!")


##############
## BACK EMF ##
##############
# Record back emf for a given amount of time. The time when
# auto_er.back_emf_at_time is recorded can also be provided here
def back_emf(
    print_time=p.refs["back_emf_print_time"],
    time=p.refs["back_emf_period"],
):
    p()  # Refresh prefs

    # "RECORDING BACK EMF FOR [X] SECONDS"
    print(
        prtclrs.green
        + prtclrs.bold
        + "RECORDING BACK EMF FOR "
        + str(round(time))
        + " SECONDS"
        + prtclrs.reset
    )

    completion_time = dt.datetime.now() + dt.timedelta(seconds=time)

    # "ETA: [X]"
    print("\tETA:\t" + completion_time.strftime("%I:%M:%S %p"))

    auto_er.back_emf_at_time = auto_er.back_emf(
        psu=setup.psu,
        back_emf_period=time,
        csv_path=p.refs["back_emf_csv_path"],
        disable_first=True,
        back_emf_print_time=print_time,
    )


# "Print Colors": dictionary of ANSI escape codes for console printing purposes
class prtclrs:
    reset = "\033[0m"
    bold = "\033[01m"
    black = "\033[30m"
    red = "\033[31m"
    green = "\033[32m"
    orange = "\033[33m"
    blue = "\033[34m"
    purple = "\033[35m"
    cyan = "\033[36m"
    lightgrey = "\033[37m"
    darkgrey = "\033[90m"
    lightred = "\033[91m"
    lightgreen = "\033[92m"
    yellow = "\033[93m"
    lightblue = "\033[94m"
    pink = "\033[95m"
    lightcyan = "\033[96m"


if __name__ == "__main__":
    p()
    main()
