#!/usr/bin/env python3
"""
Unit tests for MSG to EML Converter
"""

import unittest
import os
import tempfile
from email import message_from_file
from msg_to_eml_converter import MSGToEMLConverter


class TestMSGToEMLConverter(unittest.TestCase):
    """Test cases for MSGToEMLConverter"""

    def setUp(self):
        """Set up test fixtures"""
        self.converter = MSGToEMLConverter()
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test files"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_converter_initialization(self):
        """Test that converter initializes correctly"""
        self.assertIsInstance(self.converter, MSGToEMLConverter)
        self.assertFalse(self.converter.verbose)

    def test_invalid_file_path(self):
        """Test that FileNotFoundError is raised for non-existent files"""
        with self.assertRaises(FileNotFoundError):
            self.converter.convert_file('nonexistent.msg')

    def test_invalid_extension(self):
        """Test that ValueError is raised for non-MSG files"""
        temp_file = os.path.join(self.temp_dir, 'test.txt')
        with open(temp_file, 'w') as f:
            f.write('test')

        with self.assertRaises(ValueError):
            self.converter.convert_file(temp_file)

    def test_convert_directory_not_found(self):
        """Test that FileNotFoundError is raised for non-existent directory"""
        with self.assertRaises(FileNotFoundError):
            self.converter.convert_directory('/nonexistent/directory')

    def test_convert_directory_not_a_directory(self):
        """Test that ValueError is raised when path is not a directory"""
        temp_file = os.path.join(self.temp_dir, 'test.txt')
        with open(temp_file, 'w') as f:
            f.write('test')

        with self.assertRaises(ValueError):
            self.converter.convert_directory(temp_file)

    def test_headers_setting(self):
        """Test that email headers are set correctly"""
        from email.mime.text import MIMEText
        from datetime import datetime

        msg_data = {
            'subject': 'Test Subject',
            'sender': 'sender@example.com',
            'to': 'recipient@example.com',
            'cc': 'cc@example.com',
            'bcc': 'bcc@example.com',
            'date': datetime.now(),
            'body': 'Test body',
            'htmlBody': '',
            'attachments': []
        }

        eml_msg = MIMEText('test')
        self.converter._set_headers(eml_msg, msg_data)

        self.assertEqual(eml_msg['Subject'], 'Test Subject')
        self.assertEqual(eml_msg['From'], 'sender@example.com')
        self.assertEqual(eml_msg['To'], 'recipient@example.com')
        self.assertEqual(eml_msg['Cc'], 'cc@example.com')
        self.assertEqual(eml_msg['Bcc'], 'bcc@example.com')
        self.assertIsNotNone(eml_msg['Date'])
        self.assertIsNotNone(eml_msg['Message-ID'])


class TestEMLFileFormat(unittest.TestCase):
    """Test that generated EML files are valid"""

    def setUp(self):
        """Set up test fixtures"""
        self.converter = MSGToEMLConverter()
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test files"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_eml_file_creation(self):
        """Test that EML file is created with valid structure"""
        from email.mime.text import MIMEText
        from email import generator

        # Create a simple message
        msg = MIMEText('Test body', 'plain', 'utf-8')
        msg['Subject'] = 'Test Subject'
        msg['From'] = 'sender@example.com'
        msg['To'] = 'recipient@example.com'

        eml_path = os.path.join(self.temp_dir, 'test.eml')
        self.converter._write_eml_file(msg, eml_path)

        # Verify file exists
        self.assertTrue(os.path.exists(eml_path))

        # Verify file can be read as valid email
        with open(eml_path, 'r') as f:
            parsed_msg = message_from_file(f)
            self.assertEqual(parsed_msg['Subject'], 'Test Subject')
            self.assertEqual(parsed_msg['From'], 'sender@example.com')
            self.assertEqual(parsed_msg['To'], 'recipient@example.com')


def run_tests():
    """Run all tests"""
    unittest.main(verbosity=2)


if __name__ == '__main__':
    run_tests()
