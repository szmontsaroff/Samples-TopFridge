#!/usr/bin/env python3
# Author:  Stephen Montsaroff
# Created: 11/17/2020
"""
Project: Rigetti 
File: FrigeData.py
Description:
"""


from time import sleep
from datetime import datetime, timedelta, time
from collections import defaultdict
import pickle
import os

TIME_FORMAT = '%Y-%m-%d %H:%M:%S'
LOG_FIELDS = ['fridge_id', 'cooldown_number', 'cooldown_start', 'cooldown_end', 'warmup_start', 'warmup_end']
VALID_LINE_LEN = 6

class FridgeData(object):
    """
    Object for reading, updating and calculating data from a cryogenic fridge log steam
    """
    def __init__(self, history_file="FridgeData.pickle"):
        self._history_file = os.path.abspath(history_file)
        self._log_raw_read_data = defaultdict(None)
        self._fridge_and_cycle_data = defaultdict(None)
        self._fridge_summary_data = defaultdict(None)


    def Update(self, lines):
        """
        Take lines read from in CSV format of the form:

        #fridge_id,cooldown_number,cooldown_start,cooldown_end,warmup_start,warmup_end
         0,0,2019-01-05 08:10:00,2019-01-06 14:27:00,2019-01-10 08:15:00,2019-01-11 09:12:00
        And process

        NB we are NOT assuming data is comming in ordered either by Fridge ID or by cooldown cycle, so
        we will process everthing
        """
        # just do things simply with split
        update_timestamp = datetime.now()
        read_time_string = datetime.now().strftime(TIME_FORMAT)
        self._log_raw_read_data[update_timestamp] = []

        for line in lines:
            line = line.strip()
            self._log_raw_read_data[update_timestamp].append(line)

            entry = defaultdict(None)
            if line and not self._is_comment(line) and self._is_valid_data(line):
                data = line.strip().split(',')
                fridge_id = int(data[0])
                cooldown_number = int(data[1])

                if fridge_id not in self._fridge_and_cycle_data:
                    self._fridge_and_cycle_data[fridge_id] = defaultdict(None)

                if cooldown_number not in self._fridge_and_cycle_data[fridge_id]:
                    self._fridge_and_cycle_data[fridge_id][cooldown_number] = defaultdict(None)

                for i in range(2, 6):
                    self._fridge_and_cycle_data[fridge_id][cooldown_number][LOG_FIELDS[i]] = \
                        datetime.strptime(data[i], TIME_FORMAT)

                self._fridge_and_cycle_data[fridge_id][cooldown_number]['update_timestamp'] = update_timestamp
        #To Do: All is done in memory now, could retrieve from cache or db.

        # Deal with 'time between cycles' e.g. cycle N needs its time for warmup_end and the next cooldown_start
        # Brute force
        for fridge_id, cycles in self._fridge_and_cycle_data.items():

            cycle_ids = sorted(cycles.keys())
            for i in range(0, len(cycle_ids)):
                cycle_id = cycle_ids[i]

                cooldown_time = (self._fridge_and_cycle_data[fridge_id][cycle_id]['cooldown_end'] - \
                                self._fridge_and_cycle_data[fridge_id][cycle_id]['cooldown_start']).total_seconds()

                warmup_time = (self._fridge_and_cycle_data[fridge_id][cycle_id]['warmup_end'] - \
                                self._fridge_and_cycle_data[fridge_id][cycle_id]['warmup_start'] ).total_seconds()

                running_time = (self._fridge_and_cycle_data[fridge_id][cycle_id]['warmup_start'] - \
                                self._fridge_and_cycle_data[fridge_id][cycle_id]['cooldown_end'] ).total_seconds()
                # Update global structure organized by fridge/cycle
                self._fridge_and_cycle_data[fridge_id][cycle_id]['fridge_id'] = fridge_id
                self._fridge_and_cycle_data[fridge_id][cycle_id]['cooldown_time'] = cooldown_time
                self._fridge_and_cycle_data[fridge_id][cycle_id]['running_time'] = running_time
                self._fridge_and_cycle_data[fridge_id][cycle_id]['warmup_time'] = warmup_time
                self._fridge_and_cycle_data[fridge_id][cycle_id]['next_cycle_start'] = None
                self._fridge_and_cycle_data[fridge_id][cycle_id]['next_cycle_wait_time'] = None

                if cycle_id  < cycle_ids[-1]:
                    next_cycle_id = cycle_ids[i + 1]
                    self._fridge_and_cycle_data[fridge_id][cycle_id]['next_cycle_start'] = \
                        self._fridge_and_cycle_data[fridge_id][next_cycle_id]['cooldown_start']
                    wait_time = (self._fridge_and_cycle_data[fridge_id][next_cycle_id]['cooldown_start'] - \
                                self._fridge_and_cycle_data[fridge_id][cycle_id]['warmup_end']).total_seconds()
                    self._fridge_and_cycle_data[fridge_id][cycle_id]['next_cycle_wait_time'] = wait_time

            # Now update summary
            summary =self.Calculate_Fridge_Summary_Data(fridge_id)
            summary['update_timestamp'] = update_timestamp
            self._fridge_summary_data[fridge_id] = summary
        #
        # Now Create/update a log
        #
        new_entry = {str(update_timestamp): {'fridge_summary_data': self._fridge_summary_data,
                     'fridge_and_cycle_data': self._fridge_and_cycle_data}}

        try:
            if os.path.isfile(self._history_file):
                with open(self._history_file, 'rb') as pickle_file:
                    history_data = pickle.load(pickle_file)
                history_data.update(new_entry)
            else:
                history_data = new_entry
            with open(self._history_file, 'wb+') as pickle_file:
                pickle.dump(history_data, pickle_file)
        except Exception as e:
            print(f"Failed to update history file {self._history_file}: {str(e)}")


    def List_Fridges(self):
        """
        List fridge recorded for a fridge
        :param fridge_id:
         :return:
        Returns None if there is no data
        """
        if not self._fridge_and_cycle_data:
            return None

        return(self._fridge_and_cycle_data.keys())

    def Get_Number_of_Fridges(self):
        """
        Get Number of fridges in the data
        :return:
               """
        if not self._fridge_and_cycle_data:
            return 0

        return(len(self.List_Fridges()))

    def List_Cycles_of_Fridge(self, fridge_id):
        """
        List Cycles recorded for a fridge
        :param fridge_id:
         :return:
        Returns None if there is no data
        """
        if not self._fridge_and_cycle_data:
            return None

        return(self._fridge_and_cycle_data['fridge_id'].keys())

    def Get_Number_of_Cycles_of_Fridge(self, fridge_id):
        """
        Get number of  Cycles recorded for a fridge
        :param fridge_id:
         :return:
        Returns None if there is no data
        """
        if not self._fridge_and_cycle_data or not self._fridge_and_cycle_data[fridge_id]:
            return 0

        return(len(self._fridge_and_cycle_data['fridge_id'].keys()))

    def Get_Fridge_Cycle_Data(self, fridge_id: int)-> dict:
        """
        Returns of durations for cooling, warming, and waiting for cycles of a fridge
        :param fridge_id:
        :return:
        Returns None if there is no data
        """
        if not self._fridge_and_cycle_data or not self._fridge_and_cycle_data[fridge_id]:
            return None

        ret = defaultdict(None)
        cycle_list = sorted(self._fridge_and_cycle_data[fridge_id].keys())
        for cycle in cycle_list:
            cycle_data = defaultdict(None)
            cycle_data['fridge_id'] =fridge_id
            cycle_data['cycle'] = cycle
            cycle_data['start'] = self._fridge_and_cycle_data[fridge_id][cycle]['cooldown_start']
            cycle_data['end'] = self._fridge_and_cycle_data[fridge_id][cycle]['warmup_end']
            cycle_data['cooldown_time'] = self._fridge_and_cycle_data[fridge_id][cycle]['cooldown_time']
            cycle_data['running_time'] = self._fridge_and_cycle_data[fridge_id][cycle]['running_time']
            cycle_data['warmup_time'] = self._fridge_and_cycle_data[fridge_id][cycle]['warmup_time']
            cycle_data['next_cycle_wait_time'] = self._fridge_and_cycle_data[fridge_id][cycle]['next_cycle_wait_time']
            ret[cycle] = cycle_data
        return ret

    def Calculate_Fridge_Summary_Data(self, fridge_id:int) -> dict:
       """

       :param fridge:

        Take the data from a particular read (specified by update_timestamp)
        reads data, combines with any existing metrics
        and processes and calculates (both globally, and for each fridge)

	- Time spent cooling down a fridge per cycle, for all past cycles.
	- Time spent warming up a fridge per cycle, for all past cycles.
	- Time spent between cycles, for all past cycles - defined as time
	  between warmup_end and the next cooldown_start
	- Summary of percent of time spent cooling down,
	- Percent of time spent warming up
	- Percent of time cold across all past cycles.

        :param current_raw_read:
        :return:
        """
       if not self._fridge_and_cycle_data or not self._fridge_and_cycle_data[fridge_id]:
           return None

       cycle_list = sorted(self._fridge_and_cycle_data[fridge_id].keys())
       totals = {'cooldown_time': 0,
                 'running_time': 0,
                 'warmup_time': 0,
                 'next_cycle_wait_time': 0}

       total_time = (self._fridge_and_cycle_data[fridge_id][cycle_list[-1]]['warmup_end'] - \
                    self._fridge_and_cycle_data[fridge_id][cycle_list[0]]['cooldown_start']).total_seconds()
       for cycle in cycle_list:
           totals['cooldown_time'] += self._fridge_and_cycle_data[fridge_id][cycle]['cooldown_time']
           totals['running_time'] += self._fridge_and_cycle_data[fridge_id][cycle]['running_time']
           totals['warmup_time'] += self._fridge_and_cycle_data[fridge_id][cycle]['warmup_time']
           if cycle == cycle_list[-1]:
               continue
           totals['next_cycle_wait_time'] += self._fridge_and_cycle_data[fridge_id][cycle]['next_cycle_wait_time']

       averages = {'cooldown_time': totals['cooldown_time'] / len(cycle_list),
                   'running_time': totals['running_time'] / len(cycle_list),
                   'warmup_time': totals['warmup_time'] / len(cycle_list),
                   'next_cycle_wait_time': totals['next_cycle_wait_time'] / (len(cycle_list) - 1)
                   }
       percents = {'cooldown_time': totals['cooldown_time'] / total_time,
                   'running_time': totals['running_time'] / total_time,
                   'warmup_time': totals['warmup_time'] / total_time,
                   'next_cycle_wait_time': totals['next_cycle_wait_time'] / total_time
                   }
       return ({'fridge_id': fridge_id,
                'num_of_cycles':len(cycle_list),
                'total_time': total_time,
                'totals': totals,
                'averages': averages,
                'percents': percents})

    def Get_Fridge_Summary_Data(self, fridge_id):
        """
        Returns the Summary data for a given fridge
        :param fridge_id:
        :return:
        Return None if no such fridge and/or data not loading
        """
        if not self._fridge_and_cycle_data or not self._fridge_and_cycle_data[fridge_id]:
            return None

        return self._fridge_summary_data[fridge_id]

    def Get_raw_log_data(self) -> dict:
        """
        Return raw text of log, organized as a dict indexed by date time stampt
        :return:
        """
        return self._log_raw_read_data

    def Get_data_by_fridge_and_cycle(self) -> dict:
        """
        Return data organized by fridge and cycle
        :return:
        """
        return self._fridge_and_cycle_data

    def _is_comment(self,line: str) -> bool:
        """
        Check for comment, which we define as any line starting without digit.
        :param line:
        :return:
        """
        if line[0].isdigit():
            return False
        else:
            return True

    def _is_valid_data(self, line: str) -> bool:
        # To Do Add validation and logging
        # To Do, handle missing time stamps and cases when time before if later than time after.
        
        if len(line.strip().split(',')) != VALID_LINE_LEN:
            # To Do some sort of logging
            return False
        else:
            fridge_id, cooldown_number, cooldown_start, cooldown_end, warmup_start, warmup_end = line.split(',')
            #First check for valid ints in first two fields.
            try:
                int(fridge_id)
                int(cooldown_number)
            except Exception as e:
                # To Do Logging
                return False
            #Next check if remaining field are valid timestamps and the first is earlier than the second.
            try:
                if datetime.strptime(cooldown_end, TIME_FORMAT) < datetime.strptime(cooldown_start, TIME_FORMAT):
                    # To Do Logging
                    return False
                if datetime.strptime(cooldown_end, TIME_FORMAT) < datetime.strptime(cooldown_start, TIME_FORMAT):
                    # To Do Logging
                    return False
            except Exception as e:
                #To Do Logging
                return False

        return True

    def FormatElapsedTime(time:int) -> str:
       """

       :return:
       """
       sec = 50000
       sec_value = sec % (24 * 3600)
       hour_value = sec_value // 3600
       sec_value %= 3600
       min = sec_value // 60
       sec_value %= 60
       print("Converted sec value in hour:", hour_value)
       print("Converted sec value in minutes:", min)

