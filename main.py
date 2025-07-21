#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" main.py

This script contains the logic for autonomous electrorefining. Users can create
their own custom Auto ER profiles within the main function. Functions for
refining, sweeping, and recording back emf are included as well.

Example profile (put in the main() function):
    refine_succeeded = True
    while refine_succeeded:

        refine_succeeded = refine_dc(
            current=10,
            refining_period=60,
            sample_period=5,
            voltage_limit=7,
            do_r=True,
            r_threshold=0.3,
            r_time=60,
        )

        sweep(
            min_current=0,
            max_current=60,
            current_step=1.5,
            settle_time=10,
            voltage_limit=12.5,
        )

        back_emf(
            record_time=60,
            report_time=45,
        )

"""

import power_supplies
import datetime as dt
import time
import csv
import sys
import math


# Create your own custom Auto ER profile in the following function:
def main():

    ### PHASE I: 10 -> 15 -> 20 ###
    # Avoids any weird resistance things that happen initally, will force
    # 10 -> 15 -> 20

    back_emf()

    refine_dc(current=10, refining_period=60, do_r=False)
    back_emf()
    sweep(max_current=20)

    refine_dc(current=15, refining_period=60, do_r=False)
    back_emf()
    sweep(max_current=25)

    refine_dc(current=20, refining_period=60, do_r=False)
    back_emf()
    sweep(max_current=30)

    ### PHASE II: Increase by 5 until "failure" (R too high) ###
    refine_succeeded = True
    current_up = 25

    # Until R gets too high, loop
    while refine_succeeded:
        refine_succeeded = refine_dc(current=current_up, refining_period=60)
        back_emf()

        # To avoid sweeping too agressively, only go from
        # 0 -> operarting current + 10

        max_current = current_up + 10
        if max_current > 60:
            max_current = 60

        if refine_succeeded:
            sweep(max_current=max_current)

        current_up = current_up + 5

        # Max it out at 60 A
        if current_up >= 60:
            current_up = 60

    # Once it fails:
    refine_succeeded = True
    ### PHASE III: Decrease by 5 every time it fails until 15 ###

    # First current is 5 less than failing point
    current_down = current_up - 5

    # As long as current is at least 20:
    while current_down >= 20:

        # Maintain current until "failure"
        while refine_succeeded:
            refine_succeeded = refine_dc(
                current=current_down, refining_period=60
            )
            back_emf()

            # To avoid sweeping too agressively, only go from
            # 0 -> operarting current + 10

            max_current = current_down + 10
            if max_current > 60:
                max_current = 60

            if refine_succeeded:
                sweep(max_current=max_current)

        # Once it "fails," decrease operating current by 5 and repeat
        current_down = current_down - 5
        refine_succeeded = True

    # Once current is less than 20 (15), stop


def setup():
    """
    Required before executing the main function; creates and initializes the
    Power_supplies object that's used for communication
    """

    setup.psu = power_supplies.Power_supplies()


def refine_dc(
    current,
    refining_period=60,
    sample_period=5,
    voltage_limit=7,
    do_r=True,
    r_threshold=0.3,
    r_time=60,
):
    """
    Refines at a specifed current for a specifed amount of time. If enabled,
    refining will terminate early based on the behavior of the static resistance
    and will return False. Otherwise, return True.

    Parameters
    ----------
        current : int or float
            refining current (in amps)
        refining_period : int or float, optional
            period to refine (in minutes)
        sample_period : int or float, optional
            the amount of time between measurements of the current and voltage
            (in seconds)
        voltage_limit : int or float, optional
            voltage limit enforced on the power supply during refining (in
            volts)
        do_r : bool, optional
            enables the auto-termination functionality
        r_threshold : int or float, optional
            if the static resistance is above this value for a specified amount
            of time, refining will automatically stop (in ohms)
        r_time : int or float, optional
            the amount of consecutive time that the static resistance needs to
            be above r_threshold (in seconds)
    """

    print(
        prtclrs.red
        + prtclrs.bold
        + "REFINING DC AT "
        + f"{current:05.2f}"
        + "A FOR "
        + f"{refining_period:0.0f}"
        + " MINUTES"
        + prtclrs.reset
    )

    completion_time = dt.datetime.now() + dt.timedelta(minutes=refining_period)

    # "ETA: [X]"
    print("\tETA:\t" + completion_time.strftime("%I:%M:%S %p"))

    setup.psu.disable_dc()

    setup.psu.set_dc_voltage(voltage_limit)
    setup.psu.set_dc_current(current)
    setup.psu.enable_dc()

    start_time = time.time()

    high_r_state = False

    while time.time() - start_time <= refining_period * 60:
        curr, volt = setup.psu.record_dc()
        calculated_resistance = 0

        try:
            calculated_resistance = volt / curr
        except:
            pass

        if do_r:
            if calculated_resistance >= r_threshold:
                if not high_r_state:
                    high_r_start_time = time.time()
                    high_r_state = True

                if time.time() - high_r_start_time >= r_time:
                    setup.psu.disable_dc()
                    return False

                print(
                    prtclrs.purple
                    + "Calculated resistance above threshold.\t"
                    + str(round(60 - (time.time() - high_r_start_time), 1))
                    + "s until termination."
                    + prtclrs.reset
                )

            else:
                high_r_state = False

        time.sleep(sample_period)

    setup.psu.disable_dc()
    return True


def sweep(
    min_current=0,
    max_current=60,
    current_step=1.5,
    settle_time=10,
    voltage_limit=12.5,
):
    """
    Performs a current sweep and appends the data to the sweeps CSV file.

    Parameters
    ----------
        min_current : int or float, optional
            optional, current to start (in amps)
        max_current : int or float, optional
            current to end at (in amps)
        current_step : int or float, optional
            amount of current to increase between steps of the sweep (in amps)
        settle_time : int or float, optional
            amount of time to wait for the voltage to settle after increasing
            the current (in seconds)
        voltage_limit : int or float, optional
            voltage limit enforced on the power supply while sweeping (in volts)
    """

    print(
        prtclrs.blue
        + prtclrs.bold
        + "STARTING SWEEP FROM "
        + str(min_current)
        + "A -> "
        + str(max_current)
        + "A"
        + prtclrs.reset
    )

    num_steps = math.ceil((max_current - min_current) / current_step + 1)

    # Due to sensor latency, it takes about 1.5s per step to record data
    duration = num_steps * (settle_time + 1.5)

    completion_time = dt.datetime.now() + dt.timedelta(seconds=duration)
    print("\tETA:\t" + completion_time.strftime("%I:%M:%S %p"))

    setup.psu.set_dc_voltage(voltage_limit)
    setup.psu.set_dc_current(min_current)

    start_time = time.time()
    start_dt = dt.datetime.now()
    setup.psu.enable_dc()

    curr_array = []
    volt_array = []

    step = 0
    # Increase by the set amount until you meet or exceed the max current
    while step < max_current:
        setup.psu.set_dc_current(step)
        setup.psu.meas_dc()

        time.sleep(settle_time)

        curr, volt = setup.psu.meas_dc()
        curr_array.append(curr)
        volt_array.append(volt)

        step += current_step

    # After meeting or exceeding the max current, do one last step at the max
    # current:
    setup.psu.set_dc_current(max_current)
    setup.psu.meas_dc()

    time.sleep(settle_time)
    curr, volt = setup.psu.meas_dc()
    curr_array.append(curr)
    volt_array.append(volt)

    setup.psu.disable_dc()

    with open("sweeps.csv", "a", newline="") as csvfile:
        # Add in the first column so each sweep appended to the .csv is:
        # +-----------+-----------+-----------+-----------+----
        # |  (blank)  | current_0 | current_1 | current_2 | ...
        # +-----------+-----------+-----------+-----------+----
        # | timestamp | voltage_0 | voltage_1 | voltage_2 | ...
        # +-----------+-----------+-----------+-----------+----

        current_row = [""]
        voltage_row = [start_dt.strftime("%Y-%m-%d %H:%M:%S")]
        for c in curr_array:
            current_row.append(str(c))

        for v in volt_array:
            voltage_row.append(str(v))

        csv.writer(csvfile).writerow(current_row)
        csv.writer(csvfile).writerow(voltage_row)


def back_emf(
    record_time=60,
    report_time=45,
):
    """
    Records back EMF for a specifed amount of time to the back_emf CSV file. It
    also prints the back EMF after a specifed amount of time to the terminal.

    Parameters
    ----------
        record_time : int or float, optional
            duration of back EMF recording (in seconds)
        report_time : int or float, optional
            print the voltage to the terminal after this amount of time has
            passed (in seconds)
    """

    print(
        prtclrs.green
        + prtclrs.bold
        + "RECORDING BACK EMF FOR "
        + str(record_time)
        + " SECONDS"
        + prtclrs.reset
    )

    time_array = [""]
    volt_array = [dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")]

    start_time = time.time()
    bemf_printed = False

    while time.time() - start_time <= record_time:
        volt = setup.psu.meas_dc_volt()
        volt_array.append(str(float(volt)))
        time_array.append(str(time.time() - start_time))

        if time.time() - start_time >= report_time and not bemf_printed:
            print(
                prtclrs.green
                + "Back emf voltage at "
                + str(report_time)
                + "s:\t"
                + str(volt)
                + prtclrs.reset
            )
            bemf_printed = True

    with open("back_emf.csv", "a", newline="") as csvfile:
        csv.writer(csvfile).writerow(time_array)
        csv.writer(csvfile).writerow(volt_array)


# "Print colors": a helper dictionary of terminal codes to change color
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
    setup()
    main()

# Obsolete function, was used to capture data to fit to a transfer function
# def refine_xfer(
#     current,
#     xfer_period=2,
#     refining_period=60,
#     sample_period=5,
#     voltage_limit=7,
#     do_r=True,
#     r_threshold=0.3,
#     r_time=60,
# ):
#     """
#     Wrapper function for refine_dc(). It rapidally records the DC voltage at the
#     start of the refining period, then refines normally. The purpose is to
#     collect data to then fit to a transfer (xfer) function.

