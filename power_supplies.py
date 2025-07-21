#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" power_supplies.py

This module contains the logic for basic communication with our programmable
Keysight DC power supply, our AMETEK AC power supply, and our Keysight
digital multimeters. Since we only did one run with the AC power supply, its 
code has been commented out.

"""

# Needed to use the TCP socket available on our power supply
import socket
import csv
import datetime as dt


class Power_supplies:
    """
    Parameters
    ----------
        dc_ip_port : (str, int), optional
            IPv4 address and port for the DC power supply
        curr_dmm_ip_port : (str, int), optional
            IPv4 address and port for the digital multimeter measuring current
        volt_dmm_ip_port : (str, int), optional
            IPv4 address and port for the digital multimeter measuring voltage
        socket_timeout : int, optional
            timeout for the sockets (in seconds)
        socket_buffer : int, optional 
            size of the buffer to hold data from a socket
        data_csv_path : str, optional
            path for the main data CSV file (excluding sweeps and back
            EMF measurements)
        full_csv_path : str, optional
            path for the full data CSV file (including sweeps and back EMF 
            measurements)
    """

    def __init__(
        self,
        dc_ip_port=("192.168.0.57", 5025),
        # ac_ip_port=("169.254.55.142", 5025),
        curr_dmm_ip_port=("192.168.0.64", 5025),
        volt_dmm_ip_port=("192.168.0.36", 5025),
        socket_timeout=5,
        socket_buffer=1024,
        data_csv_path="data.csv",
        full_csv_path="full_data.csv",
    ):

        self.buffer = socket_buffer
        self.data_csv_path = data_csv_path
        self.full_csv_path = full_csv_path

        self.dc_socket = socket.socket()
        self.dc_socket.connect(dc_ip_port)
        self.dc_socket.settimeout(socket_timeout)

        # self.ac_socket = socket.socket()
        # self.ac_socket.connect(ac_ip_port)
        # self.ac_socket.settimeout(socket_timeout)

        self.volt_dmm_socket = socket.socket()
        self.volt_dmm_socket.connect(volt_dmm_ip_port)
        self.volt_dmm_socket.settimeout(socket_timeout)

        self.curr_dmm_socket = socket.socket()
        self.curr_dmm_socket.connect(curr_dmm_ip_port)
        self.curr_dmm_socket.settimeout(socket_timeout)

    # Internal function, appends a line to the full_data CSV file
    def __appendln(self, current_dc, volt_dc):
        # Seconds since epoch
        time_now = dt.datetime.timestamp(dt.datetime.now())
        with open(self.full_csv_path, "a", newline="") as csvfile:
            csv.writer(csvfile).writerow(
                [
                    str(dt.datetime.timestamp(dt.datetime.now())),
                    str(current_dc),
                    str(volt_dc),
                    # current_ac,
                    # volt_ac,
                    # freq,
                ]
            )

    # Internal function, appends a line to the (non-full) data CSV file
    def __appendln_data(self, current_dc, volt_dc):
        with open(self.data_csv_path, "a", newline="") as csvfile:
            csv.writer(csvfile).writerow(
                [
                    dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    str(current_dc),
                    str(volt_dc),
                    # current_ac,
                    # volt_ac,
                    # freq,
                ]
            )

    # Internal function, sends a command to the specified socket and (opionally)
    # waits for a response
    def __sendln(self, socket_to_use, message, force=False):
        if force:
            socket_to_use.sendall("*CLS\n".encode())  # Clears the output queue

        # *OPC?: "Causes the instrument to place an ASCII '1' in the Output
        #         Queue when all pending operations are completed."
        message = "*OPC?;" + message + "\n"

        socket_to_use.sendall(message.encode())

        # If force is False, wait until '1;' is sent from the power supply,
        # indicating that the command is completed. Otherwise move on after
        while not force:
            try:
                socket_to_use.recv(2)
                break

            except:
                pass

    # Internal function, sends a message (if provided) to a specifed socket and
    # then returns a message from that socket
    def __read(self, socket_to_use, message=""):
        if message != "":
            self.__sendln(socket_to_use, message)

        try:
            myOutput = socket_to_use.recv(self.buffer).decode()

            # Just return the first part, without the '\n'
            return myOutput.split("\n")[0]

        # If it times out, try it again
        except TimeoutError as error:
            return self.__read(socket_to_use, message)

    # Public function, sets the voltage of the DC power supply
    def set_dc_voltage(self, voltage_to_set):
        self.__sendln(self.dc_socket, "VOLT " + str(voltage_to_set))

    # Public function, sets the current of the DC power supply
    def set_dc_current(self, current_to_set):
        self.__sendln(self.dc_socket, "CURR " + str(current_to_set))

    # Public function, enables the DC power supply's output
    def enable_dc(self):
        self.__sendln(self.dc_socket, "OUTP ON")

    # Public function, disables the DC power supply's output and also appends a
    # line with zeros in the full_data CSV file to record the time
    def disable_dc(self):
        self.__sendln(self.dc_socket, "OUTP OFF")
        self.__appendln(0, 0)

    # Public function, calculates the DC current by measurring the voltage drop
    # across the shunt resistor
    def meas_dc(self):

        # A linear regression was fit by Ander Fuller on 9/16/24 to best 
        # calculate the true DC current and uses the following parameters:
        meas_curr = float(
            (float(self.__read(self.curr_dmm_socket, "MEAS:VOLT:DC?")) + 0.00000585503)
            / 0.000997256
        )
        meas_volt = float(self.__read(self.volt_dmm_socket, "MEAS:VOLT:DC?"))

        self.__appendln(meas_curr, meas_volt)

        return (meas_curr, meas_volt)

    # Public function, measures the DC voltage
    def meas_dc_volt(self):
        meas_volt = float(self.__read(self.volt_dmm_socket, "MEAS:VOLT:DC?"))
        return meas_volt

    # Public function, measures and records the DC current and voltage
    def record_dc(self):
        curr, volt = self.meas_dc()
        self.__appendln_data(curr, volt)
        return (float(curr), float(volt))

    # def set_ac_voltage(self, voltage_to_set):
    #     self.__sendln(self.ac_socket, "MODE ACDC")
    #     self.__sendln(self.ac_socket, "VOLT " + str(voltage_to_set))

    # def set_dc_offset(self, voltage_to_set):
    #     self.__sendln(self.ac_socket, "MODE ACDC")
    #     self.__sendln(self.ac_socket, "VOLT:OFFS " + str(voltage_to_set))

    # def enable_ac(self):
    #     self.__sendln(self.ac_socket, "MODE ACDC")
    #     self.__sendln(self.ac_socket, "OUTPUT:RI:LEVEL LOW")
    #     self.__sendln(self.ac_socket, "FREQ 1000")
    #     self.__sendln(self.ac_socket, "OUTP ON")

    # def disable_ac(self):
    #     self.__sendln(self.ac_socket, "OUTP OFF")
    #     self.__appendln(0, 0)

    # def meas_ac(self):
    #     dc_curr = float(self.__read(self.ac_socket, "MEAS:CURR:DC?"))
    #     dc_volt = float(self.__read(self.dmm_socket, "MEAS:VOLT:DC?"))
    #     ac_curr = float(self.__read(self.ac_socket, "MEAS:CURR:AC?"))
    #     ac_volt = float(self.__read(self.dmm_socket, "MEAS:VOLT:AC?"))
    #     freq = float(self.__read(self.dmm_socket, "MEAS:FREQ?"))
    #     print((dc_curr, dc_volt, ac_curr, ac_volt, freq))
    #     self.__appendln(dc_curr, dc_volt, ac_curr, ac_volt, freq)

    #     return (dc_curr, dc_volt, ac_curr, ac_volt, freq)

    # def record_ac(self):
    #     dc_curr, dc_volt, ac_curr, ac_volt, freq = self.meas_ac()
    #     self.__appendln_data(dc_curr, dc_volt, ac_curr, ac_volt, freq)

    # Attempt to disable the power supply before detaching the sockets
    def __del__(self):
        self.disable_dc()
        # self.disable_ac()
        self.dc_socket.detach()
        # self.ac_socket.detach()
        self.volt_dmm_socket.detach()
        self.curr_dmm_socket.detach()
