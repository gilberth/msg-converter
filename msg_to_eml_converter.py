#!/usr/bin/env python3
"""
MSG to EML Converter

Converts Microsoft Outlook MSG files to standard EML format.
"""

import os
import sys
import mimetypes
from email import generator
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
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

    def preview_file(self, msg_path):
        """
        Preview MSG file without converting to EML.
        Returns message data as a dictionary suitable for JSON serialization.

        Args:
            msg_path (str): Path to the input MSG file

        Returns:
            dict: Message data including headers, body, and attachment info
        """
        if not os.path.exists(msg_path):
            raise FileNotFoundError(f"MSG file not found: {msg_path}")

        if not msg_path.lower().endswith('.msg'):
            raise ValueError("Input file must have .msg extension")

        # Open and parse MSG file
        try:
            msg = extract_msg.Message(msg_path)
            preview_data = self._extract_preview_data(msg)
            msg.close()
            return preview_data
        except Exception as e:
            raise RuntimeError(f"Error reading MSG file: {e}")

    def _extract_preview_data(self, msg):
        """Extract preview data from MSG object (without binary data)"""
        import base64

        # Safely extract date
        date_str = ''
        try:
            if msg.date:
                if hasattr(msg.date, 'isoformat'):
                    date_str = msg.date.isoformat()
                else:
                    date_str = str(msg.date)
        except Exception:
            date_str = ''

        # Helper function to safely convert to string
        def safe_str(value):
            if value is None:
                return ''
            if isinstance(value, bytes):
                try:
                    return value.decode('utf-8', errors='ignore')
                except:
                    return value.decode('latin-1', errors='ignore')
            return str(value)

        preview = {
            'subject': safe_str(msg.subject),
            'sender': safe_str(msg.sender),
            'to': safe_str(msg.to),
            'cc': safe_str(msg.cc),
            'bcc': safe_str(msg.bcc),
            'date': date_str,
            'body': safe_str(msg.body),
            'htmlBody': safe_str(msg.htmlBody),
            'attachments': [],
            'inline_attachments': []
        }

        # Extract attachment info (without binary data for regular attachments)
        try:
            for i, attachment in enumerate(msg.attachments):
                try:
                    filename = attachment.longFilename or attachment.shortFilename or f'attachment_{i}'

                    if not attachment.data:
                        continue

                    content_id = getattr(attachment, 'cid', None) or getattr(attachment, 'contentId', None)

                    # Get MIME type
                    mime_type, _ = mimetypes.guess_type(filename)
                    if mime_type is None:
                        mime_type = 'application/octet-stream'

                    att_info = {
                        'filename': filename,
                        'size': len(attachment.data),
                        'type': mime_type
                    }

                    # For inline attachments (images), include base64 data for preview
                    if content_id:
                        att_info['content_id'] = content_id
                        att_info['data'] = base64.b64encode(attachment.data).decode('utf-8')
                        preview['inline_attachments'].append(att_info)
                    else:
                        preview['attachments'].append(att_info)
                except Exception as e:
                    # Skip problematic attachments
                    print(f"Warning: Could not process attachment {i}: {e}")
                    continue
        except Exception as e:
            # If we can't process attachments at all, continue without them
            print(f"Warning: Could not process attachments: {e}")

        return preview

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
            'attachments': [],
            'inline_attachments': []
        }

        # Extract attachments
        for i, attachment in enumerate(msg.attachments):
            filename = attachment.longFilename or attachment.shortFilename or f'attachment_{i}'

            # Check if attachment has data
            if not attachment.data:
                continue

            att_data = {
                'filename': filename,
                'data': attachment.data,
                'content_id': getattr(attachment, 'cid', None) or getattr(attachment, 'contentId', None)
            }

            # Determine if it's an inline attachment (embedded image)
            # Inline attachments typically have a Content-ID
            if att_data['content_id']:
                data['inline_attachments'].append(att_data)
            else:
                data['attachments'].append(att_data)

        if self.verbose:
            print(f"  Subject: {data['subject']}")
            print(f"  From: {data['sender']}")
            print(f"  To: {data['to']}")
            print(f"  Attachments: {len(data['attachments'])}")
            print(f"  Inline Attachments: {len(data['inline_attachments'])}")

        return data

    def _create_eml_message(self, msg_data):
        """Create an EML message from extracted MSG data"""
        has_html = bool(msg_data['htmlBody'])
        has_attachments = bool(msg_data['attachments'])
        has_inline = bool(msg_data['inline_attachments'])

        # Case 1: Simple text only (no HTML, no attachments, no inline)
        if not has_html and not has_attachments and not has_inline:
            eml_msg = MIMEText(msg_data['body'], 'plain', 'utf-8')
            self._set_headers(eml_msg, msg_data)
            return eml_msg

        # Create the main container
        eml_msg = MIMEMultipart('mixed')
        self._set_headers(eml_msg, msg_data)

        # Build the content part (text/html with inline images)
        if has_html and has_inline:
            # Need related for HTML with inline images
            msg_related = MIMEMultipart('related')

            # Add text/html alternative inside related
            msg_alternative = MIMEMultipart('alternative')
            text_part = MIMEText(msg_data['body'], 'plain', 'utf-8')
            html_part = MIMEText(msg_data['htmlBody'], 'html', 'utf-8')
            msg_alternative.attach(text_part)
            msg_alternative.attach(html_part)

            msg_related.attach(msg_alternative)

            # Add inline attachments to related
            for inline_att in msg_data['inline_attachments']:
                self._add_inline_attachment(msg_related, inline_att)

            eml_msg.attach(msg_related)

        elif has_html:
            # HTML without inline images
            msg_alternative = MIMEMultipart('alternative')
            text_part = MIMEText(msg_data['body'], 'plain', 'utf-8')
            html_part = MIMEText(msg_data['htmlBody'], 'html', 'utf-8')
            msg_alternative.attach(text_part)
            msg_alternative.attach(html_part)
            eml_msg.attach(msg_alternative)

        else:
            # Just plain text
            text_part = MIMEText(msg_data['body'], 'plain', 'utf-8')
            eml_msg.attach(text_part)

        # Add regular attachments at the end
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

    def _add_inline_attachment(self, eml_msg, attachment):
        """Add inline attachment (embedded image) to EML message"""
        filename = attachment['filename']
        data = attachment['data']
        content_id = attachment['content_id']

        # Detect MIME type
        mime_type, _ = mimetypes.guess_type(filename)

        if mime_type is None:
            mime_type = 'application/octet-stream'

        # Split into maintype and subtype
        maintype, subtype = mime_type.split('/', 1)

        # Create appropriate MIME object
        if maintype == 'image':
            try:
                part = MIMEImage(data, _subtype=subtype)
            except:
                part = MIMEBase(maintype, subtype)
                part.set_payload(data)
                encoders.encode_base64(part)
        else:
            part = MIMEBase(maintype, subtype)
            part.set_payload(data)
            encoders.encode_base64(part)

        # Add Content-ID header for inline reference
        if content_id:
            # Ensure Content-ID is properly formatted
            if not content_id.startswith('<'):
                content_id = f'<{content_id}>'
            if not content_id.endswith('>'):
                content_id = f'{content_id}>'
            part.add_header('Content-ID', content_id)

        # Add inline disposition
        part.add_header('Content-Disposition', 'inline', filename=filename)

        eml_msg.attach(part)

    def _add_attachment(self, eml_msg, attachment):
        """Add attachment to EML message"""
        filename = attachment['filename']
        data = attachment['data']

        # Detect MIME type
        mime_type, _ = mimetypes.guess_type(filename)

        if mime_type is None:
            mime_type = 'application/octet-stream'

        # Split into maintype and subtype
        maintype, subtype = mime_type.split('/', 1)

        # Create appropriate MIME object
        if maintype == 'image':
            # Use MIMEImage for images
            try:
                part = MIMEImage(data, _subtype=subtype)
            except:
                # Fallback to base64 encoding
                part = MIMEBase(maintype, subtype)
                part.set_payload(data)
                encoders.encode_base64(part)
        elif maintype == 'text':
            # For text files
            part = MIMEBase(maintype, subtype)
            part.set_payload(data)
            encoders.encode_base64(part)
        else:
            # For other types
            part = MIMEBase(maintype, subtype)
            part.set_payload(data)
            encoders.encode_base64(part)

        # Add filename header
        part.add_header(
            'Content-Disposition',
            f'attachment; filename="{filename}"'
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