def format_time_period(period_in_seconds:str) ->str:
    """
    Standard Time output format
    :param period_in_seconds:str:
    :return:
    """
    minutes, seconds = divmod(period_in_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours,24)

    return(f"Days {int(days):02d}, {int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}")


def FormatSummaryData(summary: dict) -> str:

    Summary_String= ""

    Summary_String += f"  {'Times':20}  {'Total':^20}  {'Average':^20}  {'Percent':^20}\n"

    Summary_String += f"  {'Cool Down Time:':20} "
    Summary_String += f"  {format_time_period(summary['totals']['cooldown_time']):^20}"
    Summary_String += f"  {format_time_period(summary['averages']['cooldown_time']):^20}"
    Summary_String += f"  {summary['percents']['cooldown_time'] * 100:11.2f}% \n"

    Summary_String += f"  {'Running Time:':20} "
    Summary_String += f"  {format_time_period(summary['totals']['running_time']):^20}"
    Summary_String += f"  {format_time_period(summary['averages']['running_time']):^20}"
    Summary_String += f"  {summary['percents']['running_time'] * 100:11.2f}% \n"

    Summary_String += f"  {'Warm Up Time:':20} "
    Summary_String += f"  {format_time_period(summary['totals']['warmup_time']):^20}"
    Summary_String += f"  {format_time_period(summary['averages']['warmup_time']):^20}"
    Summary_String += f"  {summary['percents']['warmup_time'] * 100:11.2f}% \n"

    Summary_String += f"  {'Wait Time:':20} "
    Summary_String += f"  {format_time_period(summary['totals']['next_cycle_wait_time']):^20}"
    Summary_String += f"  {format_time_period(summary['averages']['next_cycle_wait_time']):^20}"
    Summary_String += f"  {summary['percents']['next_cycle_wait_time'] * 100:11.2f}% \n"

    return Summary_String


