import contextlib
import importlib
import io
import tempfile
import unittest
from collections import namedtuple
from pathlib import Path
from unittest.mock import patch

from lazynlp import crawl


class DownloadFiltersTest(unittest.TestCase):
    def setUp(self):
        # Each test starts with a fresh module, including function defaults.
        importlib.reload(crawl)
        self.resources = contextlib.ExitStack()
        self.addCleanup(self.resources.close)
        self.root = Path(self.resources.enter_context(tempfile.TemporaryDirectory()))
        self.calls = 0
        (self.root / 'exclude_extensions.txt').write_text('.pdf\n')
        (self.root / 'exclude_domains.txt').write_text('blocked\n')
        self.resources.enter_context(patch.object(crawl, 'dir_path', str(self.root)))
        self.download = self.resources.enter_context(
            patch.object(crawl, 'download_page', return_value=(0, b'synthetic page'))
        )
        self.resources.enter_context(
            patch.object(crawl, 'clean_page', return_value='Synthetic text')
        )
        # Isolate domain parsing as well: no public suffix downloads or network calls.
        domains = {
            'https://example.test/keep.html': ('', 'example', 'test'),
            'https://example.test/report.pdf': ('', 'example', 'test'),
            'https://blocked.test/keep.html': ('', 'blocked', 'test'),
            'https://custom.test/keep.html': ('', 'custom', 'test'),
            'https://example.test/file.custom': ('', 'example', 'test'),
        }
        extracted = namedtuple('Extracted', 'subdomain domain suffix')
        self.resources.enter_context(
            patch.object(crawl.tldextract, 'extract',
                         side_effect=lambda url: extracted(*domains[url]))
        )
        self.resources.enter_context(
            patch.object(crawl.urllib.request, 'urlopen', side_effect=AssertionError('Unexpected network call'))
        )

    def run_download(self, urls, **kwargs):
        self.calls += 1
        links = self.root / ('links-{}.txt'.format(self.calls))
        links.write_text('\n'.join(urls) + '\n')
        folder = self.root / ('output-{}'.format(self.calls))
        self.download.reset_mock()
        # Close all crawl file handles so checks are deterministic on Windows too.
        with contextlib.ExitStack() as files, contextlib.redirect_stdout(io.StringIO()):
            def open_file(*args, **options):
                return files.enter_context(open(*args, **options))

            with patch.object(crawl, 'open', side_effect=open_file, create=True):
                crawl.download_pages(str(links), str(folder), **kwargs)
        return [call.args[0] for call in self.download.call_args_list]

    def test_default_filters_do_not_leak_into_a_later_call(self):
        urls = ['https://example.test/report.pdf', 'https://blocked.test/keep.html']
        self.assertEqual(self.run_download(urls), [])
        self.assertEqual(self.run_download(urls, default_skip=False), urls)

    def test_caller_owned_filters_are_not_modified(self):
        extensions = ['.custom']
        domains = ['custom']
        self.run_download(['https://example.test/keep.html'],
                          extensions=extensions, domains=domains)
        self.assertEqual(extensions, ['.custom'])
        self.assertEqual(domains, ['custom'])

    def test_none_filters_work_with_and_without_defaults(self):
        url = 'https://example.test/report.pdf'
        self.assertEqual(self.run_download([url], extensions=None, domains=None), [])
        self.assertEqual(self.run_download([url], default_skip=False,
                                          extensions=None, domains=None), [url])

    def test_custom_filters_work_without_defaults(self):
        urls = ['https://example.test/keep.html', 'https://example.test/report.pdf',
                'https://blocked.test/keep.html', 'https://custom.test/keep.html',
                'https://example.test/file.custom']
        self.assertEqual(self.run_download(urls, default_skip=False,
                                          extensions=['.custom'], domains=['custom']), urls[:3])

    def test_custom_filters_are_combined_with_defaults(self):
        urls = ['https://example.test/keep.html', 'https://example.test/report.pdf',
                'https://blocked.test/keep.html', 'https://custom.test/keep.html',
                'https://example.test/file.custom']
        self.assertEqual(self.run_download(urls, extensions=['.custom'], domains=['custom']), urls[:1])


if __name__ == '__main__':
    unittest.main()
