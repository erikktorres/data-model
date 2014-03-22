# == BSD2 LICENSE ==
# Copyright (c) 2014, Tidepool Project
# 
# This program is free software; you can redistribute it and/or modify it under
# the terms of the associated License, which is identical to the BSD 2-Clause
# License as published by the Open Source Initiative at opensource.org.
# 
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the License for more details.
# 
# You should have received a copy of the License along with this program; if
# not, you can obtain one from Tidepool Project at tidepool.org.
# == BSD2 LICENSE ==

# for Python 3 compatibility
from __future__ import print_function

import argparse
from datetime import datetime as dt
from datetime import time as t
from datetime import timedelta as td
import json
import random
import sys
from urllib2 import urlopen
import uuid

HOURS = range(0,24)

VERY_LIKELY = [7, 8, 11, 12, 6, 11]

for i in VERY_LIKELY:
    j = 0
    while j < 3:
        HOURS.append(i)
        j += 1

LIKELY = [9, 13, 4, 5, 9, 10]

for i in LIKELY:
    j = 0
    while j < 2:
        HOURS.append(i)
        j += 1

SIXTY = range(0, 60)

MICRO = range(0, 1000000)

class Dexcom:
    """Generate demo Dexcom data."""

    def __init__(self, filename, days):
        """Load the indexed segments to use for generating demo Dexcom data."""

        filename = filename if (filename != None) else 'indexed_segments.json'

        self.segments = json.load(open(filename, 'rU'))

        self.days = days

        self.delta = td(minutes=5)

    def _increment_timestamp(self, t):
        """Increment a timestamp with a timedelta and return the updated value."""

        self.current = t + self.delta
        return self.current

    def _stitch_segments(self):
        """Stitch together segments of Dexcom data."""
        
        initial = random.choice(self.segments[random.choice(self.segments.keys())])

        start = dt.now() + td(hours=random.choice(range(-5,6)))

        self.current = start

        self.readings = [{'deviceTime': self._increment_timestamp(self.current), 'value': reading['blood_glucose']} for reading in initial]

        last_reading = initial[len(initial) - 1]['blood_glucose']

        self.final = start + td(days=self.days)

        elapsed = self.current - start

        while(elapsed.total_seconds() < (86400 * self.days)):
            try:
                next = random.choice(self.segments[str(last_reading + random.choice([-1, 0, 1]))])
                last_reading = next[len(next) - 1]['blood_glucose']
            except KeyError:
                print()
                print('Could not stitch segments!')

                next = None
                try:
                    while next is None:
                        next = self._get_segment(last_reading)
                except RuntimeError:
                    sys.exit('\nRecursion limit exceeded. Please try again.\n')
                last_reading = next[len(next) - 1]['blood_glucose']

            jump = random.randint(0,6)

            i = 0
            while i < jump:
                self.current = self._increment_timestamp(self.current)
                i += 1

            self.readings += [{'deviceTime': self._increment_timestamp(self.current), 'value': reading['blood_glucose']} for reading in next]
            elapsed = self.current - start

    def _get_segment(self, last_reading):
        """Return a randomly shifted segment of Dexcom data."""

        print()
        print('Rescue stitch!')

        random_increment = random.randint(-6, 6)

        try:
            return random.choice(self.segments[str(last_reading + random_increment)])
        except KeyError:
            self._get_segment(last_reading)

    def generate_JSON(self):
        """Generate a list ready to print to JSON of demo Dexcom data."""
        
        self._stitch_segments()

        self.json = [{'id': str(uuid.uuid4()), 'type': 'cbg', 'value': reading['value'], 'deviceTime': reading['deviceTime'].isoformat()[:-7]} for reading in self.readings if reading['deviceTime'] < self.final]

    def generate_txt(self):
        """Generate a tab-delimited text file of demo Dexcom data in Dexcom Studio format."""
        # TODO
        pass

