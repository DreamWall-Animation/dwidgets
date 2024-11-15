import os, sys
from datetime import date, timedelta
from PySide2 import QtWidgets, QtCore, QtGui

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))


from dwidgets import (
    AzimuthWidget, CalendarDialog, CornerEditor, DatePickerButton,
    DropFilesArea, MonthSelector, PopupCheckListButton2, RetakeCanvas,
    RangeSlider, TagView, TiltedDates, VerticalTabWidget, WeekSelector,
    WeightSlider)


class Window(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setWindowTitle('Dwidgets Show Case')

        tabwidget = VerticalTabWidget()

        tabwidget.add_section('Misc')
        tabwidget.add_tab(AzimuthAreaShowCase(), 'AzimuthWidget')
        tabwidget.add_tab(DropFilesAreaShowCase(), 'DropFilesArea')
        tabwidget.add_tab(PopupCheckListButton2ShowCase(), 'PopupCheckListButton2')
        tabwidget.add_tab(RetakeCanvasShowCase(), 'RetakeCanvas')
        tabwidget.add_tab(TagViewShowCase(), 'TagView')
        tabwidget.add_tab(CornerEditor(), 'CornerEditor')

        tabwidget.add_separator()
        tabwidget.add_section('Dates')
        tabwidget.add_tab(DatesWidgetsShowCase(), 'Date selectors')
        tabwidget.add_tab(TiltedDatesShowCase(), 'TiltedDates')

        tabwidget.add_separator()
        tabwidget.add_section('Sliders')
        tabwidget.add_tab(RangeSliderShowCase(), 'RangeSlider')
        tabwidget.add_tab(WeightSliderShowcase(), 'WeighSlider')

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(tabwidget)

    def sizeHint(self):
        return QtCore.QSize(800, 600)


class RetakeCanvasShowCase(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        image = QtGui.QImage(f'{os.path.dirname(__file__)}/landscape.webp')
        image1 = QtGui.QImage(f'{os.path.dirname(__file__)}/landscape1.png')
        image2 = QtGui.QImage(f'{os.path.dirname(__file__)}/landscape2.png')
        image3 = QtGui.QImage(f'{os.path.dirname(__file__)}/landscape3.png')
        # self.model = RetakeCanvasModel(image)
        # self.canvas = RetakeCanvas(self.model)
        self.canvas = RetakeCanvas()
        self.canvas.add_layer_image('andré', image1)
        self.canvas.add_layer_image('andré1', image2)
        self.canvas.add_layer_image('andré2', image3)
        self.canvas.disable_retake_mode(keep_layer_view=True)
        self.canvas.tools_bar.setStyleSheet('background: #666666')
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.canvas)


class DatesWidgetsShowCase(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.calendar_dialog = QtWidgets.QPushButton('CalendarDialog')
        self.calendar_dialog.released.connect(lambda: CalendarDialog().exec_())
        self.date_picker = DatePickerButton('select date')
        self.month_selector = MonthSelector()
        self.week_selector = WeekSelector()
        range_layout = QtWidgets.QFormLayout(self)
        range_layout.addWidget(self.calendar_dialog)
        range_layout.addRow('DatePickerButton', self.date_picker)
        range_layout.addRow('MonthSelector', self.month_selector)
        range_layout.addRow('WeekSelector', self.week_selector)


class RangeSliderShowCase(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        self.range_slider = RangeSlider()
        self.range_slider.set_full_range(50, 300)
        self.range_slider.set_range(75, 200)
        self.range_slider.range_changed.connect(self.range_changed)
        self.range_values = QtWidgets.QLineEdit()
        self.range_values.setReadOnly(True)
        self.range_values.setText(
            f'{self.range_slider.get_low()}-{self.range_slider.get_high()}')
        range_layout = QtWidgets.QVBoxLayout(self)
        range_layout.addWidget(self.range_slider)
        range_layout.addWidget(self.range_values)
        range_layout.addStretch()

    def range_changed(self, *_):
        self.range_values.setText(
            f'{self.range_slider.get_low()}-{self.range_slider.get_high()}')


class TagViewShowCase(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        self.tag_field = QtWidgets.QLineEdit()
        self.tag_field.setPlaceholderText('Add tags: "tag1 tag2 ..."')
        self.tag_field.returnPressed.connect(self.add_tags)
        self.tag_view = TagView()
        self.tag_view.setMaximumHeight(300)
        self.tag_view.tags = 'salut', '123', 'rose'

        tag_layout = QtWidgets.QVBoxLayout(self)
        tag_layout.addWidget(self.tag_field)
        tag_layout.addWidget(self.tag_view)
        tag_layout.addStretch()

    def sizeHint(self):
        return QtCore.QSize(250, 300)

    def add_tags(self):
        tags = [
            t for tag in self.tag_field.text().split(' ')
            for t in tag.split(',') if t]
        self.tag_view.extend(tags)
        self.tag_field.clear()


class PopupCheckListButton2ShowCase(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        self.popup1 = PopupCheckListButton2(
            'included title',
            items=[(letter, letter) for letter in 'abcdefgh'])
        self.popup2 = PopupCheckListButton2(
            'static title',
            items=[(letter, letter) for letter in 'abcdefgh'],
            default=True)
        self.popup3 = PopupCheckListButton2(
            'limited choice',
            items=[(letter, letter) for letter in 'abcdefgh'])
        self.popup3.checked_items_changed.connect(self.checker_changed)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel('Example 1'))
        layout.addWidget(self.popup1)
        txt = 'Example 2: static title, default value'
        layout.addWidget(QtWidgets.QLabel(txt))
        layout.addWidget(self.popup2)
        txt = 'Example 3: Limited selection and print on checked values'
        layout.addWidget(QtWidgets.QLabel(txt))
        layout.addWidget(self.popup3)
        layout.addStretch()

    def checker_changed(self):
        print(self.popup3.checked_data())


class AzimuthAreaShowCase(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        self.azimuth = AzimuthWidget(height=80)
        self.azimuth.angle_changed.connect(self.angle_changed)
        self.azimuth_value = QtWidgets.QLineEdit()
        self.azimuth_value.setReadOnly(True)
        self.azimuth_value.setText(str(self.azimuth.angle))

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.azimuth)
        layout.addWidget(self.azimuth_value)
        layout.addStretch()

    def angle_changed(self):
        self.azimuth_value.setText(str(self.azimuth.angle))


class DropFilesAreaShowCase(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        self.dropfiles = DropFilesArea()
        self.dropfiles.files_changed.connect(self.files_changed)
        self.dropfiles_paths = QtWidgets.QListWidget()
        self.dropfiles_paths.setFixedHeight(60)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.dropfiles)
        layout.addWidget(self.dropfiles_paths)
        layout.addStretch()

    def files_changed(self):
        self.dropfiles_paths.clear()
        for file in self.dropfiles.filepaths:
            self.dropfiles_paths.addItem(file)


dates = list(reversed([
    d for d in [date.today() - timedelta(days=n) for n in range(10)]
    if d.weekday() < 5]))


class TiltedDatesShowCase(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setMinimumSize(600, 400)
        font = QtGui.QFont()
        font.setPixelSize(15)
        font.setBold(True)
        self.dates = TiltedDates(dates)
        self.dates.display_format = '%d/%m/%Y'
        self.dates.font = font
        self.dates.angle = -45
        self.dates.setFixedHeight(300)
        self.dates.sizeHint = lambda: QtCore.QSize(500, 300)
        self.dates.spacing = 35
        self.index = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.index.setMinimum(0)
        self.index.setMaximum(6)
        self.index.setValue(3)
        self.index.valueChanged.connect(self.index_changed)
        self.dates.current_color = QtGui.QColor('red')
        self.dates.todays_color = QtGui.QColor('yellow')
        self.dates.current_date = dates[2]
        self.spacing = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.spacing.setMinimum(0)
        self.spacing.setMaximum(100)
        self.spacing.setValue(35)
        self.spacing.valueChanged.connect(self.spacing_changed)
        self.angle = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.angle.setMinimum(0)
        self.angle.setMaximum(90)
        self.angle.setValue(45)
        self.angle.valueChanged.connect(self.angle_changed)
        self.format = QtWidgets.QLineEdit('%d/%m/%Y')
        self.format.textEdited.connect(self.format_changed)

        self.layout = QtWidgets.QFormLayout(self)
        self.layout.addWidget(self.dates)
        self.layout.addRow('Date index', self.index)
        self.layout.addRow('Spacing', self.spacing)
        self.layout.addRow('Angle', self.angle)
        self.layout.addRow('Date format', self.format)

    def index_changed(self, index):
        self.dates.current_date = dates[index]

    def spacing_changed(self, spacing):
        self.dates.spacing = spacing
        self.dates.repaint()

    def angle_changed(self, angle):
        self.dates.angle = -angle
        self.dates.repaint()

    def format_changed(self, text):
        self.dates.display_format = text
        self.dates.repaint()


WEIGHTS = [
    [0.2, 0.3, 0.5],
    [0.1, 0.6, 0.1, 0.2],
    [.1, .1, .1, .2, .1, .1, .2, .1],
    [0.2, 0.3, 0.5],
]
COLORS = [
    ['#00FF00', 'blue', 'red'],
    ['orange', 'lightorange', 'darkorange', 'red'],
    ['#666666', '#12be56', 'black', 'yellow', 'pink', 'blue', 'purple', 'red'],
    ['#333333', '#555555', '#888888'],
]
TEXTS = [
    ['Pizza', 'Durum', 'Pasta'],
    ['Gym', 'Foot', 'Tennis', 'Badminton'],
    ['Maud', 'Johnny', 'Fred', 'Virginie', 'Esteban', 'Catherine', 'Yo', 'Su'],
    ['Fork', 'Spoon', 'Moon']
]


class WeightSliderShowcase(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        horizontals = [
            WeightSlider(
                weights=w, colors=c, texts=t,
                graduation=10)
            for (w, c, t) in zip(WEIGHTS, COLORS, TEXTS)]
        for slider in horizontals:
            slider.setFixedHeight(30)

        verticals1 = [
            WeightSlider(
                weights=w, colors=c, texts=t,
                orientation=QtCore.Qt.Vertical,
                graduation=10)
            for (w, c, t) in zip(WEIGHTS, COLORS, TEXTS)]
        for slider in verticals1:
            slider.setFixedWidth(30)

        verticals2 = [
            WeightSlider(
                weights=w, colors=c, texts=t,
                orientation=QtCore.Qt.Vertical,
                graduation=10)
            for (w, c, t) in zip(WEIGHTS, COLORS, TEXTS)]
        for slider in verticals2:
            slider.display_texts = True
            slider.setFixedWidth(120)

        self.vlayout = QtWidgets.QVBoxLayout()
        for slider in horizontals:
            self.vlayout.addWidget(slider)

        self.hlayout = QtWidgets.QHBoxLayout()
        for slider in verticals1 + verticals2:
            self.hlayout.addWidget(slider)

        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.addLayout(self.vlayout)
        self.layout.addLayout(self.hlayout)


app = QtWidgets.QApplication(sys.argv)
win = Window()
win.show()
win.setFixedSize(1280, 700)
win.setMinimumHeight(300)
win.setMinimumWidth(300)
app.exec_()
