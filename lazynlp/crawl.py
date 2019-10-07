import glob
import hashlib
import html
import http
import os
import re
import socket
import ssl
import time
import urllib.request

import requests
import tldextract

from .cleaner import *
from .utils import *

dir_path = os.path.dirname(os.path.realpath(__file__))


def exists(url):
    request = requests.get(url)
    return request.status_code == 200


def get_gutenberg_link_from_id(book_id):
    txt_tmpl1 = 'http://www.gutenberg.org/cache/epub/{}/pg{}.txt'
    txt_tmpl2 = 'http://www.gutenberg.org/files/{}/{}.txt'

    for tmpl in [txt_tmpl1, txt_tmpl2]:
        link = tmpl.format(book_id, book_id)
        if exists(link):
            return link

    txt_tmpl3 = 'http://www.gutenberg.org/files/{}/{}-{}.txt'
    # idx = [0, 8] + list(range(1, 8)) + list(range(9, 15))
    for i in [0, 8]:
        link = txt_tmpl3.format(book_id, book_id, i)
        if exists(link):
            return link
    return None


def get_us_gutenberg_links(outfile, max_id=58910):
    out = open(outfile, 'w')
    for book_id in range(1, max_id + 1):
        link = get_gutenberg_link_from_id(book_id)
        if link:
            out.write(link + '\n')
        else:
            print("Can't find link for book id", book_id)
    out.close()


def get_id_aus(link):
    id_ = link[link.rfind('/') + 1:link.rfind('.')]
    if id_[-1] == 'h':
        return id_[:-1]
    return id_


def get_aus_gutenberg_links(
        outfile,
        catalog_file='https://www.gutenberg.org/dirs/GUTINDEX.AUS'):
    req = urllib.request.Request(catalog_file)
    response = urllib.request.urlopen(req)
    page = response.read()
    page = page.decode('utf-8')
    html_links = re.findall(
        r'http://gutenberg.net.au/ebooks[01][0-9]/[0-9]{7}[h]?.html', page)
    txt_links = re.findall(
        r'http://gutenberg.net.au/ebooks[01][0-9]/[0-9]{7}.txt', page)
    seen_ids = set()
    with open(outfile, 'w') as out:
        for link in txt_links:
            out.write(link + '\n')
            seen_ids.add(get_id_aus(link))

        for link in html_links:
            book_id = get_id_aus(link)
            if book_id not in seen_ids:
                out.write(link + '\n')
                seen_ids.add(book_id)


def to_skip(link, extensions=None, domains=None):
    """ domains can be:
            - just the name (as in: google)
            - main domain (as in: google.com)
            - subdomain (as in: news.google.com)
    """
    for ext in extensions:
        if link.endswith(ext):
            return True
    raw_url = get_raw_url(link)
    subdomain, domain, suffix = tldextract.extract(link)
    if domain in domains:
        return True
    if '.'.join([domain, suffix]) in domains:
        return True
    if '.'.join([subdomain, domain, suffix]) in domains:
        return True
    return False


def download_page(link, context=None, timeout=None):
    """
    Return code, page
    0: successfully read (write to index)
    1: bad_url (write to bad_url)
    2: unicode error (write to non_ascii_urls)
    3. bad_connection_urls

    When code is not 0, return ''
    """
    try:
        req = urllib.request.Request(link)
    except ValueError as e:
        print(link, "doesn't exist.")
        return 1, ''
    except ConnectionResetError as e:
        print('ConnectionResetError', link)
        return 3, ''

    try:
        if timeout is not None:
            response = urllib.request.urlopen(
                req, context=context, timeout=timeout)
        else:
            response = urllib.request.urlopen(req, context=context)
    except UnicodeError as e:
        print('UnicodeError for', link)
        return 2, ''
    except (urllib.error.HTTPError) as e:
        print('Error {} for {}'.format(e.code, link))
        return 1, ''
    except urllib.error.URLError as e:
        print('URLError for', link)
        return 1, ''
    except http.client.HTTPException as e:
        print('HTTPException', link)
        return 1, ''
    except http.client.RemoteDisconnected as e:
        print('RemoteDisconnected', link)
        return 1, ''
    except (ConnectionError, socket.timeout) as e:
        print('ConnectionError or Timeout', link)
        return 3, ''

    try:
        page = response.read()
    except http.client.HTTPException as e:
        print('HTTPException', link)
        return 1, ''
    except (ConnectionError, socket.timeout) as e:
        print('ConnectionError or Timeout', link)
        return 3, ''
    return 0, page


