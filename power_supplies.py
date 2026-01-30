#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""power_supplies.py

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

        self.volt_dmm_socket = socket.socket()
        self.volt_dmm_socket.connect(volt_dmm_ip_port)
        self.volt_dmm_socket.settimeout(socket_timeout)

        self.curr_dmm_socket = socket.socket()
        self.curr_dmm_socket.connect(curr_dmm_ip_port)
        self.curr_dmm_socket.settimeout(socket_timeout)

    def __appendln(self, current_dc, volt_dc):
        """
        Internal function, appends a line to the full_data CSV file

        Parameters
        ----------
            current_dc : float
                the measured dc current (in amps)
            volt_dc : float
                the measured dc voltage (in volts)
        """

        # Seconds since epoch
        time_now = dt.datetime.timestamp(dt.datetime.now())

        with open(self.full_csv_path, "a", newline="") as csvfile:
            csv.writer(csvfile).writerow(
                [
                    str(dt.datetime.timestamp(dt.datetime.now())),
                    str(current_dc),
                    str(volt_dc),
                ]
            )

    def __appendln_data(self, current_dc, volt_dc):
        """
        Internal function, appends a line to the (non-full_) data CSV file

        Parameters
        ----------
            current_dc : float
                the measured dc current (in amps)
            volt_dc : float
                the measured dc voltage (in volts)
        """
        with open(self.data_csv_path, "a", newline="") as csvfile:
            csv.writer(csvfile).writerow(
                [
                    dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    str(current_dc),
                    str(volt_dc),
                ]
            )

    def __sendln(self, socket_to_use, message, force=False):
        """
        Internal function, sends a command to the specified socket and
        (optionally) waits for a response

        Parameters
        ----------
            socket_to_use : socket.socket
                the TCP socket of the destination device
            message : str
                the SCPI message to send to the destination device
            force : bool, optional
                whether or not to:
                    1. clear the command queue on the device and
                    2. wait for the device's "command
                    complete" acknowledgement before moving on
        """

        # Clears the device's command queue (if force == True)
        if force:
            socket_to_use.sendall("*CLS\n".encode())

        # Prepend *OPC?; to the command
        message = "*OPC?;" + message + "\n"
        # *OPC?: "Causes the instrument to place an ASCII '1' in the Output
        #         Queue when all pending operations are completed."

        socket_to_use.sendall(message.encode())

        # If force is False, wait until '1;' is sent from the power supply,
        # indicating that the command is completed. Otherwise move on after
        while not force:
            try:
                socket_to_use.recv(2)
                break

            except:
                pass

    def __read(self, socket_to_use, message=None):
        """
        Internal function, sends a message (if provided) to a specified socket
        and then returns a message from that socket

        Parameters
        ----------
            socket_to_use : socket.socket
                    the TCP socket of the device
            message : str, optional
                    the SCPI message to send to the device

        Returns
        -------
            str : the SCPI output received from the device
        """

        # If a message is provided, send it to the device
        if message:
            self.__sendln(socket_to_use, message)

        try:
            socket_output = socket_to_use.recv(self.buffer).decode()

            # Just return the first part, without the '\n'
            return socket_output.split("\n")[0]

        # If it times out, try it again
        except TimeoutError as error:
            return self.__read(socket_to_use, message)

    def set_dc_voltage(self, voltage_to_set):
        """
        Public function, sets the voltage of the DC power supply

        Parameters
        ----------
            voltage_to_set : float
                voltage to set (in volts)
        """

        # Send the command "VOLT {voltage_to_set}" to the DC power supply
        self.__sendln(self.dc_socket, "VOLT " + str(voltage_to_set))

    def set_dc_current(self, current_to_set):
        """
        Public function, sets the sets the current of the DC power supply

        Parameters
        ----------
            current_to_set : float
                current to set (in amps)
        """

        # Send the command "CURR {current_to_set}" to the DC power supply
        self.__sendln(self.dc_socket, "CURR " + str(current_to_set))

    def enable_dc(self):
        """
        Public function, enables the DC power supply's output
        """

        self.__sendln(self.dc_socket, "OUTP ON")

    def disable_dc(self):
        """
        Public function, disables the DC power supply's output and also appends
        a line with zeros in the full_data CSV file to record the time when the
        power supply was disabled
        """

        self.__sendln(self.dc_socket, "OUTP OFF")
        self.__appendln(0, 0)

    def meas_dc(self):
        """
        Public function, measures the DC current and voltage and records it to
        the full_data CSV file

        Returns
        -------
            (float, float) : the DC current (in amps), the DC voltage (in volts)
        """

        # First, current is measured indirectly using a shunt resistor:
        meas_curr = float(
            # A linear regression was fit by Ander Fuller on 9/16/24 to best
            # calculate the true DC current and uses the following parameters:
            (
                float(self.__read(self.curr_dmm_socket, "MEAS:VOLT:DC?"))
                + 0.00000585503
            )
            / 0.000997256
        )
        meas_volt = float(self.__read(self.volt_dmm_socket, "MEAS:VOLT:DC?"))

        self.__appendln(meas_curr, meas_volt)

        return (meas_curr, meas_volt)

    def meas_dc_volt(self):
        """
        Public function, measures the DC voltage

        Returns
        -------
            float : DC voltage (in volts)
        """

        meas_volt = float(self.__read(self.volt_dmm_socket, "MEAS:VOLT:DC?"))
        return meas_volt

    def record_dc(self):
        """
        Public function, measures the DC current and voltage and records it to
        the (non-full_) data CSV file

        Returns
        -------
            (float, float) : the DC current (in amps), the DC voltage (in volts)
        """

        curr, volt = self.meas_dc()
        self.__appendln_data(curr, volt)
        return (float(curr), float(volt))

    def __del__(self):
        """
        When the program terminates (manually or automatically), attempt to
        disable the DC power supply, then detach the sockets
        """

        self.disable_dc()
        self.dc_socket.detach()
        self.volt_dmm_socket.detach()
        self.curr_dmm_socket.detach()