def FormatCycleData(cycle_data: dict, **kwargs) -> list:
    formatted_cycle_data = f"  Cycles {'Start':^20}  {'End':^20}  {'Cooldown':^20}   {'Running':^20}  {'Warmup':^20}  {'Wait':^20}\n"
    selected_cycle = -1
    if 'cycle' in kwargs:
        selected_cycle = kwargs['cycle']
    for i in sorted(cycle_data.keys()):
        if selected_cycle >= 0 and i != selected_cycle:
            continue
        cycle_string = ""
        cycle_string += f"  {i:4}  "
        cycle_string += f" {str(cycle_data[i]['cooldown_start']):20}  "
        cycle_string += f" {str(cycle_data[i]['warmup_end']):20}  "
        cycle_string += f" { format_time_period(cycle_data[i]['cooldown_time']):20}  "
        cycle_string += f" {format_time_period(cycle_data[i]['running_time']):20}  "
        cycle_string += f" {format_time_period(cycle_data[i]['warmup_time']):20} "
        if cycle_data[i]['next_cycle_wait_time']:
           cycle_string += f" {format_time_period(cycle_data[i]['next_cycle_wait_time']):20}\n"
        else:
            cycle_string += f"       N/A\n"
        formatted_cycle_data += cycle_string
    return(formatted_cycle_data)

