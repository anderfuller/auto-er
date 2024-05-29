#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" power_supply.py

This module contains the logic for basic communication with our programmble
Keysight power supply.

"""

# Needed to use the TCP socket available on our power supply
import socket


class Power_supply:
    def __init__(
        self,
        ip="10.2.115.225",
        port=5025,
        timeout=5,
        buffer=1024,
        max_voltage=12.5,
    ):
        self.buffer = buffer

        self.socket = socket.socket()
        self.socket.settimeout(timeout)
        self.socket.connect((ip, port))

        self.__sendln("VOLT " + str(max_voltage))

    # Private function, simply sends a provided command to the power supply and
    # waits until it has been processed, unless the force argument is True.
    # Due to the way Python 3.x encodes strings by default, the messaage has to
    # be encoded from Unicode (UTF-16 or 32) <--> UTF-8
    def __sendln(self, message, force=False):
        # Immediately process the next command, regardless of what the power
        # supply is doing
        if force:
            self.socket.sendall("*CLS\n".encode())

        # *OPC?: "Causes the instrument to place an ASCII '1' in the Output
        #         Queue when all pending operations are completed."
        message = "*OPC?;" + message + "\n"

        self.socket.sendall(message.encode())

        # If force is False, wait until '1;' is sent from the power supply,
        # indicating that the command is completed. Otherwise move on after
        while not force:
            try:
                self.socket.recv(2)
                break

            except:
                pass

    # Returns whatever is in the socket's output buffer. If a messaage is
    # provided, send it first and return the result
    def __read(self, message=""):
        if message != "":
            self.__sendln(message)

        try:
            myOutput = self.socket.recv(self.buffer).decode()

            # Just return the first part, without the '\n'
            return myOutput.split("\n")[0]

        # If it times out, try it again
        except TimeoutError as error:
            return self.__read(message)

    # Set the current of the power supply. Note that the current will not be
    # supplied if the power supply is disabled.
    def set_current(self, current_to_set):
        self.__sendln("CURR " + str(current_to_set))

    # Enables the power supply output
    def enable(self):
        self.__sendln("OUTP ON")

    # Disables the power supply output
    def disable(self):
        self.__sendln("OUTP OFF")

    # Returns a tuple of (measured current, measured voltage)
    def measure(self):
        meas_curr = float(self.__read("MEAS:CURR?"))
        meas_volt = float(self.__read("MEAS:VOLT?"))
        print((meas_curr, meas_volt))
        return (meas_curr, meas_volt)

    # Accessor method for main.shell()
    def read(self, message):
        return self.__read(message)

    # Detach the socket when the class is deleted
    def __del__(self):
        self.disable()
        self.socket.detach()
