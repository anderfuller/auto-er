#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" power_supply.py

This module contains the logic for basic communication with our programmble
Keysight power supply.

"""

# Needed to use the TCP socket available on our power supply
import socket


class Power_supply:
    def __init__(self, ip="10.2.115.225", port=5025, timeout=5, buffer=1024):
        self.buffer = buffer

        self.socket = socket.socket()
        self.socket.settimeout(5)
        self.socket.connect((ip, port))

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

        # If force is False, wait until '1\n' is sent from the power supply,
        # indicating that the command is completed. Otherwise move on after
        while not force:
            try:
                self.mySocket.recv(2).decode()  # FIXME: 1 or 2??
                break

            except:
                pass

    # Returns whatever is in the socket's output buffer. If a messaage is
    # provided, send it first and return the result
    def __read(self, message=""):
        if message != "":
            self.__sendln(message)

        try:
            myOutput = self.mySocket.recv(self.buffer).decode()

            # Just return the first part, without the '\n'
            return myOutput.split("\n")[0]

        # If it times out, try it again
        except TimeoutError as error:
            return self.__read(message)

    # Set the current of the power supply. Note that the current will not be
    # supplied if the power supply is disabled.
    def set_current(self, current_to_set):
        self.__sendln("CURR" + str(current_to_set))

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
        return (meas_curr, meas_volt)

    # Changes some settings that are needed after the power supply turns on
    def first_time_setup(self, max_current):
        print("FIXME: change to current limited with correct limits")

    # Detach the socket when the class is deleted
    def __del__(self):
        self.socket.detach()


# ## OLD

# import socket
# from enum import Enum
# import time
# import csv
# from datetime import datetime
# import matplotlib.pyplot as plt
# import numpy as np
# import prefs

# import threading
# import asyncio

# global SET_CURRENT
# global SWEEP_INTERVAL
# global FULL_AUTO
# global RECORD_INTERVAL
# global DO_CSWEEP
# global DO_VSWEEP
# global CSTEP_SIZE
# global STEP_DURATION
# global STARTING_CURRENT
# global CAL_LIMIT
# global MIN_CURRENT
# global VSTEP_SIZE
# global STARTING_VOLTAGE
# global BEMF_SETTLE_PERIOD
# global IP
# global PORT
# global SOCKET_TIMEOUT
# global BUFFER


# class Psu_state(Enum):
#     INIT = 0
#     CAL = 1
#     OCP = 2
#     REFINE = 3


# class Power_supply:
#     def __init__(self, ip="10.2.115.225", port=5025):
#         self.state = Psu_state.INIT
#         self.mySocket = socket.socket()
#         self.mySocket.settimeout(5)
#         self.mySocket.connect((ip, port))
#         self.mySocket.settimeout(0.1)
#         self.mySocket.sendall("*OPC\n".encode())

#         self.last_current = 0.0
#         self.ocp_start_time = time.time()

#         # SET CURRENT, MEAS CURRENT, MEAS VOLTAGE
#         self.cal_array = np.array([[]])

#         # TIME (since disable), MEAS VOLTAGE
#         self.ocp_array = np.array([])

#     def __sendln(self, message):
#         message = "*WAI;*OPC;*OPC?;" + message + "\n"
#         self.mySocket.sendall("*CLS\n".encode())
#         self.mySocket.sendall(message.encode())

#         notPassed = True
#         while notPassed:
#             try:
#                 self.mySocket.recv(2).decode()
#                 notPassed = False
#             except:
#                 pass

#     def __read(self, message=""):
#         if message != "":
#             self.__sendln(message)

#         try:
#             myOutput = self.mySocket.recv(1024).decode()
#             return myOutput.split("\n")[0]
#         except TimeoutError as error:
#             return self.__read(message)

#     def set_state(self, state):
#         self.state = state

#     def enable(self):
#         self.__sendln("OUTP ON")

#     def disable(self):
#         self.__sendln("OUTP OFF")
#         # print(self.__read("OUTP?"))

#     def set_current(self, current_to_set):
#         self.last_current = round(current_to_set, 3)
#         self.__sendln("CURR " + str(self.last_current))

#     def cal_measure(self):
#         curr_fetch = self.__read("MEAS:CURR?")
#         volt_fetch = self.__read("MEAS:VOLT?")
#         print(curr_fetch, volt_fetch)

#         if self.cal_array.size < 1:
#             self.cal_array = np.array(
#                 [
#                     [
#                         float(self.last_current),
#                         float(curr_fetch),
#                         float(volt_fetch),
#                     ]
#                 ]
#             )
#         else:
#             self.cal_array = np.append(
#                 self.cal_array,
#                 [
#                     [
#                         float(self.last_current),
#                         float(curr_fetch),
#                         float(volt_fetch),
#                     ]
#                 ],
#                 axis=0,
#             )

#     def ocp_measure(self):
#         volt_fetch = self.__read("MEAS:VOLT?")
#         if self.ocp_array.size < 1:
#             self.ocp_start_time = time.time()
#             self.ocp_array = np.array(
#                 [[float(time.time() - self.ocp_start_time), float(volt_fetch)]]
#             )

#         else:
#             self.ocp_array = np.append(
#                 self.ocp_array,
#                 [
#                     [
#                         float(time.time() - self.ocp_start_time),
#                         float(volt_fetch),
#                     ]
#                 ],
#                 axis=0,
#             )

#     def graph_cal(self):
#         deriv_array = np.array([])
#         max_index = 0
#         max_ratio = 0
#         with np.errstate(divide="ignore", invalid="ignore"):
#             a = self.cal_array
#             for i in range(0, len(a) - 2):
#                 mydiv = (a[i + 1][2] - a[i][2]) / (a[i + 1][1] - a[i][1])
#                 mynextDiv = (a[i + 2][2] - a[i + 1][2]) / (
#                     a[i + 2][1] - a[i + 1][1]
#                 )
#                 ratio = (mynextDiv - mydiv) / (a[i + 1][1] - a[i][1])
#                 if np.isinf(ratio) or np.isneginf(ratio) or np.isnan(ratio):
#                     ratio = 0
#                 if ratio > max_ratio:
#                     max_ratio = ratio
#                     max_index = i

#         copy_array = np.array(self.cal_array, copy=True)
#         graph_thread1 = threading.Thread(
#             name="graph_thread1",
#             target=show_graph,
#             daemon=True,
#             args=(copy_array,),
#         )
#         graph_thread1.start()

#         print("\x1b[33m" + str(a[max_index][0]) + " is the max!\x1b[0m")
#         return a[max_index][0]

#     def export_cal(self):
#         data_to_write = [""] * (((60 + 2) * 100) + 1)
#         for row in self.cal_array:
#             curr_index = int(row[0] * 100) + 101
#             data_to_write[curr_index] = str(row[2])

#         data_to_write[0] = datetime.now().strftime("%m/%d/%Y %H:%M:%S")

#         with open("sweep.csv", "a", newline="") as csvfile:
#             csv.writer(csvfile).writerow(data_to_write)

#         self.cal_array = np.array([])

#         try:
#             os.system(
#                 'xcopy . "..\\..\\Box\\Rappleye Research\\Projects\\Auto ER\\Experiments\\2024-05-06 ER Run 5\\data_dump" /Y >nul 2>&1'
#             )
#         except:
#             print("Could not backup the directory to Box!")

#     def export_ocp(self):
#         data_to_write = [""] * (self.ocp_array.size + 1)
#         # print(self.ocp_array)
#         i = 0
#         for row in self.ocp_array:
#             data_to_write[i + 1] = row[0]
#             i = i + 1

#         with open("ocp.csv", "a", newline="") as csvfile:
#             csv.writer(csvfile).writerow(data_to_write)

#         data_to_write2 = [""] * (self.ocp_array.size + 1)
#         data_to_write2[0] = datetime.now().strftime("%m/%d/%Y %H:%M:%S")
#         i = 0
#         for row in self.ocp_array:
#             data_to_write2[i + 1] = row[1]
#             i = i + 1

#         with open("ocp.csv", "a", newline="") as csvfile:
#             csv.writer(csvfile).writerow(data_to_write2)

#         # print("exported")

#         self.ocp_array = np.array([[]])

#         # for row in self.ocp_array:

#     def er_measure(self):
#         curr_fetch = self.__read("MEAS:CURR?")
#         volt_fetch = self.__read("MEAS:VOLT?")

#         data_to_write = [
#             datetime.now().strftime("%m/%d/%Y %H:%M:%S"),
#             str(curr_fetch),
#             str(volt_fetch),
#         ]
#         with open("data.csv", "a", newline="") as csvfile:
#             csv.writer(csvfile).writerow(data_to_write)


# def show_graph(myArray):
#     plt.clf()
#     plt.scatter(myArray[:, 0], myArray[:, 2])
#     plt.show()
