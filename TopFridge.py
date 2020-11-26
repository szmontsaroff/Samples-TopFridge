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
import time
import argparse
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
from FridgeData import FridgeData, FrigeOutput
import sys

class TopFridgeHandler(PatternMatchingEventHandler):
    def __init__(self, patterns, fridge_data, **kwargs):
        super().__init__(patterns)
        self._fridge_data = fridge_data
        self._selected_fridge_id = -1
        self._selected_cycle = -1
        self._show_summary = True
        self._show_cycles = True
    
        if 'cycle' in kwargs:
            self._selected_cycle = kwargs['cycle']
        if 'fridge_id' in kwargs:
            self._selected_fridge_id = kwargs['fridge_id']
        if 'self._showCycles' in kwargs:
            self._showCycles = kwargs['showCycles']
        if 'self._showSummary' in kwargs:
            self._showSummary = kwargs['showSummary']

    def on_deleted(self, event):
        super(TopFridgeHandler, self).on_deleted(event)
        print("Exiting: File %s was just deleted" % event.src_path)
        sys.exit(0)

    def on_modified(self, event):
        super(TopFridgeHandler, self).on_modified(event)
        print("File %s was just modified" % event.src_path)

        lines = open(event.src_path, "r").readlines()
        self._fridge_data.Update(lines)
        print(FrigeOutput(self._fridge_data,
                        showSummary=self._show_summary, showCycles=self._show_cycles,
                        cycles=self._selected_cycle, fridge_id=self._selected_fridge_id))

if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description="""
        Implements a 'topc' sort of program for fridge information.
        Looks for a log file, and updates display as logfile is updated.
           """,
        formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument("input_file",
                        help="Name of the log file to get data from and monitor.")

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
    show_cycle = not (args.no_cycle_data)

    fridge_data = FridgeData()

    lines = open(input_file, "r").readlines()
    fridge_data.Update(lines)
    print(FrigeOutput(fridge_data,
                      showSummary=show_summary, showCycles=show_cycle,
                      cycles=selected_cycle, fridge_id=selected_fridge_id))

    # now set up handlers
    event_handler = TopFridgeHandler( patterns=[input_file], fridge_data=fridge_data,
                                      showSummary=show_summary, showCycles=show_cycle,
                                      cycles=selected_cycle, fridge_id=selected_fridge_id)
    observer = Observer()
    observer.schedule(event_handler, path=input_dir, recursive=False)
    observer.start()

    #Now wait for changes
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()