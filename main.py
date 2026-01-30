#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""main.py

This script contains the logic for autonomous electrorefining. Users can create
their own custom Auto ER profiles within the main function. Functions for
refining, sweeping, and recording back emf are included as well.

Example profile (put in the main() function):
    refine_succeeded = True
    while refine_succeeded:

        refine_succeeded = refine(
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


def main():

    ### PHASE I: STARTUP ###
    # This phase is necessary because the resistance is sometimes high during
    # the first couple hours of refining.

    # If we want to record Back EMF every 30 minutes and sweep every 120 minutes,
    # we will just refine for 30 minutes four times:
    for i in range(0, 4):

        # First, refine for 30 minutes
        refine(
            current=20,  # 20 A
            refining_period=30,  # 30 minutes
            sample_period=5,  # Sampling voltage/current every 5 s
            voltage_limit=7,  # Hard voltage limit of 7 V at the power supply
            do_r=False,  # Do not auto-terminate
        )

        # Then, record Back EMF
        back_emf(
            record_time=60,  # Record Back EMF for 60s
        )

    # After refining for 120 minutes, perform the first sweep:
    sweep(
        min_current=0,  # 0 A (inclusive)
        max_current=25,  # 25 A (inclusive)
        current_step=1.5,  # 1.5 A between steps
        settle_time=10,  # Wait 10 s before recording the voltage and moving to the next step
        voltage_limit=12.5,  # Hard voltage limit of 12.5V at the power supply
    )

    ### PHASE II: MAINTAIN 20 A UNTIL COMPLETION ###
    # In this phase, the same procedure happens, except it will automatically terminate
    # once the resistance gets high enough.

    # Loop until exit():
    while True:

        # Again, loop 4 times for every sweep:
        for i in range(0, 4):

            # "Succeeded" means it did NOT automatically stop
            the_last_refining_period_succeeded = refine(
                current=20,  # 20 A
                refining_period=30,  # 30 minutes
                sample_period=5,  # Sampling voltage/current every 5 s
                voltage_limit=7,  # Hard voltage limit of 7 V at the power supply
                do_r=True,  # Do auto-terminate
                # If it's above 0.3 ohms for 60 consecutive seconds, stop
                r_threshold=0.3,
                r_time=60,
            )

            back_emf(
                record_time=60,  # Record Back EMF for 60s
            )

            # If the last refining period automatically stopped, terminate the run
            # (don't do another sweep at the end):
            if not the_last_refining_period_succeeded:
                # Stop the program:
                exit()

        # After refining for 120 minutes, perform a sweep:
        sweep(
            min_current=0,  # 0 A (inclusive)
            max_current=25,  # 25 A (inclusive)
            current_step=1.5,  # 1.5 A between steps
            settle_time=10,  # Wait 10 s before recording the voltage and moving to the next step
            voltage_limit=12.5,  # Hard voltage limit of 12.5V at the power supply
        )


def setup():
    """
    Required before executing the main function; creates and initializes the
    Power_supplies object that's used for communication
    """

    setup.psu = power_supplies.Power_supplies()


def refine(
    current,
    refining_period=60,
    sample_period=5,
    voltage_limit=7,
    do_r=True,
    r_threshold=0.3,
    r_time=60,
):
    """
    Refines at a specified current for a specified amount of time. If enabled,
    refining will terminate early based on the behavior of the static resistance
    and will return False. Otherwise, return True.

    Parameters
    ----------
        current : float
            refining current (in amps)
        refining_period : float, optional
            period to refine (in minutes)
        sample_period : float, optional
            the amount of time between measurements of the current and voltage
            (in seconds)
        voltage_limit : float, optional
            voltage limit enforced on the power supply during refining (in
            volts)
        do_r : bool, optional
            enables the auto-termination functionality
        r_threshold : float, optional
            if the static resistance is above this value for a specified amount
            of time, refining will automatically stop (in ohms)
        r_time : float, optional
            the amount of consecutive time that the static resistance needs to
            be above r_threshold (in seconds)

    Returns
    -------
        bool : False if the refining period terminated early due to high
               resistance, True otherwise
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
        min_current : float, optional
            current to start (in amps)
        max_current : float, optional
            current to end at (in amps)
        current_step : float, optional
            amount of current to increase between steps of the sweep (in amps)
        settle_time : float, optional
            amount of time to wait for the voltage to settle after increasing
            the current (in seconds)
        voltage_limit : float, optional
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

    # Due to our specific sensor latency, it takes about 1.5 s per step to
    # record data
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
    Records back EMF for a specified amount of time to the back_emf CSV file. It
    also prints the back EMF after a specified amount of time to the terminal.

    Parameters
    ----------
        record_time : float, optional
            duration of back EMF recording (in seconds)
        report_time : float, optional
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


# "Print colors": a helper dictionary of ANSI terminal codes to change colors
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