class SMBG:
    """Generate demo self-monitored blood glucose data."""

    def __init__(self, dex, readings_per_day = 7):

        self.dexcom = dex.readings

        self.dates = get_dates(self.dexcom)

        self.readings_per_day = readings_per_day

        self.readings = []

        for date in self.dates:
            self.readings += self._generate_smbg(date)

        self.readings = sorted(self.readings, key=lambda reading: reading['deviceTime'])

        self.json = [{'id': str(uuid.uuid4()), 'type': 'smbg', 'value': r['value'], 'deviceTime': r['deviceTime'].isoformat()[:-7]} for r in self.readings]

    def _generate_smbg(self, d):
        """Generate timestamps and smbg values from a non-uniform pool of potential timestamps."""

        readings = []

        i = 0

        while i < self.readings_per_day:

            hour = random.choice(HOURS)

            timestamp = dt(d.year, d.month, d.day, hour, random.choice(SIXTY), random.choice(SIXTY), random.choice(MICRO))

            near = []

            for reading in self.dexcom:
                t = reading['deviceTime']
                if t.date() == d:
                    if t.hour == hour:
                        near.append(reading)

            jump = random.randint(-26, 26)

            try:
                value = random.choice(near)['value'] + jump
                readings.append({'value': value, 'deviceTime': timestamp})
            # exception occurs when can't find a near enough timestamp because data starts with datetime.now()
            # which could be middle of the afternoon, but this method will always try to generate some morning timestamps
            except IndexError:
                pass

            i += 1

        return readings

class Messages:
    """Generate demo messages with bacon ipsum."""

    def __init__(self, smbg):

        self.dates = get_dates(smbg.readings)

        self.json = []

        self._generate_messages()

    def _generate_message(self, t, message_id, parent_message_id):
        """Generate a single message with bacon ipsum."""

        if parent_message_id != '':
            timestamp = t + td(minutes=random.choice(range(1,61)))
        else:
            timestamp = t

        print()
        print(dt.now(), 'Fetching some bacon ipsum...')
        
        request = urlopen('https://baconipsum.com/api/?type=meat-and-filler&sentences=' + str(random.choice(range(1,4))))

        bacon_ipsum = json.loads(request.read())[0]

        return {'type': 'message', 'id': message_id, 'parentMessage': parent_message_id, 'utcTime': timestamp.isoformat()[:-7] + 'Z', 'messageText': bacon_ipsum}

    def _generate_messages(self):

        likelihood = [0,0,1]

        messages = []

        for d in self.dates:

            hour = random.choice(HOURS)

            timestamp = dt(d.year, d.month, d.day, hour, random.choice(SIXTY), random.choice(SIXTY), random.choice(MICRO))

            message_id = str(uuid.uuid4())

            message = self._generate_message(timestamp, message_id, '')

            self.json.append(message)

            if random.choice(likelihood):
                parent_message_id = message_id

                length_of_thread = random.choice(range(1,6))

                threaded_messages = []

                i = 0

                while i <= length_of_thread:
                    message_id = str(uuid.uuid4())

                    message = self._generate_message(timestamp, message_id, parent_message_id)

                    threaded_messages.append(message)

                    i += 1

                self.json += threaded_messages

class Meals:
    """Generate demo carb intake data."""

    def __init__(self, smbg):

        self.readings = smbg.readings

        # mean of Normal distribution of carb intake datapoints
        self.mu = 50

        # standard deviation of Normal distribution of carb intake datapoints
        self.sigma = 20

        self.carbs = self._generate_meals(self.mu, self.sigma)

        self.json = [{'id': str(uuid.uuid4()), 'type': 'carbs', 'units': 'grams', 'value': c['value'], 'deviceTime': c['deviceTime'].isoformat()[:-7]} for c in self.carbs if c['value'] > 5]

    def _generate_meals(self, mu, sigma):
        """ Generate carb counts for meals based on ."""

        mealtimes = random.sample(self.readings, int(.8 * len(self.readings)))

        carbs = [{'deviceTime': meal['deviceTime'], 'value': int(random.gauss(mu, sigma))} for meal in mealtimes]

        return carbs

