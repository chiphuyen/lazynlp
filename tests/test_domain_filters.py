import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import tldextract

from lazynlp import crawl


class DomainFiltersTest(unittest.TestCase):
    def setUp(self):
        self.resources = contextlib.ExitStack()
        self.addCleanup(self.resources.close)
        # Use real extraction results, but only the bundled public suffix list.
        extract = tldextract.TLDExtract(cache_dir=None, suffix_list_urls=())
        self.resources.enter_context(
            patch.object(crawl.tldextract, 'extract', side_effect=extract)
        )
        self.resources.enter_context(
            patch.object(crawl.socket, 'create_connection',
                         side_effect=AssertionError('Unexpected network connection'))
        )
        self.resources.enter_context(
            patch.object(crawl.requests.sessions.Session, 'request',
                         side_effect=AssertionError('Unexpected HTTP request'))
        )

    def test_matches_bare_domain(self):
        self.assertTrue(crawl.to_skip('https://news.example.com/article', [], ['example']))

    def test_matches_registered_domain(self):
        for url, domain in [('https://news.example.com/article', 'example.com'),
                            ('https://news.example.co.uk/article', 'example.co.uk')]:
            with self.subTest(domain=domain):
                self.assertTrue(crawl.to_skip(url, [], [domain]))

    def test_matches_full_subdomain(self):
        self.assertTrue(crawl.to_skip('https://news.example.com/article', [], ['news.example.com']))

    def test_does_not_match_other_domains(self):
        for domain in ['other.com', 'example.org', 'other.example.com']:
            with self.subTest(domain=domain):
                self.assertFalse(crawl.to_skip('https://news.example.com/article', [], [domain]))

    def test_empty_filters_allow_the_url(self):
        self.assertFalse(crawl.to_skip('https://example.com/article', [], []))

    def test_extension_match_does_not_require_domain_extraction(self):
        with patch.object(crawl.tldextract, 'extract',
                          side_effect=AssertionError('Domain extraction should not be needed')):
            self.assertTrue(crawl.to_skip('https://example.com/report.pdf', ['.pdf'], []))

    def test_download_pages_applies_real_domain_extraction(self):
        urls = ['https://example.com/article', 'https://news.blocked.com/article',
                'https://example.com/report.pdf']
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            links = root / 'links.txt'
            links.write_text('\n'.join(urls) + '\n')
            folder = root / 'pages'
            # Keep downloads synthetic while exercising the real filtering path.
            with contextlib.ExitStack() as files, contextlib.redirect_stdout(io.StringIO()):
                def open_file(*args, **kwargs):
                    return files.enter_context(open(*args, **kwargs))

                with patch.object(crawl, 'open', side_effect=open_file, create=True), \
                        patch.object(crawl, 'download_page', return_value=(0, b'page')) as download, \
                        patch.object(crawl, 'clean_page', return_value='Synthetic text'):
                    crawl.download_pages(str(links), str(folder), default_skip=False,
                                         extensions=['.pdf'], domains=['blocked.com'])
                    self.assertEqual([call.args[0] for call in download.call_args_list], urls[:1])
            self.assertEqual((folder / 'index.urls').read_text().splitlines(), urls[:1])
            self.assertEqual((folder / 'skip.urls').read_text().splitlines(), urls[1:])


if __name__ == '__main__':
    unittest.main()
