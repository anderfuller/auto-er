#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" main.py

This is the high-level driver script for the autonomous electrorefining
process. Preferences and parameters are pulled from the prefs.yaml file found
in the same directory.

"""

# FIXMES in priority order
# FIXME: add sweep print statements?
# FIXME: add (back) graphing
# FIXME: add error protection/run script

import power_supply
import auto_er
import yaml
import sys
import datetime
import math

YAML_FILE = "prefs.yaml"


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


def main(debug):
    # Create a dictionary of all entries from prefs.yaml
    file = open(YAML_FILE, "r")
    prefs = yaml.safe_load(file)
    file.close()

    # Initialize a Power_supply object for communication
    psu = power_supply.Power_supply(
        ip=prefs["psu_address"],
        port=prefs["psu_port"],
        timeout=prefs["psu_timeout"],
        buffer=prefs["psu_buffer"],
        max_voltage=prefs["max_voltage"],
    )

    # Initialize our refining_current to one provided
    refining_current = prefs["first_current"]

    # Perform a sweep and override the line above by assigning refining_current
    # to our newly calculated one
    if prefs["sweep_first"]:

        print(
            prtclrs.blue
            + prtclrs.bold
            + "STARTING SWEEP FROM "
            + str(prefs["starting_current"])
            + " TO "
            + str(prefs["sweep_limit"])
            + prtclrs.reset
        )

        # time_estimate = steps * step duration
        # steps = 1 + ceil(current range / step magnitude)
        time_estimate = round(
            (
                1
                + math.ceil(
                    (prefs["sweep_limit"] - prefs["starting_current"])
                    / prefs["step_magnitude"]
                )
            )
            * prefs["step_duration"]
        )

        print(
            "\tETA:\t"
            + str(
                (
                    datetime.datetime.now()
                    + datetime.timedelta(seconds=time_estimate)
                ).time()
            )
            + " or "
            + str(round((time_estimate / 60), 2))
            + " minutes from now"
        )

        if debug:
            input("Press enter to continue")

        # Perform the sweep and get the maximum second derivative
        max_sec_div = auto_er.sweep(
            psu=psu,
            step_duration=prefs["step_duration"],
            step_magnitude=prefs["step_magnitude"],
            sweep_limit=prefs["sweep_limit"],
            csv_path=prefs["sweeps_csv_path"],
            starting_current=prefs["starting_current"],
            sweep_sample_amount=prefs["sweep_sample_amount"],
        )

        refining_current = max_sec_div * prefs["operating_percentage"]

    # Continue until the resistance shoots up, indicating the run is complete
    while True:

        #  ____  _____ _____ ___ _   _ _____
        # |  _ \| ____|  ___|_ _| \ | | ____|
        # | |_) |  _| | |_   | ||  \| |  _|
        # |  _ <| |___|  _|  | || |\  | |___
        # |_| \_\_____|_|   |___|_| \_|_____|
        #####################################

        # Refresh all the parameters
        file = open(YAML_FILE, "r")
        prefs = yaml.safe_load(file)
        file.close()

        print(
            prtclrs.red
            + prtclrs.bold
            + "REFINING AT "
            + str(refining_current)
            + "A FOR "
            + str(prefs["refining_period"])
            + " MINUTES"
            + prtclrs.reset
        )

        print(
            "\tETA:\t"
            + str(
                (
                    datetime.datetime.now()
                    + datetime.timedelta(seconds=prefs["refining_period"])
                ).time()
            )
        )

        if debug:
            input("Press enter to continue")

        refine_succeeded = auto_er.refine(
            psu=psu,
            refining_current=refining_current,
            refining_period=prefs["refining_period"],
            sample_period=prefs["sample_period"],
            resistance_tolerance=prefs["resistance_tolerance"],
            resistance_time=prefs["resistance_time"],
            csv_path=prefs["data_csv_path"],
            zero_pad_data=prefs["zero_pad_data"],
        )

        # If the resistance shot up too high for too long, end the run
        if not refine_succeeded:
            psu.disable()
            print(
                prtclrs.purple
                + prtclrs.bold
                + "RESISTANCE TOO HIGH, ENDING RUN NOW"
                + prtclrs.reset
            )

            if debug:
                input("Press enter to continue")

            break

        #  ____    _    ____ _  __     _____ __  __ _____
        # | __ )  / \  / ___| |/ /    | ____|  \/  |  ___|
        # |  _ \ / _ \| |   | ' /     |  _| | |\/| | |_
        # | |_) / ___ \ |___| . \     | |___| |  | |  _|
        # |____/_/   \_\____|_|\_\    |_____|_|  |_|_|
        ##################################################

        # Refresh all the parameters
        file = open(YAML_FILE, "r")
        prefs = yaml.safe_load(file)
        file.close()

        print(
            prtclrs.green
            + prtclrs.bold
            + "RECORDING BACK EMF FOR "
            + str(prefs["back_emf_period"])
            + " SECONDS"
            + prtclrs.reset
        )

        print(
            "\tETA:\t"
            + str(
                (
                    datetime.datetime.now()
                    + datetime.timedelta(seconds=prefs["back_emf_period"])
                ).time()
            )
        )

        if debug:
            input("Press enter to continue")

        # Record Back Emf
        auto_er.back_emf(
            psu=psu,
            back_emf_period=prefs["back_emf_period"],
            csv_path=prefs["back_emf_csv_path"],
            disable_first=True,
        )

        #  ______        _______ _____ ____
        # / ___\ \      / / ____| ____|  _ \
        # \___ \\ \ /\ / /|  _| |  _| | |_) |
        #  ___) |\ V  V / | |___| |___|  __/
        # |____/  \_/\_/  |_____|_____|_|
        #####################################

        # Refresh all the parameters
        file = open(YAML_FILE, "r")
        prefs = yaml.safe_load(file)
        file.close()

        print(
            prtclrs.blue
            + prtclrs.bold
            + "STARTING SWEEP FROM "
            + str(prefs["starting_current"])
            + " TO "
            + str(prefs["sweep_limit"])
            + prtclrs.reset
        )

        # time_estimate = steps * step duration
        # steps = 1 + ceil(current range / step magnitude)
        time_estimate = round(
            (
                1
                + math.ceil(
                    (prefs["sweep_limit"] - prefs["starting_current"])
                    / prefs["step_magnitude"]
                )
            )
            * prefs["step_duration"]
        )

        print(
            "\tETA:\t"
            + str(
                (
                    datetime.datetime.now()
                    + datetime.timedelta(seconds=time_estimate)
                ).time()
            )
            + " or "
            + str(round((time_estimate / 60), 2))
            + " minutes from now"
        )

        if debug:
            input("Press enter to continue")

        # Perform another sweep
        max_sec_div = auto_er.sweep(
            psu=psu,
            step_duration=prefs["step_duration"],
            step_magnitude=prefs["step_magnitude"],
            sweep_limit=prefs["sweep_limit"],
            csv_path=prefs["sweeps_csv_path"],
            starting_current=prefs["starting_current"],
            sweep_sample_amount=prefs["sweep_sample_amount"],
        )

        refining_current = max_sec_div * prefs["operating_percentage"]


# Just a different mode the script can run in, opens a shell-like interface
# to the power supply:
def shell():
    # Create a dictionary of all entries from prefs.yaml
    file = open(YAML_FILE, "r")
    prefs = yaml.safe_load(file)
    file.close()

    # Initialize a Power_supply object for communication
    psu = power_supply.Power_supply(
        ip=prefs["psu_address"],
        port=prefs["psu_port"],
        timeout=prefs["psu_timeout"],
        buffer=prefs["psu_buffer"],
        max_voltage=prefs["max_voltage"],
    )

    while True:
        command = input()
        print(psu.read(command + ";*OPC?"))


if __name__ == "__main__":
    debug = False

    if len(sys.argv) > 1:
        if sys.argv[1] == "--debug":
            debug = True

        elif sys.argv[1] == "--shell":
            shell()

    main(debug)
