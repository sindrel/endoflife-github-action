# pylint: disable=C0301,C0114,C0115,C0116,W0621

import unittest
from unittest.mock import patch, mock_open, MagicMock
from datetime import datetime
import json
from get_cycle import write_to_output_file, _check_eol_date, _parse_semantic_version, _get_product_details, _get_version_from_structured_file, _extract_value_from_string, _construct_summary

class TestGetCycle(unittest.TestCase):

    def test_get_version_from_json_file(self):
        args = MagicMock()
        args.file_path = 'dummy_path'
        args.file_format = 'json'
        args.file_key = 'version'
        version = _get_version_from_structured_file(args, '{"version": "1.2.3"}')
        self.assertEqual(version, '1.2.3')

    def test_get_version_from_yaml_file(self):
        args = MagicMock()
        args.file_path = 'dummy_path'
        args.file_format = 'yaml'
        args.file_key = 'version'
        version = _get_version_from_structured_file(args, 'version: 1.2.3')
        self.assertEqual(version, '1.2.3')

    def test_parse_semantic_version(self):
        version = 'v1.2.3'
        major, minor, patch = _parse_semantic_version(version)
        self.assertEqual(major, '1')
        self.assertEqual(minor, '2')
        self.assertEqual(patch, '3')

    def test_check_eol_date(self):
        eol_date = '2022-01-01'
        with patch('get_cycle.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2022, 1, 2)
            mock_datetime.strptime.return_value = datetime(2022, 1, 1)
            end_of_life, days_until_eol = _check_eol_date(eol_date)
            self.assertTrue(end_of_life)
            self.assertEqual(days_until_eol, -1)

    @patch('http.client.HTTPSConnection')
    def test_get_product_details(self, mock_https):
        mock_conn = mock_https.return_value
        mock_conn.getresponse.return_value.status = 200
        mock_conn.getresponse.return_value.read.return_value = json.dumps([{"cycle": "1.2.3", "eol": "2022-01-01"}]).encode('utf-8')
        product_details = _get_product_details('dummy_product')
        self.assertEqual(product_details, [{"cycle": "1.2.3", "eol": "2022-01-01"}])

    def test_extract_value_from_string(self):
        regex = r'v([0-9]+\.[0-9]+\.[0-9]+)'
        string = 'version: v1.2.3'
        value = _extract_value_from_string(regex, string)
        self.assertEqual(value, 'v1.2.3')

    def test_construct_summary(self):
        result = {
            'product': 'dummy_product',
            'version': '1.2.3',
            'end_of_life': True,
            'days_until_eol': -1
        }
        summary = _construct_summary(result)
        self.assertEqual(summary, 'dummy_product 1.2.3 is end-of-life.')

    @patch('builtins.open', new_callable=mock_open)
    def test_write_to_output_file(self, mock_file):
        result = {
            'version': '1.2.3',
            'end_of_life': True,
            'days_until_eol': -1,
            'text_summary': 'dummy_product 1.2.3 is end-of-life.'
        }
        write_to_output_file(result, 'dummy_output_file')
        mock_file().write.assert_called_once_with(
            "\nversion=1.2.3\nend_of_life=true\ndays_until_eol=-1\ntext_summary=dummy_product 1.2.3 is end-of-life.\n"
        )

if __name__ == '__main__':
    unittest.main()
