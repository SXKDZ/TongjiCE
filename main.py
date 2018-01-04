"""
TongjiCE 1.1
Automatically course selection for Tongji University

by SXKDZ with support of lisirrx

Disclaimer: use with your own discretion
"""
import re
import sys
import json
import random
import asyncio
import aiohttp
import getpass
import logging
import _jsonnet
import calendar
from itertools import groupby
from collections import defaultdict
from urllib.parse import urljoin, urlparse, parse_qs, urlencode
from splinter import Browser
from splinter.exceptions import ElementDoesNotExist

USER_AGENT = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) '
              'AppleWebKit/537.36 (KHTML, like Gecko) '
              'Chrome/63.0.3239.84 Safari/537.36')


def get_login_cookies(browser, userid, password):
    browser.visit('http://4m3.tongji.edu.cn')

    login_link = browser.find_by_text('统一身份认证登录')
    login_link.click()

    browser.fill('Ecom_User_ID', userid)
    browser.fill('Ecom_Password', password)
    login_button = browser.find_by_name('submit')
    login_button.click()

    if browser.is_text_present('Login failed, please try again.'):
        raise Exception('Login failed!')

    assert 'JSESSIONID' in browser.cookies.all()

    return browser.cookies.all()


def extract_dict_from_html(html, pattern, group_id=1):
    js = re.search(pattern, html).group(group_id)
    return json.loads(_jsonnet.evaluate_snippet('snippet', js))


def convert_weekstate_to_string(weekstate):
    start = weekstate.find('1')
    end = weekstate.rfind('1')

    if '01' in weekstate[start:end] or '10' in weekstate[start:end]:
        prefix = 'Odd' if start % 2 and end % 2 else 'Even'
        return '{} Week #{}-#{}'.format(prefix, start, end)

    return 'Week #{}-#{}'.format(start, end)


async def attempt(url, section, cookies, interval, maximum_attempts):
    async with aiohttp.ClientSession(cookies=cookies) as session:
        if interval == 'random':
            interval = -1
        else:
            interval = int(interval)
        if maximum_attempts == 'infinity':
            maximum_attempts = -1
        attempt_count = 0
        while True:
            logging.error('Starting attempt #{} by accessing {}'.format(attempt_count, url))
            async with session.get(url, headers={'User-Agent': USER_AGENT}) as response:
                data = await response.text()
                if '选课成功' in data:
                    logging.error('Course {} is selected successfully!'.format(section))
                    return section, True
                elif '冲突' in data:
                    logging.error('Conflict courses are selected!')
                    return section, False
                elif '登录失败' in data:
                    logging.error('Unknown error occurred!')
                    return section, False
                else:
                    logging.error('Failed to select course {}. Retrying...'.format(section))
                    if interval == -1:
                        await asyncio.sleep(random.random())
                    else:
                        await asyncio.sleep(interval)
                    attempt_count += 1
                if maximum_attempts != -1 and attempt_count > maximum_attempts:
                    logging.error('Maximum attempts reached.')
                    return section, False


def main():
    browser = Browser('phantomjs')

    userid = input('Enter student matriculation ID: ')
    password = getpass.getpass('Enter password: ')
    cookies = get_login_cookies(browser, userid, password)

    entrance_navigation_link = 'http://4m3.tongji.edu.cn/eams/doorOfStdElectCourse.action'
    browser.visit(entrance_navigation_link)

    # enumerate entrance for course selection
    i = 0
    entrances = {}
    print('Available entrance for course selection:')
    while True:
        try:
            entrance = browser.find_by_id('electIndexNotice' + str(i)).first
            title = entrance.find_by_tag('h2').first
            link = entrance.find_by_text('进入选课>>>>')
            entrances[i] = urljoin(entrance_navigation_link, link['href'])
            print('{}: {}'.format(i, title.text))
            i += 1
        except ElementDoesNotExist:
            break

    if len(entrances) == 0:
        print('No available entrances at present. Please come back later...')
        sys.exit(0)

    entrance_id = input('Enter the entrance ID: ')
    entrance_link = entrances[int(entrance_id)]
    entrance_profile_id = parse_qs(urlparse(entrance_link).query)['electionProfile.id'][0]
    entrance_data_link = 'http://4m3.tongji.edu.cn/eams/tJStdElectCourse!data.action?'
    entrance_data_link += urlencode({'profileId': entrance_profile_id})

    browser.visit(entrance_link)  # it is supposed to visit the entrance page in prior requesting data (weird, uh?!)
    browser.visit(entrance_data_link)
    all_courses = browser.html
    all_courses = extract_dict_from_html(all_courses, r'var lessonJSONs = (\[.*\]);', 1)
    all_courses_indexed_by_no = {i['no']: i for i in all_courses}
    all_courses_indexed_by_code = defaultdict(list)
    for i in all_courses:
        all_courses_indexed_by_code[i['code']].append(i)

    plan_course_link = 'http://4m3.tongji.edu.cn/eams/tJStdElectCourse!planCourses.action'
    browser.visit(plan_course_link)
    planned_courses = browser.html
    planned_courses = extract_dict_from_html(planned_courses, r'window.planCourses = (\[.*\]);', 1)

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
                    calendar.day_name[arrangement['weekDay']],
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

    interval = input('Enter the interval (ms) between attempts: ')
    maximum_attempts = input('Enter the maximum number of attempts: ')

    futures = [attempt(url, section, cookies, interval, maximum_attempts) for section, url in section_urls.items()]
    loop = asyncio.get_event_loop()
    finished, _ = loop.run_until_complete(asyncio.wait(futures))

    print('Results:')
    for section in finished:
        print('{} {}: {}'.format(section.result()[0],
                                 all_courses_indexed_by_no[section.result()[0]]['name'],
                                 'Succeed' if section.result()[1] else 'Failed'))

    browser.quit()


if __name__ == '__main__':
    main()
