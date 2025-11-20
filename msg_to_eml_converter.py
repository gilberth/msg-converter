#!/usr/bin/env python3
"""
MSG to EML Converter

Converts Microsoft Outlook MSG files to standard EML format.
"""

import os
import sys
from email import generator
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from email.utils import formatdate, make_msgid
from datetime import datetime
import extract_msg


class MSGToEMLConverter:
    """Converts MSG files to EML format"""

    def __init__(self):
        self.verbose = False

    def convert_file(self, msg_path, eml_path=None, verbose=False):
        """
        Convert a single MSG file to EML format.

        Args:
            msg_path (str): Path to the input MSG file
            eml_path (str): Path to the output EML file (optional)
            verbose (bool): Print verbose output

        Returns:
            str: Path to the created EML file
        """
        self.verbose = verbose

        if not os.path.exists(msg_path):
            raise FileNotFoundError(f"MSG file not found: {msg_path}")

        if not msg_path.lower().endswith('.msg'):
            raise ValueError("Input file must have .msg extension")

        # Generate output path if not provided
        if eml_path is None:
            eml_path = msg_path.rsplit('.', 1)[0] + '.eml'

        if self.verbose:
            print(f"Reading MSG file: {msg_path}")

        # Open and parse MSG file
        try:
            msg = extract_msg.Message(msg_path)
            msg_dict = self._extract_msg_data(msg)
        except Exception as e:
            raise RuntimeError(f"Error reading MSG file: {e}")

        if self.verbose:
            print(f"Creating EML file: {eml_path}")

        # Create EML message
        eml_message = self._create_eml_message(msg_dict)

        # Write EML file
        self._write_eml_file(eml_message, eml_path)

        # Clean up
        msg.close()

        if self.verbose:
            print(f"Conversion completed successfully!")

        return eml_path

    def _extract_msg_data(self, msg):
        """Extract data from MSG object"""
        data = {
            'subject': msg.subject or '',
            'sender': msg.sender or '',
            'to': msg.to or '',
            'cc': msg.cc or '',
            'bcc': msg.bcc or '',
            'date': msg.date,
            'body': msg.body or '',
            'htmlBody': msg.htmlBody or '',
            'attachments': []
        }

        # Extract attachments
        for attachment in msg.attachments:
            att_data = {
                'filename': attachment.longFilename or attachment.shortFilename or 'attachment',
                'data': attachment.data
            }
            data['attachments'].append(att_data)

        if self.verbose:
            print(f"  Subject: {data['subject']}")
            print(f"  From: {data['sender']}")
            print(f"  To: {data['to']}")
            print(f"  Attachments: {len(data['attachments'])}")

        return data

    def _create_eml_message(self, msg_data):
        """Create an EML message from extracted MSG data"""
        # Create message container
        if msg_data['htmlBody']:
            eml_msg = MIMEMultipart('alternative')
        elif msg_data['attachments']:
            eml_msg = MIMEMultipart()
        else:
            eml_msg = MIMEText(msg_data['body'], 'plain', 'utf-8')
            self._set_headers(eml_msg, msg_data)
            return eml_msg

        # Set headers
        self._set_headers(eml_msg, msg_data)

        # Add body content
        if msg_data['htmlBody']:
            # Create multipart alternative for plain text and HTML
            text_part = MIMEText(msg_data['body'], 'plain', 'utf-8')
            html_part = MIMEText(msg_data['htmlBody'], 'html', 'utf-8')
            eml_msg.attach(text_part)
            eml_msg.attach(html_part)
        else:
            text_part = MIMEText(msg_data['body'], 'plain', 'utf-8')
            eml_msg.attach(text_part)

        # Add attachments
        for attachment in msg_data['attachments']:
            self._add_attachment(eml_msg, attachment)

        return eml_msg

    def _set_headers(self, eml_msg, msg_data):
        """Set email headers"""
        eml_msg['Subject'] = msg_data['subject']
        eml_msg['From'] = msg_data['sender']
        eml_msg['To'] = msg_data['to']

        if msg_data['cc']:
            eml_msg['Cc'] = msg_data['cc']

        if msg_data['bcc']:
            eml_msg['Bcc'] = msg_data['bcc']

        # Set date
        if msg_data['date']:
            if isinstance(msg_data['date'], datetime):
                eml_msg['Date'] = formatdate(msg_data['date'].timestamp(), localtime=True)
            else:
                eml_msg['Date'] = formatdate(localtime=True)
        else:
            eml_msg['Date'] = formatdate(localtime=True)

        # Set Message-ID
        eml_msg['Message-ID'] = make_msgid()

    def _add_attachment(self, eml_msg, attachment):
        """Add attachment to EML message"""
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment['data'])
        encoders.encode_base64(part)
        part.add_header(
            'Content-Disposition',
            f'attachment; filename="{attachment["filename"]}"'
        )
        eml_msg.attach(part)

    def _write_eml_file(self, eml_message, eml_path):
        """Write EML message to file"""
        with open(eml_path, 'w', encoding='utf-8') as f:
            gen = generator.Generator(f)
            gen.flatten(eml_message)

    def convert_directory(self, input_dir, output_dir=None, verbose=False):
        """
        Convert all MSG files in a directory to EML format.

        Args:
            input_dir (str): Input directory containing MSG files
            output_dir (str): Output directory for EML files (optional)
            verbose (bool): Print verbose output

        Returns:
            list: List of converted file paths
        """
        self.verbose = verbose

        if not os.path.exists(input_dir):
            raise FileNotFoundError(f"Directory not found: {input_dir}")

        if not os.path.isdir(input_dir):
            raise ValueError(f"Path is not a directory: {input_dir}")

        # Create output directory if specified
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        converted_files = []
        msg_files = [f for f in os.listdir(input_dir) if f.lower().endswith('.msg')]

        if not msg_files:
            print(f"No MSG files found in {input_dir}")
            return converted_files

        print(f"Found {len(msg_files)} MSG file(s) to convert")

        for msg_file in msg_files:
            msg_path = os.path.join(input_dir, msg_file)

            if output_dir:
                eml_file = msg_file.rsplit('.', 1)[0] + '.eml'
                eml_path = os.path.join(output_dir, eml_file)
            else:
                eml_path = None

            try:
                result = self.convert_file(msg_path, eml_path, verbose=verbose)
                converted_files.append(result)
                print(f"✓ Converted: {msg_file}")
            except Exception as e:
                print(f"✗ Error converting {msg_file}: {e}")

        return converted_files


def main():
    """Command-line interface"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Convert Microsoft Outlook MSG files to EML format',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert a single file
  python msg_to_eml_converter.py input.msg

  # Convert with custom output name
  python msg_to_eml_converter.py input.msg -o output.eml

  # Convert all MSG files in a directory
  python msg_to_eml_converter.py -d /path/to/msgs

  # Convert directory with output to another directory
  python msg_to_eml_converter.py -d /path/to/msgs -o /path/to/output
        """
    )

    parser.add_argument('input', nargs='?', help='Input MSG file or directory')
    parser.add_argument('-o', '--output', help='Output EML file or directory')
    parser.add_argument('-d', '--directory', action='store_true',
                        help='Process all MSG files in input directory')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Verbose output')

    args = parser.parse_args()

    if not args.input:
        parser.print_help()
        return 1

    converter = MSGToEMLConverter()

    try:
        if args.directory:
            converter.convert_directory(args.input, args.output, args.verbose)
        else:
            converter.convert_file(args.input, args.output, args.verbose)
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
