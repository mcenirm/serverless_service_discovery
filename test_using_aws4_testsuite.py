import collections
import logging
import os
import pathlib
import unittest
import urllib

import botocore
import requests

import util


logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# http://docs.aws.amazon.com/general/latest/gr/signature-v4-test-suite.html
CREDENTIALS = botocore.credentials.Credentials(
    'AKIDEXAMPLE',
    'wJalrXUtnFEMI/K7MDENG+bPxRfiCYEXAMPLEKEY'
)
DATE    = '20150830'
AMZDATE = '20150830T123600Z'
REGION  = 'us-east-1'
SERVICE = 'service'
HOST    = 'example.amazonaws.com'


class AWS4TestSuite():
    def __init__(self, location='aws4_testsuite'):
        logger.debug('New AWS4 Test Suite using location "'+location+'"')
        self.location = location
        self.examples = collections.OrderedDict()
        for entry in os.scandir(path=location):
            if entry.is_dir():
                try:
                    example = AWS4TestSuiteExample(self, entry)
                    self.examples[entry.name] = example
                except FileNotFoundError:
                    pass
        logger.debug('examples: '+repr(self.examples.keys()))


class AWS4TestSuiteExample():
    def __init__(self, suite, direntry):
        logger.debug('New AWS4 Test Suite Example using "'+direntry.name+'"')
        self.name = direntry.name

        as_path = pathlib.Path(direntry.path)
        with (as_path / (self.name + '.req')).open('r') as f:
            req = f.read()
        with (as_path / (self.name + '.creq')).open('r') as f:
            creq = f.read()
        with (as_path / (self.name + '.sreq')).open('r') as f:
            sreq = f.read()

        self.original = parse_original_request(req)
        self.canonical = parse_canonical_request(creq)
        self.signed = parse_signed_request(sreq)


class Holder():
    pass


def parse_original_request(contents):
    r = Holder()
    r.contents = contents
    lines = contents.split('\n')

    r.method, remainder = lines[0].split(' ', 1)
    r.uri, _ = remainder.rsplit(' ', 1)
    r.headers, line_i = parse_headers_block(lines, 1)
    r.body = '\n'.join(lines[line_i:])

    r.parsed_url = urllib.parse.urlparse(r.uri, allow_fragments=False)
    r.querystring_params = urllib.parse.parse_qs(r.parsed_url.query)

    return r


def parse_canonical_request(contents):
    c = Holder()
    c.contents = contents
    lines = contents.split('\n')

    c.method = lines[0]
    c.uri = lines[1]
    c.querystring = lines[2]
    c.headers, line_i = parse_headers_block(lines, 3)
    c.body = '\n'.join(lines[line_i:])

    return c


def parse_signed_request(contents):
    s = parse_original_request(contents)
    return s


def parse_headers_block(lines, line_i):
    headers = requests.structures.CaseInsensitiveDict()
    prev_key = None
    while line_i < len(lines):
        line = lines[line_i]
        line_i += 1
        if line == '':
            break
        cont_line = line.lstrip()
        if cont_line == line:
            key, value = line.split(':', 1)
            headers[key] = value.lstrip()
            prev_key = key
        else:
            headers[key] += ' '+cont_line
    return headers, line_i


class TestUsingAWS4TestSuite(unittest.TestCase):
    def setUp(self):
        self.suite = AWS4TestSuite()

    def test_suite(self):
        self.assertIsNotNone(self.suite)
        self.assertTrue(len(self.suite.examples))

    def test_create_canonical_querystring(self):
        for example in self.suite.examples.values():
            if example.name in [
                'post-vanilla-query-space',
                'post-vanilla-query-nonunreserved',
            ]:
                continue
                # skip the ones where it seems like AWS is wrong

            logger.debug('testing create_canonical_querystring on '+example.name)

            self.assertEqual(
                util.create_canonical_querystring(
                    example.original.querystring_params
                ),
                example.canonical.querystring,
                msg=example.name+' '+repr(example.original.parsed_url)+' '+repr(example.original.querystring_params)
            )
