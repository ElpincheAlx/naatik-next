"""Injected Spectacle command/file boundary; no real mouse release or monitor test."""
import base64
from pathlib import Path
import unittest
from unittest.mock import patch
from PIL import Image
from naatik_next.ocr import capture, spectacle_capability
from naatik_next.storage import Cancelled, UserError


class CaptureReleaseTests(unittest.TestCase):
    def invoke(self, mode='valid', supported=True):
        spectacle_capability.cache_clear()
        self.commands = []
        def run(args, timeout, env=None):
            self.commands.append(args)
            if '--version' in args:
                return 'spectacle 6.7.5\n'
            if '--help' in args:
                return '--region --background --output --new-instance' + (' --release-capture' if supported else '')
            output = Path(args[args.index('--output') + 1])
            if mode == 'valid':
                Image.new('RGB', (73, 41), 'white').save(output)
            elif mode == 'empty':
                output.touch()
            return ''
        with patch('naatik_next.platform_support.kde_x11', return_value=True), \
                patch('naatik_next.ocr.shutil.which', return_value=str(Path(__file__))), \
                patch('naatik_next.ocr.run', side_effect=run):
            return capture()

    def test_release_flag_and_image_dimensions_preserved(self):
        import io
        result = self.invoke()
        args = self.commands[-1]
        for option in ('--new-instance', '--region', '--release-capture', '--background', '--nonotify', '--output'):
            self.assertIn(option, args)
        self.assertNotIn('--copy-image', args)
        self.assertNotIn('--copy-path', args)
        with Image.open(io.BytesIO(base64.b64decode(result))) as image:
            self.assertEqual(image.size, (73, 41))

    def test_missing_and_empty_region_do_not_return_image(self):
        for mode in ('cancel', 'empty'):
            with self.subTest(mode=mode), self.assertRaises(Cancelled):
                self.invoke(mode)

    def test_missing_release_option_rejected_before_capture(self):
        with self.assertRaises(UserError):
            self.invoke(supported=False)
        self.assertEqual(len(self.commands), 2)
