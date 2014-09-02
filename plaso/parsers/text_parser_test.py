#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright 2012 The Plaso Project Authors.
# Please see the AUTHORS file for details on individual authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""This file contains the tests for the generic text parser."""

import unittest

import pyparsing

from plaso.events import text_events
from plaso.formatters import interface as formatters_interface
from plaso.formatters import manager as formatters_manager
from plaso.lib import errors
from plaso.lib import lexer
from plaso.lib import timelib_test
from plaso.parsers import interface
from plaso.parsers import test_lib
from plaso.parsers import text_parser


class TestTextEvent(text_events.TextEvent):
  """Test text event."""
  DATA_TYPE = 'test:parser:text'


class TestTextEventFormatter(formatters_interface.EventFormatter):
  """Test text event formatter."""
  DATA_TYPE = 'test:parser:text'
  FORMAT_STRING = u'{body}'

  SOURCE_LONG = 'Test Text Parser'


class TestTextParser(text_parser.SlowLexicalTextParser):
  """Implement a text parser object that can successfully parse a text file.

  To be able to achieve that one function has to be implemented, the ParseDate
  one.
  """
  NAME = 'test_text'

  tokens = [
      lexer.Token('INITIAL',
                  r'^([\d\/]+) ', 'SetDate', 'TIME'),
      lexer.Token('TIME', r'([0-9:\.]+) ', 'SetTime', 'STRING_HOST'),
      lexer.Token('STRING_HOST', r'([^\-]+)- ', 'ParseStringHost', 'STRING'),
      lexer.Token('STRING', '([^\n]+)', 'ParseString', ''),
      lexer.Token('STRING', '\n', 'ParseMessage', 'INITIAL')]

  def ParseStringHost(self, match, **_):
    user, host = match.group(1).split(':')
    self.attributes['hostname'] = host
    self.attributes['username'] = user

  def SetDate(self, match, **_):
    month, day, year = match.group(1).split('/')
    self.attributes['imonth'] = int(month)
    self.attributes['iyear'] = int(year)
    self.attributes['iday'] = int(day)

  def Scan(self, unused_file_entry):
    pass

  def CreateEvent(self, timestamp, offset, attributes):
    event_object = TestTextEvent(timestamp, 0, attributes)
    event_object.offset = offset
    return event_object


class BaseParserTest(test_lib.ParserTestCase):
  """An unit test for the plaso parser library."""

  def testParserNotImplemented(self):
    """Test the base class Parse function."""
    self.assertRaises(TypeError, interface.BaseParser)


class TextParserTest(test_lib.ParserTestCase):
  """An unit test for the plaso parser library."""

  def setUp(self):
    """Sets up the needed objects used throughout the test."""
    self._parser = TestTextParser()

  def testTextParserFail(self):
    """Test a text parser that will not match against content."""
    test_file = self._GetTestFilePath(['text_parser', 'test1.txt'])

    with self.assertRaises(errors.UnableToParseFile):
      _ = self._ParseFile(self._parser, test_file)

  def testTextParserSuccess(self):
    """Test a text parser that will match against content."""
    test_file = self._GetTestFilePath(['text_parser', 'test2.txt'])
    event_queue_consumer = self._ParseFile(self._parser, test_file)
    event_objects = self._GetEventObjectsFromQueue(event_queue_consumer)

    event_object = event_objects[0]

    msg1, _ = formatters_manager.EventFormatterManager.GetMessageStrings(
        event_object)

    expected_timestamp = timelib_test.CopyStringToTimestamp(
        '2011-01-01 05:23:15')
    self.assertEquals(event_object.timestamp, expected_timestamp)

    self.assertEquals(msg1, 'first line.')
    self.assertEquals(event_object.hostname, 'myhost')
    self.assertEquals(event_object.username, 'myuser')

    event_object = event_objects[1]

    msg2, _ = formatters_manager.EventFormatterManager.GetMessageStrings(
        event_object)

    expected_timestamp = timelib_test.CopyStringToTimestamp(
        '1991-12-24 19:58:06')
    self.assertEquals(event_object.timestamp, expected_timestamp)

    self.assertEquals(msg2, 'second line.')
    self.assertEquals(event_object.hostname, 'myhost')
    self.assertEquals(event_object.username, 'myuser')


class PyParserTest(test_lib.ParserTestCase):
  """Few unit tests for the pyparsing unit."""

  def _CheckIPv4(self, ip_address):
    # TODO: Add a similar IPv6 check.
    try:
      text_parser.PyparsingConstants.IPV4_ADDRESS.parseString(ip_address)
      return True
    except pyparsing.ParseException:
      return False

  def testPyConstantIPv4(self):
    """Run few tests to make sure the constants are working."""
    self.assertTrue(self._CheckIPv4('123.51.234.52'))
    self.assertTrue(self._CheckIPv4('255.254.23.1'))
    self.assertTrue(self._CheckIPv4('1.1.34.2'))
    self.assertFalse(self._CheckIPv4('1.1.34.258'))
    self.assertFalse(self._CheckIPv4('a.1.34.258'))
    self.assertFalse(self._CheckIPv4('.34.258'))
    self.assertFalse(self._CheckIPv4('34.258'))
    self.assertFalse(self._CheckIPv4('10.52.34.258'))

  def testPyConstantOctet(self):
    with self.assertRaises(pyparsing.ParseException):
      text_parser.PyparsingConstants.IPV4_OCTET.parseString('526')

    with self.assertRaises(pyparsing.ParseException):
      text_parser.PyparsingConstants.IPV4_OCTET.parseString('1026')

    with self.assertRaises(pyparsing.ParseException):
      text_parser.PyparsingConstants.IPV4_OCTET.parseString(
          'a9', parseAll=True)

  def testPyConstantOthers(self):
    with self.assertRaises(pyparsing.ParseException):
      text_parser.PyparsingConstants.MONTH.parseString('MMo')
    with self.assertRaises(pyparsing.ParseException):
      text_parser.PyparsingConstants.MONTH.parseString('M')
    with self.assertRaises(pyparsing.ParseException):
      text_parser.PyparsingConstants.MONTH.parseString('March', parseAll=True)

    self.assertTrue(text_parser.PyparsingConstants.MONTH.parseString('Jan'))

    line = '# This is a comment.'
    parsed_line = text_parser.PyparsingConstants.COMMENT_LINE_HASH.parseString(
        line)
    self.assertEquals(parsed_line[-1], 'This is a comment.')
    self.assertEquals(len(parsed_line), 2)


if __name__ == '__main__':
  unittest.main()
