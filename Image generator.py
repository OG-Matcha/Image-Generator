import openai
import re
import requests
import os
import json
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import QThread, pyqtSignal


class ConfigWindow(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Configuration")

        # Create a QIcon object from the icon file
        icon_path = "Icon.ico"
        icon = QIcon(icon_path)
        self.setWindowIcon(icon)

        # Create the layout
        self.layout = QtWidgets.QVBoxLayout(self)

        # Create the API key input
        self.api_key_label = QtWidgets.QLabel("OpenAI API key:", self)
        self.api_key_input = QtWidgets.QLineEdit(self)
        self.api_key_input.setPlaceholderText("Enter your OpenAI API key")
        self.api_key_layout = QtWidgets.QHBoxLayout()
        self.api_key_layout.addWidget(self.api_key_label)
        self.api_key_layout.addWidget(self.api_key_input)
        self.layout.addLayout(self.api_key_layout)

        # Create the save button
        self.save_button = QtWidgets.QPushButton(
            "Save", clicked=self.save_config)
        self.layout.addWidget(self.save_button)

    def save_config(self):
        api_key = self.api_key_input.text()
        # Validate the API key
        if not self.validate_api_key(api_key):
            # Show an error message if the API key is not valid
            QtWidgets.QMessageBox.warning(
                self, "Invalid API key", "Please enter a valid OpenAI API key")
            return

        # Save the API key to the config.json file
        config = {"api_key": api_key}
        with open("config.json", "w") as f:
            json.dump(config, f)

        # Close the configuration window
        self.close()

    def validate_api_key(self, api_key):
        # Set the API key
        openai.api_key = api_key

        # Make a request to the OpenAI API to get the models list
        try:
            _ = openai.Model.list()
        except openai.error.AuthenticationError:
            # Return False if the request fails
            return False

        # Return True if the request succeeds
        return True


class ImageGenerationThread(QThread):
    # Declare a signal to emit the generated image
    image_generated = pyqtSignal(QPixmap)
    progress_bar_start_signal = pyqtSignal()
    progress_bar_stop_signal = pyqtSignal()
    warning_signal = QtCore.pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        self.prompt = ""
        self.size = ""

    def run(self):
        try:
            self.progress_bar_start_signal.emit()
            # Generate the image
            response = openai.Image.create(
                prompt=self.prompt,
                n=1,
                size=self.size,
            )
            # Extract the image data from the response
            image_url = response['data'][0]['url']
            image_data = requests.get(image_url).content
            # Load the image data into a QPixmap
            pixmap = QPixmap()
            pixmap.loadFromData(image_data)
            # Emit the image
            self.progress_bar_stop_signal.emit()
            self.image_generated.emit(pixmap)

        # Handle invalid prompt error
        except openai.error.InvalidRequestError as e:

            if re.search(r"too long", str(e)):
                self.warning_signal.emit(
                    "Invalid Prompt", "Your prompt may contains too many texts")
                self.progress_bar_stop_signal.emit()
            elif re.search(r"prompt", str(e)):
                self.warning_signal.emit(
                    "Invalid Prompt", "Your prompt may contain text that are not valid")
                self.progress_bar_stop_signal.emit()

        # Handle connection failures
        except openai.error.APIConnectionError:
            self.warning_signal.emit(
                "Connect Error", "You should connect to the internet and try again")
            self.progress_bar_stop_signal.emit()

        except requests.exceptions.ConnectionError:
            self.warning_signal.emit(
                "Connect Error", "Your should connect to the internet and try again")
            self.progress_bar_stop_signal.emit()


class DrawingBotWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OpenAI Drawing Bot")
        self.setMinimumSize(1200, 1300)

        # Check for OpenAI API key
        self.config_path = "config.json"

        if not os.path.exists(self.config_path):
            # No configuration file, let the user enter the API key
            self.show_config_window()
        else:
            # Load the API key from the configuration file
            with open(self.config_path, "r") as f:
                config = json.load(f)
                openai.api_key = config["api_key"]

        # Create a QIcon object from the icon file
        icon_path = "Icon.ico"
        icon = QIcon(icon_path)
        self.setWindowIcon(icon)

        # Create the central widget and layout
        self.central_widget = QtWidgets.QWidget(self)
        self.central_layout = QtWidgets.QVBoxLayout(self.central_widget)
        self.setCentralWidget(self.central_widget)

        # Create the prompt input
        self.prompt_label = QtWidgets.QLabel("Prompt:", self.central_widget)
        self.prompt_input = QtWidgets.QLineEdit(self.central_widget)
        self.prompt_input.setPlaceholderText("Enter a prompt")
        self.prompt_layout = QtWidgets.QHBoxLayout()
        self.prompt_layout.addWidget(self.prompt_label)
        self.prompt_layout.addWidget(self.prompt_input)
        self.central_layout.addLayout(self.prompt_layout)

        # Create the horizontal layout for the size buttons
        self.size_button_layout = QtWidgets.QHBoxLayout()
        self.size_label = QtWidgets.QLabel("Size:", self.central_widget)
        self.size_button_layout.addWidget(self.size_label)

        # Create the 256x256 size button
        self.size_256_button = QtWidgets.QPushButton(
            self.central_widget, text="256x256", clicked=self.set_size_256
        )
        self.size_button_layout.addWidget(self.size_256_button)

        # Create the 512x512 size button
        self.size_512_button = QtWidgets.QPushButton(
            self.central_widget, text="512x512", clicked=self.set_size_512
        )
        self.size_button_layout.addWidget(self.size_512_button)

        # Create the 1024x1024 size button
        self.size_1024_button = QtWidgets.QPushButton(
            self.central_widget, text="1024x1024", clicked=self.set_size_1024
        )
        self.size_button_layout.addWidget(self.size_1024_button)

        # Add the size button layout to the central layout
        self.central_layout.addLayout(self.size_button_layout)

        # Create the file name input
        self.name_label = QtWidgets.QLabel("File Name:", self.central_widget)
        self.name_input = QtWidgets.QLineEdit(self.central_widget)
        self.name_input.setPlaceholderText("Enter the file name")
        self.name_layout = QtWidgets.QHBoxLayout()
        self.name_layout.addWidget(self.name_label)
        self.name_layout.addWidget(self.name_input)
        self.central_layout.addLayout(self.name_layout)

        # Create the horizontal layout for the format buttons
        self.format_button_layout = QtWidgets.QHBoxLayout()
        self.format_label = QtWidgets.QLabel("Format:", self.central_widget)
        self.format_button_layout.addWidget(self.format_label)

        # Create the jpeg format button
        self.format_jpeg_button = QtWidgets.QPushButton(
            self.central_widget, text="JPEG", clicked=self.set_format_jpeg
        )
        self.format_button_layout.addWidget(self.format_jpeg_button)

        # Create the png format button
        self.format_png_button = QtWidgets.QPushButton(
            self.central_widget, text="PNG", clicked=self.set_format_png
        )
        self.format_button_layout.addWidget(self.format_png_button)

        # Create the bmp format button
        self.format_bmp_button = QtWidgets.QPushButton(
            self.central_widget, text="BMP", clicked=self.set_format_bmp
        )
        self.format_button_layout.addWidget(self.format_bmp_button)

        # Add the format button layout to the central layout
        self.central_layout.addLayout(self.format_button_layout)

        # Create the horizontal layout for the file path, save image and generate buttons
        self.button_layout = QtWidgets.QHBoxLayout()

        # Create the file path button
        self.file_path_button = QtWidgets.QPushButton(
            self.central_widget, text="Select File Path", clicked=self.select_file_path
        )
        self.button_layout.addWidget(self.file_path_button)

        # Create the save button
        self.save_button = QtWidgets.QPushButton(
            self.central_widget, text="Save Image", clicked=self.save_image
        )
        self.button_layout.addWidget(self.save_button)

        # Create the generate button
        self.generate_button = QtWidgets.QPushButton(
            self.central_widget, text="Generate", clicked=self.generate_image
        )
        self.button_layout.addWidget(self.generate_button)

        # Add the horizontal layout to the central layout
        self.central_layout.addLayout(self.button_layout)

        # Create the progress bar
        self.progress_bar = QtWidgets.QProgressBar(self.central_widget)
        self.progress_bar.setVisible(False)
        self.style = '''
            QProgressBar {
                border: 2px solid #000;
                border-radius: 5px;
                text-align:center;
                height: 20px;
            }
            QProgressBar::chunk {
                background: #C7F08D;
                width:1px;
            }
        '''
        self.progress_bar.setStyleSheet(self.style)
        self.central_layout.addWidget(self.progress_bar)

        # Create the image preview label
        self.preview_label = QtWidgets.QLabel(
            "The Image will show here", self.central_widget)
        self.preview_label.setAlignment(QtCore.Qt.AlignCenter)
        self.central_layout.addWidget(self.preview_label)

        # Initialize the file path
        self.file_path = ""

        # Create the thread
        self.image_generation_thread = ImageGenerationThread()
        # Connect the signal to a slot
        self.image_generation_thread.image_generated.connect(self.update_image)
        self.image_generation_thread.warning_signal.connect(self.warning)
        self.image_generation_thread.progress_bar_start_signal.connect(
            self.show_progress_bar)
        self.image_generation_thread.progress_bar_stop_signal.connect(
            self.hide_progress_bar)

    def set_size_256(self):
        self.size_label.setText("Size:\t256x256")

    def set_size_512(self):
        self.size_label.setText("Size:\t512x512")

    def set_size_1024(self):
        self.size_label.setText("Size:\t1024x1024")

    def set_format_jpeg(self):
        self.format_label.setText("Format:\tJPEG")

    def set_format_png(self):
        self.format_label.setText("Format:\tPNG")

    def set_format_bmp(self):
        self.format_label.setText("Format:\tBMP")

    def select_file_path(self):
        self.file_path = QtWidgets.QFileDialog.getExistingDirectory(
            self, caption="Select file path")

    def show_config_window(self):
        config_window = ConfigWindow()
        config_window.exec_()

    def generate_image(self):
        # Get the prompt, size, name, and format from the inputs
        prompt = self.prompt_input.text()
        size = self.size_label.text()

        # Check if all of the input is valid and exist
        if not openai.api_key:
            self.show_config_window()
            return

        if not prompt:
            QtWidgets.QMessageBox.warning(
                self, "Missing Entry", "Please enter a prompt.")
            return

        if not size[5:]:
            QtWidgets.QMessageBox.warning(
                self, "Missing Entry", "Please select a size.")
            return

        # Set the prompt, size in the thread
        self.image_generation_thread.prompt = prompt
        self.image_generation_thread.size = size[6:]

        # Start the thread
        self.image_generation_thread.start()

    def warning(self, title, message):
        QtWidgets.QMessageBox.warning(self, title, message)

    def show_progress_bar(self):
        # Show the progress bar
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setValue(30)

    def hide_progress_bar(self):
        # Hide the progress bar
        self.progress_bar.setVisible(False)

    def update_image(self, pixmap):
        # Update the image label with the new image
        self.preview_label.setPixmap(pixmap)
        self.image = pixmap

    def save_image(self):
        # Validate the inputs
        if not self.name_input.text():
            QtWidgets.QMessageBox.warning(
                self, "Missing Entry", "Please enter a file name.")
            return
        if not self.file_path:
            QtWidgets.QMessageBox.warning(
                self, "Missing Path", "Please select a file path.")
            return
        if not self.image:
            QtWidgets.QMessageBox.warning(
                self, "No Image", "Please generate an image first.")
            return
        if not self.format_label.text()[7:]:
            QtWidgets.QMessageBox.warning(
                self, "Missing Entry", "Please select a format.")
            return

        # Save the image
        file_name = self.name_input.text()
        format = self.format_label.text()[8:].lower()
        self.image.save(f"{self.file_path}/{file_name}.{format}")


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    window = DrawingBotWindow()
    window.show()
    app.exec_()
