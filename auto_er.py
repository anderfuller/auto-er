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
):
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

        # If the calculated resistance is above the threshold
        if voltage / current >= resistance_tolerance:

            # If this is the first loop...
            if not high_r_state:
                # Set the start time to now
                high_r_start_time = time.time()

                # And set the high_r_state bool so the start time doesn't reset
                high_r_state = True

            # If it's had a high enough resistance for a long enough time
            if time.time() - high_r_start_time >= resistance_time:
                # Break and return False
                psu.disable()
                return False

        # If the calculated resistance is NOT above the threshold
        else:
            # Set the high_r_state to False, which will cause the
            # high_r_start_time to be reset once it is above the threshold
            # again, thus resetting the timer
            high_r_state = False

        # Then, just wait for the next sampling time
        wait(sample_period)

    return True


# Constantly records the voltage for a specified time to the csv
def back_emf(psu, back_emf_period, csv_path, disable_first=True):
    if disable_first:
        psu.disable()

    start_time = time.time()

    time_array = [""]
    voltage_array = [datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
    while time.time() - start_time <= back_emf_period:
        time_array.append(str(time.time() - start_time))

        # Index 1 of measure() is the voltage
        voltage_array.append(str(psu.measure()[1]))

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
    sample_amount=5,
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
        wait(step_duration)

        total_current = 0
        total_voltage = 0
        for i in range(0, sample_amount):
            c, v = psu.measure()
            total_current += c
            total_voltage += v

        current_array.append(total_current / sample_amount)
        voltage_array.append(total_voltage / sample_amount)

        # If we just recorded the at the sweep_limit, break
        if current_step == sweep_limit:
            break

        # Otherwise, increment it
        current_step += step_magnitude

        # But if it overshoots, bring it down to the maximum. This is to ensure
        # that there is a measurement at the maximum, even if the
        # step_magnitude would normally overshoot it. For example, with a
        # starting_current of 0.0 and a sweep_limit of 60.0 and a
        # step_magnitude of 9, the current_step would eventually reach 54.0.
        # The next value *would* be 63, but the next line of code forces it
        # down to 60 to ensure a measurement is made there.
        if current_step > sweep_limit:
            current_step = sweep_limit

    # Now with a current and voltage array, find the maximum second derivative

    # First differentiate voltage w.r.t. current
    dE_dI = np.diff(voltage_array) / np.diff(current_array)

    # Then differentiate that w.r.t. current (w/ size n-1)
    d2E_dI2 = np.diff(dE_dI) / np.diff(current_array[:-1])

    #FIXME: write to csv in best possible manner!!!!!!!

    # Current corresponding to the index of the maximum second derivative
    return float(current_array[np.argmax(d2E_dI2)])

# OLD
# import time

# import power_supply

# psu = Power_supply()

# refining_bool = True

# def calibrate():
#     psu.set_state(Psu_state.CAL)
#     current_amp = MIN_CURRENT
#     while(current_amp  <= CAL_LIMIT):
#         psu.set(current_amp)
#         wait(STEP_DURATION)
#         psu.cal_measure()
#         current_amp += STEP_MAGNITUDE

# def ocp():
#     psu.set_state(Psu_state.OCP)
#     start_time = time.time()
#     psu.disable()
#     while((time.time() - OCP_PERIOD) <= start_time):
#         psu.ocp_measure()

# # second derivative modeling
# def suggset():
#     psu.export_cal()
#     psu.export_ocp()

# def refine():
#     psu.set_state(Psu_state.REFINE)
#     start_time = time.time()
#     psu.set(REFINE_CURRENT)
#     psu.enable()
#     psu.er_measure()
#     last_measure = time.time()

#     while((time.time() - (REFINING_PERIOD * 60) <= start_time)):
#         if((time.time()  - SAMPLE_PERIOD) <= last_measure):
#             psu.er_measure()
#             last_measure = time.time()

# # MAIN LOOP
# while(refining_bool):
#     # Calibrate first
#     calibrate()
#     ocp()
#     suggest()
#     refine()