def FrigeOutput(fridge_data:dict, **kwargs) -> str:

    selected_fridge_id = -1
    selected_cycle = -1
    showSummary = True
    showCycles = True

    if 'cycle' in kwargs:
        selected_cycle = kwargs['cycle']
    if 'fridge_id' in kwargs:
        selected_fridge_id = kwargs['fridge_id']
    if 'showCycles' in kwargs:
        showCycles = kwargs['showCycles']
    if 'showSummary' in kwargs:
        showSummary = kwargs['showSummary']

    output = ""
    for fridge_id in fridge_data.List_Fridges():
        if selected_fridge_id >= 0 and fridge_id != selected_fridge_id:
            continue
        summary_data = fridge_data.Get_Fridge_Summary_Data(fridge_id)
        cycle_data = fridge_data.Get_Fridge_Cycle_Data(fridge_id)
        if showSummary:
            output += f"Fridge {fridge_id} Summary:\n"
            output += FormatSummaryData(summary_data)

        if showCycles:
            output += f"Fridge {fridge_id} Cycle Data:\n"
            output += FormatCycleData(cycle_data, cycle=selected_cycle)

        output += f"Fridge {fridge_id}: Cycle Count: {summary_data['num_of_cycles']}  " + \
                  f"Total Time: {format_time_period(summary_data['total_time'])}  " + \
                  f"Updated: {summary_data['update_timestamp']}\n\n"
    return output.strip()

if __name__ == "__main__":
    fridge_data = FridgeData()

    lines = open('input.csv', "r").readlines()
    fridge_data.Update(lines)
    print(FrigeOutput(fridge_data))
    lines = open('input2.csv', "r").readlines()
    fridge_data.Update(lines)
    sleep(2.5)
    os.system("cls") if "nt" in os.name else os.system("clear")
    print(FrigeOutput(fridge_data,showSummary=False))
    lines = open('input1.csv', "r").readlines()
    fridge_data.Update(lines)
    sleep(2.5)
    os.system("cls") if "nt" in os.name else os.system("clear")
    print(FrigeOutput(fridge_data))
    sleep(0.5)
    with open('FridgeData.pickle', 'rb') as pickle_file:
        history_data = pickle.load(pickle_file)
    i = 0