def get_current_idx(index_file, links):
    lines = open(index_file, 'r').readlines()
    idx = len(lines)
    if idx > 0:
        last_seen = lines[-1].strip()
        while True:
            link = links.readline().strip()
            if link == last_seen:
                break
    return idx, links


def download_pages(link_file,
                   folder,
                   timeout=30,
                   default_skip=True,
                   extensions=[],
                   domains=[]):
    """
    link_file (str):
        file contains links to pages to crawl. Each line contains one URL.
    folder (str):
        folder that you want to contain your downloaded pages.
    timeout:
        seconds to wait for a page to respond before abandoning it.

    default_skip (bool):
        True if you want to automatically skip all URLs that contain
        domains and extensions known to be scraper-unfriendly or NSFW.
        See the list of excluded domains at lazynlp/exclude_domains.txt.

        domains can be:
            - just the name (as in: google)
            - main domain (as in: google.com)
            - subdomain (as in: news.google.com)

        See the list of excluded extensions at
        lazynlp/exclude_extensions.txt

        You can also add your own domains and extensions to skip with domains
        and extensions and arguments.

    In the folder:
            Each URL is downloaded into a file, indexed by the order in which
            it is downloaded.
            The first line of each file is the URL.
            The rest is the textual content of the page.

            index.urls contains all the URLs that have been successfully downloaded.
            bad.urls contains the URLs that are bad.
            connection.urls contains the URLs that haven't been downloaded because
                            of connection issues.
            non_ascii.urls contains the URLs that haven't been downloaded because
                            of bad encoding issues.
            empty.urls contains the URLs that have empty textual content.
    """
    index_file = os.path.join(folder, 'index.urls')
    idx = 0
    links = open(link_file, 'r')

    if os.path.isdir(folder) and os.path.exists(index_file):
        """ If index file exists, we've downloaded from this list of
        URLs before, continue from where it left off the last time.
        """
        idx, links = get_current_idx(index_file, links)
        print(idx)
    else:
        os.makedirs(folder, exist_ok=True)

    index = open(os.path.join(folder, 'index.urls'), 'a')
    skipped_urls = open(os.path.join(folder, 'skip.urls'), 'a')
    bad_connection_urls = open(os.path.join(folder, 'connection.urls'), 'a')
    bad_urls = open(os.path.join(folder, 'bad.urls'), 'a')
    non_ascii_urls = open(os.path.join(folder, 'non_ascii.urls'), 'a')
    empty_urls = open(os.path.join(folder, 'empty.urls'), 'a')

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    hashed = hashlib.sha1()

    if default_skip:
        ext_lines = open(f'{dir_path}/exclude_extensions.txt', 'r').readlines()
        extensions.extend([line.strip() for line in ext_lines])
        domain_lines = open(f'{dir_path}/exclude_domains.txt', 'r').readlines()
        domains.extend([line.strip() for line in domain_lines])

    for link in links:
        link = link.strip()
        if to_skip(link, extensions, domains):
            skipped_urls.write(link + '\n')
            print('Skip', link)
            continue

        code, page = download_page(link, ctx, timeout)
        if code == 1:
            bad_urls.write(link + '\n')
        elif code == 2:
            non_ascii_urls.write(link + '\n')
        elif code == 3:
            bad_connection_urls.write(link + '\n')
        if code > 0:
            continue

        txt = clean_page(page)

        if not txt:
            print('Empty page', link)
            empty_urls.write(link + '\n')
            continue

        print(idx, link)
        hashed.update(str(time.time()).encode())
        name = hashed.hexdigest()
        with open(f'{folder}/{idx}_{name}.txt', 'w') as out:
            out.write(link + '\n' + txt)

        print(find_unprintable(txt))
        index.write('{}\n'.format(link))
        idx += 1

    links.close()
