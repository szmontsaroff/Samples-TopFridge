#!/usr/bin/env python3

"""
Author:  Stephen Montsaroff
Created: 11/23/2020
Project: Rigetti
File: TopFridge.py
Copyright (c) Stephen Montsaroff 2020
Description:
"""
import os
import argparse
from FridgeData import FridgeData, FrigeOutput, FormatSummaryData, FormatCycleData, format_time_period
import sys
import pickle


if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description="""
        Implements a read of data stored in pickle format from FridgeTop.
           """,
        formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument("input_file",
                        help="Name of the picke file containing history.")

    parser.add_argument('--fridge', type=int, default=-1, help= \
        """Select data from specific type=int, Fridge for display.""")
    parser.add_argument('--cycle', type=int, default=-1, help= \
        """Select data from specific cycle for display.""")

    parser.add_argument('--no_summary_data', action='store_true',
                        default=False, help="""Suppresses the output for summary data""")
    parser.add_argument('--no_cycle_data', action='store_true',
                        default=False, help="""Suppresses the output for cycle data""")

    (args, unknown) = parser.parse_known_args()
    input_file = os.path.abspath(args.input_file)
    input_dir = os.path.dirname(input_file)

    selected_cycle = args.cycle
    selected_fridge_id = args.fridge
    show_summary = not (args.no_summary_data)
    show_cycles = not (args.no_cycle_data)

    if not os.path.isfile(input_file):
        print(f"Input file: {input_file} not found.")

    with open(input_file,"rb") as pickle_file:
        history_data = pickle.load(pickle_file)
    record_times = list(history_data.keys())
    for number, time in enumerate(record_times):
        print(f"  Record {number+1}: Date {str(time)}")
    record_number = input("\nEnter valid record number to display information (or <CR> to end):")
    if not record_number.isdigit() or int(record_number) > len(record_times):
        sys.exit()

    recovered_data = history_data[record_times[int(record_number)]]
    output = ""
    for fridge_id in recovered_data['fridge_summary_data'].keys():
        if selected_fridge_id >= 0 and fridge_id != selected_fridge_id:
            continue
        summary_data = recovered_data['fridge_summary_data'][fridge_id]
        cycle_data = recovered_data['fridge_and_cycle_data'][fridge_id]
        if show_summary:
            output += f"Fridge {fridge_id} Summary:\n"
            output += FormatSummaryData(summary_data)

        if show_cycles:
            output += f"Fridge {fridge_id} Cycle Data:\n"
            output += FormatCycleData(cycle_data, cycle=selected_cycle)

        output += f"Fridge {fridge_id}: Cycle Count: {summary_data['num_of_cycles']}  " + \
                  f"Total Time: {format_time_period(summary_data['total_time'])}  " + \
                  f"Updated: {summary_data['update_timestamp']}\n\n"
    print(output.strip())

