#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" auto_er.py

This module contains the logic for each part of the autonomous electrorefining
process. Note that a higher level driver function is needed to perform the
overall process and provide parameters

"""

import power_supply
import time
import datetime
import csv
import numpy as np


# Refine at a specified current for a period, sampling current and voltage
# throughout the process. Returns True after a successful refining period and
# False if the calculated resistance shoots up too high for a long enough
# period
def refine(
    psu,
    refining_current,
    refining_period,
    sample_period,
    resistance_tolerance,
    resistance_time,
    csv_path,
    zero_pad_data=True,
):
    # Add a row of zeroes to make integrating over the data easier (for total
    # charged passed, faradaic efficiency, etc.). We assume the charge
    # passed during non-refining is zero and thus can calculate it better.
    if zero_pad_data:
        with open(csv_path, "a", newline="") as csvfile:
            csv.writer(csvfile).writerow(
                [
                    datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "0.0",
                    "0.0",
                ]
            )

    psu.enable()

    start_time = time.time()
    psu.set_current(refining_current)
    high_r_state = False

    # Until enough time has passed...
    while time.time() - start_time <= refining_period * 60:
        current, voltage = psu.measure()

        # Record the current and voltage to the csv
        with open(csv_path, "a", newline="") as csvfile:
            csv.writer(csvfile).writerow(
                [
                    datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    current,
                    voltage,
                ]
            )

        calculated_resistance = 0
        try:
            calculated_resistance = voltage / current
        except:
            pass

        # If the calculated resistance is above the threshold
        if calculated_resistance >= resistance_tolerance:

            # If this is the first loop...
            if not high_r_state:
                # Set the start time to now
                high_r_start_time = time.time()

                # And set the high_r_state bool so the start time doesn't reset
                high_r_state = True

            # If it's had a high enough resistance for a long enough time
            if time.time() - high_r_start_time >= resistance_time:
                psu.disable()  # Disable the power supply,
                if zero_pad_data:  # Add a row of zeroes,
                    with open(csv_path, "a", newline="") as csvfile:
                        csv.writer(csvfile).writerow(
                            [
                                datetime.datetime.now().strftime(
                                    "%Y-%m-%d %H:%M:%S"
                                ),
                                "0.0",
                                "0.0",
                            ]
                        )

                # Break, and return False
                return False

        # If the calculated resistance is NOT above the threshold
        else:
            # Set the high_r_state to False, which will cause the
            # high_r_start_time to be reset once it is above the threshold
            # again, thus resetting the timer
            high_r_state = False

        # Then, just wait for the next sampling time
        time.sleep(sample_period)

        # Add a row of zeroes indicating we are done refining
        if zero_pad_data:
            with open(csv_path, "a", newline="") as csvfile:
                csv.writer(csvfile).writerow(
                    [
                        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "0.0",
                        "0.0",
                    ]
                )

    return True


# Constantly records the voltage for a specified time to the csv
def back_emf(psu, back_emf_period, csv_path, disable_first=True):
    if disable_first:
        psu.disable()

    start_time = time.time()

    time_array = [""]
    voltage_array = [datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
    while time.time() - start_time <= back_emf_period:
        # Index 1 of measure() is the voltage
        voltage_array.append(str(psu.measure()[1]))
        time_array.append(str(time.time() - start_time))

    with open(csv_path, "a", newline="") as csvfile:
        csv.writer(csvfile).writerow(time_array)
        csv.writer(csvfile).writerow(voltage_array)


# Performs a current sweep with the specified parameters and returns the
# current corresponding to the maximum second derivative from the sweep
def sweep(
    psu,
    step_duration,
    step_magnitude,
    sweep_limit,
    csv_path,
    starting_current=0.0,
    sweep_sample_amount=5,
):
    current_step = starting_current
    psu.set_current(starting_current)
    current_array = []
    voltage_array = []

    start_time = time.time()
    psu.enable()

    # Runs until the maximum measurement has been made (see comments below)
    while True:
        psu.set_current(current_step)
        time.sleep(step_duration)

        total_current = 0
        total_voltage = 0
        for i in range(0, sweep_sample_amount):
            c, v = psu.measure()
            total_current += c
            total_voltage += v

        current_array.append(total_current / sweep_sample_amount)
        voltage_array.append(total_voltage / sweep_sample_amount)

        # If we just recorded at the sweep_limit, break
        if current_step == sweep_limit:
            break

        # Otherwise, increment it
        current_step += step_magnitude
        print("CURRENT_STEP:")
        print(current_step)

        # But if it overshoots, bring it down to the maximum. This is to ensure
        # that there is a measurement at the maximum, even if the
        # step_magnitude would normally overshoot it. For example, with a
        # starting_current of 0.0 and a sweep_limit of 60.0 and a
        # step_magnitude of 9, the current_step would eventually reach 54.0.
        # The next value *would* be 63, but the next line of code forces it
        # down to 60 to ensure a measurement is made there.
        if current_step > sweep_limit:
            current_step = sweep_limit

    # Export the data to .csv first
    with open(csv_path, "a", newline="") as csvfile:
        # Add in the first column so each sweep appended to the .csv is:
        # +-----------+-----------+-----------+-----------+----
        # |  (blank)  | current_0 | current_1 | current_2 | ...
        # +-----------+-----------+-----------+-----------+----
        # | timestamp | voltage_0 | voltage_1 | voltage_2 | ...
        # +-----------+-----------+-----------+-----------+----

        current_row = [""]
        voltage_row = [datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
        for c in current_array:
            current_row.append(str(c))

        for v in voltage_array:
            voltage_row.append(str(v))

        csv.writer(csvfile).writerow(current_row)
        csv.writer(csvfile).writerow(voltage_row)

    # Now with a current and voltage array, find the maximum second derivative

    # Ignore any divide by zero errors, as they are handled below
    with np.errstate(divide="ignore", invalid="ignore"):
        # First differentiate voltage w.r.t. current
        dE_dI = np.where(
            # Any zeros in the denominator will now result in the quotient
            # being zero
            np.diff(current_array) == 0,  # If entry is zero
            0,  # Set to zero
            np.diff(voltage_array)
            / np.diff(current_array),  # Otherwise divide
        )

        # Then differentiate that w.r.t. current (w/ size n-1)
        d2E_dI2 = np.where(
            np.diff(current_array)[:-1] == 0,
            0,
            np.diff(dE_dI) / np.diff(current_array)[:-1],
        )

    max_sec_div = float(current_array[np.argmax(d2E_dI2)])

    # Current corresponding to the index of the maximum second derivative
    return max_sec_div
