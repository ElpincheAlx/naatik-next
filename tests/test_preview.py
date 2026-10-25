"""Offscreen painting regressions; these do not exercise desktop capture."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import unittest
from PySide6.QtCore import QSize
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QApplication
from naatik_next.preview import ImagePreview

APP = QApplication.instance() or QApplication([])


class PreviewTests(unittest.TestCase):
    def test_tiny_capture_is_not_enlarged_or_cropped(self):
        image = QImage(43, 45, QImage.Format_RGB32)
        image.fill(QColor('white'))
        image.setPixelColor(0, 0, QColor('red'))
        image.setPixelColor(42, 44, QColor('blue'))
        preview = ImagePreview()
        preview.resize(850, 140)
        preview.set_image(image)
        preview.show()
        APP.processEvents()
        target = preview.image_rect()
        self.assertEqual(target.size(), QSize(43, 45))
        result = preview.grab().toImage()
        self.assertEqual(result.pixelColor(target.topLeft()), QColor('red'))
        self.assertEqual(result.pixelColor(target.bottomRight()), QColor('blue'))
        preview.close()

    def test_whole_image_remains_visible_after_resize(self):
        image = QImage(400, 800, QImage.Format_RGB32)
        image.fill(QColor('white'))
        painter = QPainter(image)
        painter.fillRect(0, 0, 400, 80, QColor('red'))
        painter.fillRect(0, 720, 400, 80, QColor('blue'))
        painter.end()
        preview = ImagePreview()
        preview.set_image(image)
        preview.show()
        for width, height in [(850, 140), (120, 180), (960, 250)]:
            preview.resize(width, height)
            APP.processEvents()
            target = preview.image_rect()
            self.assertTrue(preview.contentsRect().contains(target))
            self.assertLessEqual(abs(target.width() / target.height() - .5), .01)
            result = preview.grab().toImage()
            self.assertEqual(result.pixelColor(target.center().x(), target.top() + 2), QColor('red'))
            self.assertEqual(result.pixelColor(target.center().x(), target.bottom() - 2), QColor('blue'))
        preview.close()