class Boluses:
    """Generate demo bolus data."""

    def __init__(self, meals):

        self.meals = meals.carbs

        self.ratio = 15.0

        self.mu = 2.0

        self.sigma = 2.0

        self.boluses = self._generate_meal_boluses()

        self._generate_extended_boluses()

        self._generate_correction_boluses()

        self.json = [b for b in self.boluses if (b['value'] > 0)]

        for bolus in self.json:
            bolus['deviceTime'] = bolus['deviceTime'].isoformat()[:-7]

    def _time_shift(self):

        return td(minutes=random.randint(-5,5))

    def _ratio_shift(self):

        return random.randint(-2, 2)

    def _dose_shift(self):

        return random.choice([-1.5, -1.0, -0.5, 0.5, 1.0, 1.5])

    def _recommendation(self):

        return random.randint(-3,3)

    def _generate_meal_boluses(self):
        """Generate boluses to match generated carb counts."""

        bolus = self

        likelihood = [0,0,0,0,1]

        boluses = [{'id': str(uuid.uuid4()), 'type': 'bolus', 'deviceTime': meal['deviceTime'] + random.choice(likelihood) * bolus._time_shift(), 'value': round(float(meal['value'] / (bolus.ratio + random.choice(likelihood) * bolus._ratio_shift())), 1), 'recommended': round(meal['value'] / bolus.ratio, 1)} for meal in bolus.meals]

        return boluses

    def _generate_correction_boluses(self):
        """Generate some correction boluses."""

        likelihood = [0,0,1]

        self.meals = sorted(self.meals, key=lambda x: x['deviceTime'])

        t = self.meals[0]['deviceTime']

        end = self.meals[len(self.meals) - 1]['deviceTime']

        delta = td(hours=12)

        while t < end:
            next = t + delta + self._time_shift()

            current_value = round(random.gauss(self.mu, self.sigma), 1)

            current_recommendation = round(current_value + random.choice(likelihood) * self._dose_shift(), 1)

            if (current_recommendation > 0) and (current_value > 0):
                self.boluses.append({'id': str(uuid.uuid4()), 'type': 'bolus', 'deviceTime': next, 'value': current_value, 'recommended': current_recommendation})

            t = next

    def _generate_extended_boluses(self):
        """Generate some dual- and square-wave boluses."""

        likelihood = [0,1]

        durations = [30,45,60,90,120,180,240]

        for bolus in self.boluses:
            coin_flip = random.choice(likelihood)

            if coin_flip:
                if bolus['value'] >= 2:
                    dual = random.choice(likelihood)
                    if dual:
                        bolus['initialDelivery'] = round(float(random.choice(range(1,10)))/10 * bolus['value'], 1)
                        bolus['extendedDelivery'] = bolus['value'] - bolus['initialDelivery']
                        # duration in milliseconds for now
                        # TODO: reconsider units?
                        bolus['duration'] = random.choice(durations) * 60 * 1000
                        bolus['type'] = 'bolus'
                        bolus['extended'] = True
                    else:
                        bolus['extendedDelivery'] = bolus['value']
                        # duration in milliseconds for now
                        # TODO: reconsider units?
                        bolus['duration'] = random.choice(durations) * 60 * 1000
                        bolus['type'] = 'bolus'
                        bolus['extended'] = True

