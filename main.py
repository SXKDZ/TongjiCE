"""
TongjiCE - Automatically course selection for Tongji University

By SXKDZ with support of lisirrx
https://sxkdz.org

Disclaimer: use with your own discretion!
"""
import os
import sys
import json
import random
import asyncio
import aiohttp
import getpass
import argparse
import calendar
from itertools import groupby
from splinter import Browser

from utility import *


USER_AGENT = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) '
              'AppleWebKit/537.36 (KHTML, like Gecko) '
              'Chrome/63.0.3239.84 Safari/537.36')


def convert_weekstate_to_string(weekstate):
    start = weekstate.find('1')
    end = weekstate.rfind('1')

    if '01' in weekstate[start:end] or '10' in weekstate[start:end]:
        prefix = 'Odd' if start % 2 and end % 2 else 'Even'
        return '{} Week #{}-#{}'.format(prefix, start, end)

    return 'Week #{}-#{}'.format(start, end)


def start_selection(config, cookies, section_urls, all_courses_indexed_by_no):
    interval = config['interval']
    maximum_attempts = config['maximum_attempts']

    futures = [attempt(url, section, cookies, interval, maximum_attempts) for section, url in section_urls.items()]
    loop = asyncio.get_event_loop()
    finished, _ = loop.run_until_complete(asyncio.wait(futures))

    print('Results:')
    for section in finished:
        print('{} {}: {}'.format(section.result()[0],
                                 all_courses_indexed_by_no[section.result()[0]]['name'],
                                 'Succeed' if section.result()[1] else 'Failed'))


async def attempt(url, section, cookies, interval, maximum_attempts):
    async with aiohttp.ClientSession(cookies=cookies) as session:
        if interval == 'random':
            interval = -1
        else:
            interval = float(interval)
        if maximum_attempts == 'infinity':
            maximum_attempts = -1
        else:
            maximum_attempts = int(maximum_attempts)
        attempt_count = 0
        while True:
            print('Starting attempt #{} by accessing {}'.format(attempt_count, url))
            async with session.get(url, headers={'User-Agent': USER_AGENT}) as response:
                data = await response.text()
                if '选课成功' in data:
                    print('Course {} is selected successfully!'.format(section))
                    return section, True
                elif '冲突' in data:
                    print('Conflict courses are selected!')
                    return section, False
                elif '登录失败' in data:
                    print('Unknown error occurred! Perhaps you have already selected this course.')
                    return section, False
                elif '人数已满' in data:
                    print('Failed to select course {} due to limitation on capacity. Retrying...'
                          .format(section))
                else:
                    print('Unknown error orrurred!')
                    print(data)
                    return section, False

                if interval == -1:
                    await asyncio.sleep(random.random())
                else:
                    await asyncio.sleep(interval)
                attempt_count += 1

                if maximum_attempts != -1 and attempt_count > maximum_attempts:
                    print('Maximum attempts reached.')
                    return section, False


def get_arguments():
    parser = argparse.ArgumentParser(usage='%(prog)s [options]')
    parser.add_argument('-C', '--conf',
                        nargs='?', type=argparse.FileType('r'), default=sys.stdin,
                        help='load the configuration from the specified file')
    return vars(parser.parse_args())


def main():
    # http://cx-freeze.readthedocs.org/en/latest/faq.html
    if getattr(sys, 'frozen', False):
        # frozen
        base_path = os.path.dirname(sys.executable)
    else:
        # unfrozen
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    phantomjs_path = os.path.join(base_path, 'phantomjs')
    browser = Browser('phantomjs', **{'executable_path': phantomjs_path})

    arguments = get_arguments()

    if arguments['conf'] == sys.stdin:
        userid = input('Enter student matriculation ID: ')
        password = getpass.getpass('Enter password: ')
        cookies = get_login_cookies(browser, userid, password)

        print('Available entrances for course selection:')
        entrances = enumerate_entrance(browser)
        if len(entrances) == 0:
            print('No available entrances at present. Please come back later...')
            sys.exit(0)

        entrance_id = input('Enter the entrance ID: ')
        entrance_link = entrances[int(entrance_id)]

        planned_courses, all_courses_indexed_by_no, all_courses_indexed_by_code = \
            get_course_information(browser, entrance_link)

        print('Available planned courses:')
        for school_year, group in groupby(planned_courses, lambda x: x['coruseSchoolYear']):  # should be a typo anyway
            print(school_year)
            for course in group:
                print('{}: {} ({}, {} {})'.format(
                    course['code'], course['name'], course['courseTypeName'],
                    course['credits'], 'credits' if course['credits'] > 1 else 'credit'))

        courses_to_be_selected = input('Enter course IDs that you want to automatically selected, split with space: ')

        for course in courses_to_be_selected.split():
            print('Available section(s) for {}:'.format(course))
            for section in sorted(all_courses_indexed_by_code[course], key=lambda x: x['no']):
                print('{}: {} ({}by {})'.format(section['no'],
                                                section['name'],
                                                section['remark'] + ', ' if section['remark'] is None else '',
                                                section['teachers']))
                for arrangement in section['arrangeInfo']:
                    print('{} #{}-#{} ({})'.format(
                        calendar.day_name[arrangement['weekDay'] - 1],
                        arrangement['startUnit'],
                        arrangement['endUnit'],
                        convert_weekstate_to_string(arrangement['weekState'])))

        sections_to_be_selected = input('Enter sections IDs that you want to automatically selected, split with space: ')
        sections = {}
        for section in sections_to_be_selected.split():
            sections[section] = all_courses_indexed_by_no[section]['id']
        base_section_select_url = 'http://4m3.tongji.edu.cn/eams/tJStdElectCourse!batchOperator.action?'
        section_urls = {section: base_section_select_url + urlencode({'electLessonIds': id})
                        for section, id in sections.items()}

        config = {
            'interval': input('Enter the interval (seconds) between attempts: '),
            'maximum_attempts': input('Enter the maximum number of attempts: ')
        }

    else:
        config = json.load(arguments['conf'])
        userid = config['student_ID']
        password = config['password']
        cookies = get_login_cookies(browser, userid, password)
        entrances = enumerate_entrance(browser, echo=False)
        entrance_link = entrances[int(config['entrance_ID'])]

        planned_courses, all_courses_indexed_by_no, all_courses_indexed_by_code = \
            get_course_information(browser, entrance_link)

        sections = {}
        for section in config['courses']:
            sections[section] = all_courses_indexed_by_no[section]['id']
        base_section_select_url = 'http://4m3.tongji.edu.cn/eams/tJStdElectCourse!batchOperator.action?'
        section_urls = {section: base_section_select_url + urlencode({'electLessonIds': id})
                        for section, id in sections.items()}

    browser.quit()

    start_selection(config, cookies, section_urls, all_courses_indexed_by_no)


if __name__ == '__main__':
    main()
