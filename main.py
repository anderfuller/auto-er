#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" main.py

This is the high-level driver script for the autonomous electrorefining
process. Preferences and parameters are pulled from the prefs.yaml file found
in the same directory.

"""

import power_supply
import auto_er
import yaml

YAML_FILE = "prefs.yaml"


def main():
    # Create a dictionary of all entries from prefs.yaml
    file = open(YAML_FILE, "r")
    prefs = yaml.safe_load(file)
    file.close()

    # Initialize a Power_supply object for communication
    psu = power_supply.Power_supply(
        ip=prefs["psu_address"],
        port=prefs["psu_port"],
        timeout=["psu_timeout"],
        buffer=prefs["psu_buffer"],
    )

    refining_current = prefs["first_current"]
    if prefs["sweep_first"]:
        max_sec_div = auto_er.sweep(
            psu=psu,
            step_duration=prefs["step_duration"],
            step_magnitude=prefs["step_magnitude"],
            sweep_limit=prefs["sweep_limit"],
            csv_path=prefs["sweeps_csv_path"],
        )

        refining_current = max_sec_div * prefs["operating_percentage"]

    run_completed = False

    # Continue until the resistance shoots up, indicating the run is complete
    while True:
        refine_succeeded = auto_er.refine(
            psu=psu,
            refining_current=refining_current,
            refining_period=prefs["refining_period"],
            sample_period=prefs["sample_period"],
            resistance_tolerance=prefs["resistance_tolerance"],
            resistance_time=prefs["resistance_time"],
            csv_path=prefs["data_csv_path"],
            starting_current=0.0,
            sample_amount=5,
        )

        # If the resistance shot up too high for too long, end the run
        if not refine_succeeded:
            psu.disable()
            print("all done!")
            break

        # Record Back Emf
        auto_er.back_emf(
            psu=psu,
            back_emf_period=prefs["back_emf_period"],
            csv_path=prefs["back_emf_csv_path"],
            disable_first=True,
        )

        # Perform another sweep
        max_sec_div = auto_er.sweep(
            psu=psu,
            step_duration=prefs["step_duration"],
            step_magnitude=prefs["step_magnitude"],
            sweep_limit=prefs["sweep_limit"],
            csv_path=prefs["sweeps_csv_path"],
            starting_current=0.0,
            sample_amount=5,
        )

        refining_current = max_sec_div * prefs["operating_percentage"]


if __name__ == "__main__":
    main()