#     Parameters
#     ----------
#         current : int or float
#             refining current (in amps)
#         xfer_period : int or float
#             time to rapidally record the DC voltage (in minutes)
#         refining_period : int or float, optional
#             total period to refine (in minutes)
#         sample_period : int or float, optional
#             the amount of time between measurements of the current and voltage
#             (in seconds)
#         voltage_limit : int or float, optional
#             voltage limit enforced on the power supply during refining (in
#             volts)
#         do_r : bool, optional
#             enables the auto-termination functionality
#         r_threshold : int or float, optional
#             if the static resistance is above this value for a specified amount
#             of time, refining will automatically stop (in ohms)
#         r_time : int or float, optional
#             the amount of consecutive time that the static resistance needs to
#             be above r_threshold (in seconds)
#     """

#     print(
#         prtclrs.orange
#         + prtclrs.bold
#         + "BRIEFLY REFINING DC AT "
#         + f"{current:05.2f}"
#         + "A FOR "
#         + f"{xfer_period:0.0f}"
#         + " MINUTES TO COLLECT DATA FOR A XFER FUNCTION"
#         + prtclrs.reset
#     )

#     setup.psu.disable_dc()

#     setup.psu.set_dc_voltage(voltage_limit)
#     setup.psu.set_dc_current(current)