class Basal:
    """Generate demo basal data."""

    def __init__(self, schedule, boluses, carbs):

        self.boluses = boluses

        self.carbs = carbs

        self.endpoints = self._get_endpoints()

        if schedule:
            self.schedule = schedule
        else:
            self.schedule = {
                t(0,0,0): 0.8,
                t(2,0,0): 0.65,
                t(4,0,0): 0.75,
                t(5,0,0): 0.85,
                t(6,0,0): 1.00,
                t(9,0,0): 0.8,
                t(15,0,0): 0.9,
                t(20,0,0): 0.8
            }

        self.segment_starts = sorted([time for time in self.schedule.keys()])

        self.segments = []

        self.temp_segments = []

        self.end_initial = self._get_initial_segment()

        self.end_middle = self._get_middle_segments()

        self._get_final_segment()

        self.generate_temp_basals()
        # more hackery because of my bad while loops /o\
        self.temp_segments.pop()

        self.json = [s for s in self.segments] + [s for s in self.temp_segments]

        for segment in self.json:
            segment['start'] = segment['start'].isoformat()
            segment['end'] = segment['end'].isoformat()
            segment['id'] = str(uuid.uuid4())

    def _append_segment(self, d, segment_start, inferred = False):

        try:
            index = self.segment_starts.index(t(d.hour, d.minute, d.second))
        except ValueError:
            index = self.segment_starts.index(segment_start) - 1

        try:
            current_segment = self.segment_starts[index]
        except IndexError:
            current_segment = self.segment_starts[len(self.segment_starts) - 1]

        segment = {                
                    'type': 'basal-rate-segment',
                    'delivered': self.schedule[current_segment],
                    'value': self.schedule[current_segment],
                    'deliveryType': 'scheduled',
                    'inferred': inferred,
                    'start': dt(d.year, d.month, d.day, d.hour, d.minute, d.second),
                    'end': dt(d.year, d.month, d.day, segment_start.hour, segment_start.minute, segment_start.second)
                }

        if segment_start == t(0,0,0):
            segment['end'] = segment['end'] + td(days=1)

        # print('Basal segment start', segment['start'].isoformat())
        # print('Basal segment end', segment['end'].isoformat())
        # print('Basal segment rate', segment['delivered'])
        # print()

        self.segments.append(segment);

    def _append_temp_segment(self, d, duration, value):

        start = dt(d.year, d.month, d.day, d.hour, d.minute, d.second)

        segment = {                
                    'type': 'basal-rate-segment',
                    'delivered': value,
                    'value': value,
                    'deliveryType': 'temp',
                    'inferred': False,
                    'start': start,
                    'end': start + duration
                }

        # print('Basal segment start', segment['start'].isoformat())
        # print('Basal segment end', segment['end'].isoformat())
        # print('Basal segment rate', segment['delivered'])
        # print()

        self.temp_segments.append(segment);

    def _get_difference(self, t1, t2):

        d = dt.now() - td(days=30)

        dt1 = dt(d.year, d.month, d.day, t1.hour, t1.minute, t1.second)

        dt2 = dt(d.year, d.month, d.day, t2.hour, t2.minute, t2.second)

        if t1 == t(0,0,0):
            dt1 = dt1 + td(days=1)

        return dt1 - dt2

    def _get_endpoints(self):

        bolus_times = []

        for b in self.boluses:
            date_string = b['deviceTime']
            bolus_times.append({'deviceTime': dt.strptime(date_string, '%Y-%m-%dT%H:%M:%S')})

        all_pump_data = bolus_times + self.carbs

        all_pump_data = sorted(all_pump_data, key=lambda x: x['deviceTime'])

        return (all_pump_data[0], all_pump_data[len(all_pump_data) - 1])

    def _get_initial_segment(self):

        d = self.endpoints[0]['deviceTime']

        beginning = t(d.hour, d.minute, d.second)

        for i, start in enumerate(self.segment_starts):
            if beginning < start:
                self._append_segment(d, start, True)
                return start
        else:
            self._append_segment(d, t(0,0,0), True)
            return t(0,0,0)

    def _get_middle_segments(self):

        midnight = t(0,0,0)

        index = self.segment_starts.index(self.end_initial)

        segment_start = self.end_initial

        d = self.endpoints[0]['deviceTime']

        end = self.endpoints[1]['deviceTime']

        start_datetime = dt(d.year, d.month, d.day, segment_start.hour, segment_start.minute, segment_start.second)

        if segment_start == midnight:
            start_datetime = start_datetime + td(days=1)

        current_datetime = start_datetime

        while current_datetime < end:
            try:
                next_segment_start = self.segment_starts[index + 1]
                index += 1            
            except IndexError:
                next_segment_start = midnight
                index = 0
            self._append_segment(current_datetime, next_segment_start)
            start_datetime = current_datetime
            difference = self._get_difference(next_segment_start, t(current_datetime.hour, current_datetime.minute, current_datetime.second))
            current_datetime = current_datetime + difference

        return start_datetime

    def _get_final_segment(self):

        # this is hack since I didn't do a great job on the while loop in _get_middle_segments
        self.segments.pop()

        d = self.endpoints[1]['deviceTime']

        self._append_segment(self.end_middle, t(d.hour, d.minute, d.second), True)

    def generate_temp_basals(self):

        day_skip = range(0,1)

        durations = range(30, 510, 30)

        start = self.endpoints[0]['deviceTime']
        end = self.endpoints[1]['deviceTime']

        current_datetime = start

        basal_range = (min(self.schedule.values()) * 100, (max(self.schedule.values()) + max(self.schedule.values()) / 2) * 100)

        basal_possibilities = [x / 100.0 for x in range(0, int(basal_range[1]), 25)]

        while current_datetime < end:
            days_delta = td(days=random.choice(day_skip))
            time_delta = td(hours=random.choice(HOURS), minutes=random.choice(SIXTY))
            current_datetime = current_datetime + days_delta + time_delta
            self._append_temp_segment(current_datetime, td(minutes=random.choice(durations)), random.choice(basal_possibilities))

