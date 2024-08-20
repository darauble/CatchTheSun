import sys

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLineEdit,
    QLabel, QSizePolicy, QSpacerItem, QRadioButton, QButtonGroup, QDateEdit,
    QPushButton, QShortcut, QDialog, QMessageBox
)
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtCore import (
    Qt, QObject, pyqtSlot, pyqtSignal, QUrl, QDate                      
)

from skyfield.api import Topos, load
from skyfield.almanac import find_discrete, sunrise_sunset
import numpy as np

import time
from datetime import timezone, timedelta

import folium
import os
import math

def calculate_azimuth(lat1, lon1, lat2, lon2):
    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)

    delta_lon = lon2 - lon1

    x = math.sin(delta_lon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(delta_lon)
    
    azimuth = math.atan2(x, y)
    
    azimuth = math.degrees(azimuth)
    
    if azimuth < 0:
        azimuth += 360

    return azimuth

def haversine(lat1, lon1, lat2, lon2):
    # Radius of the Earth in kilometers. Wild americans can write the miles here.
    earth_radius = 6371.0

    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)

    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    # Calculate the distance in kilometers
    distance = earth_radius * c

    return distance

class ProcessingDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Processing...")
        self.setModal(True)
        self.setWindowFlags(Qt.Dialog | Qt.CustomizeWindowHint | Qt.WindowTitleHint)

        layout = QVBoxLayout()
        label = QLabel("Searching for azimuths...", self)
        layout.addWidget(label)
        self.setLayout(layout)


class CoordinateHandler(QObject):
    coordinatesChanged = pyqtSignal(str)
    markerColorChanged = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.current_marker_color = "red"

    @pyqtSlot(str)
    def receive_coordinates(self, latlon):
        self.coordinatesChanged.emit(latlon)

    @pyqtSlot(str)
    def set_marker_color(self, color):
        self.current_marker_color = color
        self.markerColorChanged.emit(color)


class CatchTheSunApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Catch the Sun")
        self.setGeometry(100, 100, 1300, 900)

        self.shortcut_exit = QShortcut(QKeySequence("Ctrl+Q"), self)
        self.shortcut_exit.activated.connect(self.close)

        # Ephemeris loading
        self.ephemeris = load("de421.bsp")
        self.timescale = load.timescale()

        # Initial latitude and longitude inputs for the observer
        self.observer_coords = QLineEdit(self)
        self.observer_coords.setFixedSize(180, 25)
        self.observer_coords.setReadOnly(True)

        self.object_coords = QLineEdit(self)
        self.object_coords.setFixedSize(180, 25)
        self.object_coords.setReadOnly(True)

        # Radio buttons
        self.radio1 = QRadioButton("Observer")
        self.radio2 = QRadioButton("Object")
        self.radio1.setFixedSize(100, 25)
        self.radio2.setFixedSize(100, 25)
        self.radio1.setChecked(True)

        self.radio_group = QButtonGroup()
        self.radio_group.addButton(self.radio1)
        self.radio_group.addButton(self.radio2)

        self.radio1.toggled.connect(self.update_marker_color)
        self.radio2.toggled.connect(self.update_marker_color)

        start_date_label = QLabel("Start date:")
        start_date_label.setFixedSize(70, 25)
        
        self.start_date_edit = QDateEdit(self)
        self.start_date_edit.setFixedSize(120, 25)
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDate(QDate.currentDate())

        end_date_label = QLabel("End date:")
        end_date_label.setFixedSize(70, 25)
        
        self.end_date_edit = QDateEdit(self)
        self.end_date_edit.setFixedSize(120, 25)
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDate(QDate.currentDate().addMonths(1))

        azimuth_label = QLabel("Azimuth:")
        azimuth_label.setFixedSize(120, 25)
        
        self.azimuth_edit = QLineEdit(self)
        self.azimuth_edit.setFixedSize(120, 25)
        self.azimuth_edit.setReadOnly(True)

        closest_azimuth_label = QLabel("Closest Azimuth:")
        closest_azimuth_label.setFixedSize(120, 25)
        
        self.closest_azimuth_edit = QLineEdit(self)
        self.closest_azimuth_edit.setFixedSize(120, 25)
        self.closest_azimuth_edit.setReadOnly(True)

        distance_label = QLabel("Distance:")
        distance_label.setFixedSize(70, 25)

        self.distance_edit = QLineEdit(self)
        self.distance_edit.setFixedSize(180, 25)
        self.distance_edit.setReadOnly(True)

        calculate_button = QPushButton("Find the azimuth and time!", self)
        calculate_button.setFixedSize(200, 25)
        calculate_button.clicked.connect(self.calculateAzimuthAndTime)

        calculated_time_label = QLabel("Time:")
        calculated_time_label.setFixedSize(70, 25)

        self.calculated_time_edit = QLineEdit(self)
        self.calculated_time_edit.setFixedSize(180, 25)
        self.calculated_time_edit.setReadOnly(True)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)

        input_layout1 = QHBoxLayout()
        
        input_layout1.addWidget(self.radio1)
        input_layout1.addWidget(self.observer_coords)
      
        input_layout1.addWidget(start_date_label)
        input_layout1.addWidget(self.start_date_edit)

        input_layout1.addWidget(azimuth_label)
        input_layout1.addWidget(self.azimuth_edit)

        input_layout1.addWidget(distance_label)
        input_layout1.addWidget(self.distance_edit)

        input_layout1.addWidget(calculate_button)

        input_layout1.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        input_layout2 = QHBoxLayout()
        
        input_layout2.addWidget(self.radio2)
        input_layout2.addWidget(self.object_coords)

        input_layout2.addWidget(end_date_label)
        input_layout2.addWidget(self.end_date_edit)

        input_layout2.addWidget(closest_azimuth_label)
        input_layout2.addWidget(self.closest_azimuth_edit)

        input_layout2.addWidget(calculated_time_label)
        input_layout2.addWidget(self.calculated_time_edit)
        
        input_layout2.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        # Add input layouts to main layout
        main_layout.addLayout(input_layout1)
        main_layout.addLayout(input_layout2)

        # Display the Folium map
        self.create_map()
        self.map_view = QWebEngineView()
        self.map_view.setUrl(QUrl.fromLocalFile(self.map_file_path))
        self.map_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Add the map view to the main layout
        main_layout.addWidget(self.map_view)

        # Set up the web channel for communication between Python and JavaScript
        self.channel = QWebChannel()
        self.coord_handler = CoordinateHandler()
        self.channel.registerObject("handler", self.coord_handler)
        self.map_view.page().setWebChannel(self.channel)

        # Connect the coordinatesChanged signal to the update_coordinates slot
        self.coord_handler.coordinatesChanged.connect(self.update_coordinates)

        # Set the initial marker color for the observer (default)
        # - Doesn"t work, most likely due to timing when things get initialized
        # - Initialized below in the injected JavaScript
        self.coord_handler.set_marker_color("red")
        # self.update_marker_color()

    def calculateAzimuthAndTime(self):
        start_date = self.start_date_edit.date()
        start_year = start_date.year()
        start_month = start_date.month()
        start_day = start_date.day()

        end_date = self.end_date_edit.date()
        end_year = end_date.year()
        end_month = end_date.month()
        end_day = end_date.day()


        observer_text = self.observer_coords.text()
        object_text = self.object_coords.text()

        if "," in observer_text and "," in object_text:
            start_time = self.timescale.utc(start_year, start_month, start_day)
            end_time = self.timescale.utc(end_year, end_month, end_day)

            if start_time.tt >= end_time.tt:
                QMessageBox.critical(self, "Error", "Start date should be earlier than the end date.")
                return
            
            processing_dialog = ProcessingDialog()
            processing_dialog.show()

            observer_lat, observer_lon = map(float, observer_text.split(","))
            observer_location = Topos(latitude_degrees=observer_lat, longitude_degrees=observer_lon)

            t, y = find_discrete(start_time, end_time, sunrise_sunset(self.ephemeris, observer_location))
    
            azimuths = []
            times = []
            
            for time_stamp in t:
                observer = self.ephemeris["earth"] + observer_location
                astrometric = observer.at(time_stamp).observe(self.ephemeris["sun"])
                alt, az, _ = astrometric.apparent().altaz()
                azimuths.append(az.degrees)
                times.append(time_stamp)
            
            best_time_index = np.argmin(np.abs(np.array(azimuths) - float(self.azimuth_edit.text())))

            self.closest_azimuth_edit.setText(f"{azimuths[best_time_index]:.2f}")

            ## Calculate time zone
            local_offset_sec = -time.timezone if time.localtime().tm_isdst == 0 else -time.altzone
            local_offset = timedelta(seconds=local_offset_sec)
            local_tz = timezone(local_offset)
            local_time = times[best_time_index].utc_datetime().astimezone(local_tz)
            self.calculated_time_edit.setText(f"{local_time:%Y-%m-%d %H:%M:%S}")

            processing_dialog.accept()
        else:
            QMessageBox.critical(self, "Error", "Observer and object are not selected yet.")

    def update_marker_color(self):
        if self.radio1.isChecked():
            self.coord_handler.set_marker_color("red")
        else:
            self.coord_handler.set_marker_color("blue")

    def create_map(self):
        # Create a map centered at a default location
        m = folium.Map(location=[55.1785178, 23.7507568], zoom_start=8)

        # JavaScript for injection to handle map clicks, add markers, draw a line, and get marker color from Python
        marker_azimuth_js = """
        function initializeChannel() {
            const mapElement = document.querySelector(".folium-map");
            const mapId = mapElement.id;
            const map = window[mapId];
            let marker1 = null;
            let marker2 = null;
            let line = null;

            // Function to update the marker color based on the current selection
            function addMarker(lat, lon, color) {
                let iconUrl, iconSize, iconAnchor;

                if (color === "red") {
                    if (marker1) {
                        map.removeLayer(marker1);
                    }
                    iconUrl = "http://maps.google.com/mapfiles/ms/icons/red-dot.png";
                } else {
                    if (marker2) {
                        map.removeLayer(marker2);
                    }
                    iconUrl = "http://maps.google.com/mapfiles/ms/icons/blue-dot.png";
                }

                // Set the icon size and anchor point (lower middle)
                iconSize = [32, 32];
                iconAnchor = [16, 32];  // Half width, full height

                let markerIcon = L.icon({
                    iconUrl: iconUrl,
                    iconSize: iconSize,
                    iconAnchor: iconAnchor
                });

                if (color === "red") {
                    marker1 = L.marker([lat, lon], {icon: markerIcon}).addTo(map).bindPopup("Observer: " + lat + ", " + lon);
                } else {
                    marker2 = L.marker([lat, lon], {icon: markerIcon}).addTo(map).bindPopup("Object: " + lat + ", " + lon);
                }

                // Check if both markers are placed, then draw the line
                if (marker1 && marker2) {
                    if (line) {
                        map.removeLayer(line);
                    }
                    let latlngs = [
                        marker1.getLatLng(),
                        marker2.getLatLng()
                    ];
                    line = L.polyline(latlngs, {color: "green"}).addTo(map);
                }
            }

            // Listen for the color change signal from Python
            handler.markerColorChanged.connect(function(color) {
                window.currentMarkerColor = color;
            });

            // Initialize the marker color from Python
            // window.currentMarkerColor = handler.current_marker_color;
            // - Doesn"t work, so hardcoded here as a default (workaround)
            window.currentMarkerColor = "red";

            map.on("click", function(e) {
                const lat = e.latlng.lat.toFixed(7);
                const lon = e.latlng.lng.toFixed(7);
                let latlon = lat + "," + lon;

                // Send the coordinates to the Python backend
                handler.receive_coordinates(latlon);

                // Add the marker based on the current color
                addMarker(lat, lon, window.currentMarkerColor);
            });
        }

        document.addEventListener("DOMContentLoaded", function() {
            const mapElement = document.querySelector(".folium-map");
            const mapId = mapElement.id;
            const map = window[mapId];

            new QWebChannel(qt.webChannelTransport, function(channel) {
                window.handler = channel.objects.handler;
                initializeChannel();
            });
        });
        """

        # Attach the JavaScript to the map
        m.get_root().html.add_child(folium.Element(f"<script src=\"qrc:///qtwebchannel/qwebchannel.js\"></script>"))
        m.get_root().html.add_child(folium.Element(f"<script>{marker_azimuth_js}</script>"))

        # Save the map as an HTML file
        self.map_file_path = os.path.join(os.getcwd(), "map.html")
        m.save(self.map_file_path)

    def update_coordinates(self, latlon):
        if latlon:
            if self.radio1.isChecked():
                self.observer_coords.setText(latlon)
            else:
                self.object_coords.setText(latlon)
            
            observer_text = self.observer_coords.text()

            if "," in observer_text:
                observer_lat, observer_lon = map(float, observer_text.split(","))

                object_text = self.object_coords.text()

                if "," in object_text:
                    object_lat, object_lon = map(float, object_text.split(","))
                    azimuth = calculate_azimuth(observer_lat, observer_lon, object_lat, object_lon)
                    distance = haversine(observer_lat, observer_lon, object_lat, object_lon)

                    self.azimuth_edit.setText(f"{azimuth:.2f}")
                    self.distance_edit.setText(f"{distance:.2f}")
    
    def closeEvent(self, event):
        os.remove(self.map_file_path)
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CatchTheSunApp()
    window.show()
    sys.exit(app.exec_())