#     start_time = time.time()
#     setup.psu.enable_dc()

#     curr, volt = setup.psu.record_dc()

#     while time.time() - start_time <= xfer_period * 60:
#         setup.psu.record_dc_volt(curr)

#     setup.psu.disable_dc()

#     return refine_dc(
#         current=current,
#         refining_period=refining_period - xfer_period,
#         sample_period=sample_period,
#         voltage_limit=voltage_limit,
#         do_r=do_r,
#         r_threshold=r_threshold,
#         r_time=r_time,
#     )

# Obsolete function used for AC refining
# def refine_ac(ac_volt, dc_offset, refining_period=60):

#     print(
#         prtclrs.red
#         + prtclrs.bold
#         + "REFINING AC+DC AT "
#         + str(round(dc_offset, 2))
#         + "+/- "
#         + str(round(ac_volt, 2))
#         + "FOR 60 MINUTES"
#         + prtclrs.reset
#     )

#     completion_time = dt.datetime.now() + dt.timedelta(minutes=refining_period)

#     # "ETA: [X]"
#     print("\tETA:\t" + completion_time.strftime("%I:%M:%S %p"))

#     setup.psu.disable_ac()
#     setup.psu.set_ac_voltage(ac_volt)
#     setup.psu.set_dc_offset(dc_offset)

#     start_time = time.time()
#     setup.psu.enable_ac()
#     print("here")
#     while time.time() - start_time <= refining_period * 60:
#         print("there")
#         setup.psu.record_ac()
#         time.sleep(5)

#     setup.psu.disable_ac()