# TODO User class for generating profile info
# class User:

#     def __init__(self, user):

#         self.name = self._get_name()

#     def _get_name(self):
#         """Get a fake username from randomuser.me."""

#         request = urlopen('http://api.randomuser.me/0.3/')

#         data = json.loads(request.read())

#         deets = data['results'][0]['user']

def get_dates(data):
    """Get the unique dates from an arbitrary set of device data."""

    dates = set([])

    for reading in data:
        dates.add(reading['deviceTime'].date())

    return dates

def print_JSON(all_json, out_file):

    # rename 'id' to '_id'
    for a in all_json:
        a['_id'] = a['id']
        del a['id']

    # add deviceId field to smbg, boluses, carbs, and basal-rate-segments
    pump_fields = ['smbg', 'carbs', 'bolus', 'basal-rate-segment']
    for a in all_json:
        if a['type'] in pump_fields:
            a['deviceId'] = 'Paradigm Revel - 523'

    # temporarily add a device time to messages to enable sorting
    for a in all_json:
        try:
            t = a['utcTime']
            a['deviceTime'] = t
        except KeyError:
            pass

    # temporarily add a device time to basals to enable sorting
    for a in all_json:
        try:
            t = a['start']
            a['deviceTime'] = t
        except KeyError:
            pass

    all_json = sorted(all_json, key=lambda x: x['deviceTime'])

    # remove device time from messages
    for a in all_json:
        try:
            utc = a['utcTime']
            del a['deviceTime']
        except KeyError:
            pass

    # remove device time from basals
    for a in all_json:
        try:
            start = a['start']
            del a['deviceTime']
        except KeyError:
            pass

    # print()
    # print("Preview: first 50 data points...")
    # print()

    # for i in all_json[0:50]:
    #     print(i)

    # print()

    with open(out_file, 'w') as f:
        f.write(json.dumps(all_json, indent=4, separators=(',', ': ')))

def main():

    parser = argparse.ArgumentParser(description='Generate demo diabetes data for Tidepool applications and visualizations.')
    parser.add_argument('-d', '--dexcom', action='store', dest='dexcom_segments', help='name of file containing indexed continuous segments of Dexcom data;\ndefault is indexed_segments.json')
    parser.add_argument('-n', '--num_days', action='store', dest='num_days', default=30, type=int, help='number of days of demo data to generate;\ndefault is 30')
    parser.add_argument('-o', '--output_file', action='store', dest='output_file', default='device-data.json', help='name of output JSON file;\ndefault is device-data.json')
    parser.add_argument('-q', '--quiet_messages', action='store_true', dest='quiet_messages', help='use this flag to turn off messages when bacon ipsum is being slow')
    args = parser.parse_args()

    dex = Dexcom(args.dexcom_segments, args.num_days)
    dex.generate_JSON()

    smbg = SMBG(dex)

    meals = Meals(smbg)

    boluses = Boluses(meals)

    basal = Basal({}, boluses.json, meals.carbs)

    if args.quiet_messages:
        all_json = dex.json + smbg.json + basal.json + meals.json + boluses.json
    else:
        messages = Messages(smbg)
        all_json = dex.json + smbg.json + basal.json + meals.json + boluses.json + messages.json

    print_JSON(all_json, args.output_file)
    print()

if __name__ == '__main__':
    main()