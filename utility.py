import re
from collections import defaultdict
from urllib.parse import urlparse, parse_qs, urljoin, urlencode

from splinter.exceptions import ElementDoesNotExist


def extract_dict_from_html(browser, html, pattern, group_id=1):
    js_snippet = re.search(pattern, html).group(group_id)
    return browser.evaluate_script(js_snippet)


def get_login_cookies(browser, userid, password):
    browser.visit('http://4m3.tongji.edu.cn/eams/login.action')

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


def enumerate_entrance(browser, echo=True):
    entrance_navigation_link = 'http://4m3.tongji.edu.cn/eams/doorOfStdElectCourse.action'
    browser.visit(entrance_navigation_link)

    # enumerate entrance for course selection
    i = 0
    entrances = {}
    while True:
        try:
            entrance = browser.find_by_id('electIndexNotice' + str(i)).first
            link = entrance.find_by_text('进入选课>>>>')
            entrances[i] = urljoin(entrance_navigation_link, link['href'])
            if echo:
                title = entrance.find_by_tag('h2').first
                print('{}: {}'.format(i, title.text))
            i += 1
        except ElementDoesNotExist:
            break

    return entrances


def get_course_information(browser, entrance_link):
    entrance_profile_id = parse_qs(urlparse(entrance_link).query)['electionProfile.id'][0]
    entrance_data_link = 'http://4m3.tongji.edu.cn/eams/tJStdElectCourse!data.action?'
    entrance_data_link += urlencode({'profileId': entrance_profile_id})

    browser.visit(entrance_link)  # it is supposed to visit the entrance page in prior requesting data (weird, uh?!)
    browser.visit(entrance_data_link)
    all_courses = browser.html
    all_courses = extract_dict_from_html(browser, all_courses, r'var lessonJSONs = (\[.*\]);', 1)
    all_courses_indexed_by_no = {i['no']: i for i in all_courses}
    all_courses_indexed_by_code = defaultdict(list)
    for i in all_courses:
        all_courses_indexed_by_code[i['code']].append(i)

    plan_course_link = 'http://4m3.tongji.edu.cn/eams/tJStdElectCourse!planCourses.action'
    browser.visit(plan_course_link)
    planned_courses = browser.html
    planned_courses = extract_dict_from_html(browser, planned_courses, r'window.planCourses = (\[.*\]);', 1)

    return planned_courses, all_courses_indexed_by_no, all_courses_indexed_by_code
