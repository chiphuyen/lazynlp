import re
import requests

regex_url = r"https?:\/\/(www)?[^\/]*"
regex_dis = r"Disallow:\s*([^\n]*)"


def find_match(url):
    """
    Extracts base url from a given url
    returns status 0 for success and -1 for fail
    """
    matches = re.search(regex_url, url)
    if matches:
        base_url = matches.group()
        return 0, base_url
    return -1, ''


def generate_robot_url(url):
    """
    returns the url for robots.txt file
    returns status 0 for success and -1 for fail
    returns the base url as the third parameter
    """
    success, baseurl = find_match(url)
    if success != 0:
        return -1,''
    robots_url = baseurl + '/robots.txt'
    return 0,robots_url,baseurl

def process_robot_string_to_regex(robot):
    """
    converts disallowed url to regex string and returns it
    """
    regex = re.sub(r"\*", "[^/]*", robot, 0, re.IGNORECASE)
    return regex

def read_disallows(url):
    """
    returns baseurl and a list of Pattern objects for disallowed urls
    you can map the urls based on the baseurl and then check every url corresponding to the base url
    with the pattern objects in this list to see if the given url is allowed by robots.txt for crawling
    """
    success, robots_url,baseurl = generate_robot_url(url)
    if success != 0:
        return []
    disallowed = []
    data = requests.get(robots_url).text
    matches = re.finditer(regex_dis, data, re.MULTILINE | re.IGNORECASE)
    for matchNum, match in enumerate(matches, start=1):
        url = match.group(1)
        outp = process_robot_string_to_regex(url)
        disallowed.append(re.compile(outp))
    return baseurl,disallowed