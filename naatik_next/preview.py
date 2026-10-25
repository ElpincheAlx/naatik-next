"""Paint the whole source image inside the actual preview area."""
from .i18n import t
from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QSizePolicy, QWidget


class ImagePreview(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._image = QImage()
        self.setMinimumHeight(140)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.setAccessibleName(t('Vista previa de la imagen completa'))

    def sizeHint(self):
        # Source dimensions must not impose a minimum width on the window.
        return QSize(480, 200)

    def set_image(self, image):
        self._image = QImage(image)
        self.update()

    def image_rect(self):
        area = self.contentsRect().adjusted(8, 8, -8, -8)
        if self._image.isNull() or area.isEmpty():
            return QRect()
        size = self._image.size()
        # Shrink to fit while preserving aspect ratio; do not enlarge tiny captures.
        if size.width() > area.width() or size.height() > area.height():
            size.scale(area.size(), Qt.KeepAspectRatio)
        target = QRect(0, 0, size.width(), size.height())
        target.moveCenter(area.center())
        return target

    def paintEvent(self, event):
        painter = QPainter(self)
        if self._image.isNull():
            painter.setPen(self.palette().windowText().color())
            painter.drawText(self.contentsRect(), Qt.AlignCenter | Qt.TextWordWrap,
                             t('Selecciona una región o abre una imagen para comenzar.'))
            return
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.drawImage(self.image_rect(), self._image)
