# Copyright (c) 2022 Richard Bernards
# Author: Richard Bernards
#
# MIT License
#
# Copyright (c) 2022 Richard Bernards
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# Dependency on adafruit-circuitpython-ssd1306 (https://github.com/adafruit/Adafruit_CircuitPython_SSD1306)
#
# prerequisite install commands:
#    sudo apt-get install python3-pip python3-pil python-smbus i2ctools
#    sudo pip3 install adafruit-circuitpython-ssd1306
#    sudo pip3 install psutil
#
# Use 'i2cdetect -y 1' to check for disp at 3xC

import time
import subprocess
from board import SCL, SDA
import busio
import RPi.GPIO as GPIO
from PIL import Image, ImageDraw, ImageFont
import adafruit_ssd1306
import psutil

# GPIO PIN Button is connected to
PULSE_BTN = 20
# Time in seconds the screen will remain on before going to sleep
OLED_SLEEP_TIMEOUT = 15
# Time in seconds to keep button pressed to trigger reboot
REBOOT_TIMEOUT = 5
# Time in seconds to keep button pressed to trigger shutdown
SHUTDOWN_TIMEOUT = 10
# Font to use on display
font = ImageFont.load_default()
#font = ImageFont.truetype('/usr/share/fonts/truetype/dogica/dogica.ttf', 6)

# Verbose commandline printing on or off
VERBOSE = False


# Setup
GPIO.setmode(GPIO.BCM)
GPIO.setup(PULSE_BTN, GPIO.IN)

i2c = busio.I2C(SCL, SDA)
oled = adafruit_ssd1306.SSD1306_I2C(128, 32, i2c)


# Configure OLED display
oled.rotation = 2
oled.fill(0)
oled.show()

width = oled.width
height = oled.height
if VERBOSE: print("OLED disp size                  | width: " + str(width) + " height: " + str(height))
image = Image.new("1", (width, height))

draw = ImageDraw.Draw(image)
draw.rectangle((0, 0, width, height), outline=0, fill=0)

# Pretty print byte sizes into a string
def get_size(bytes, suffix="B"):
	factor = 1024
	for unit in ["", "K", "M", "G", "T", "P"]:
		if bytes < factor:
			return f"{bytes:.0f}{unit}{suffix}"
		bytes /= factor


# Show a line with a 1px white border at the edges of the screen
def disp_show_line_nice(line):
	if VERBOSE: print("Printing nice line              | line: " + line)
	padding = 1

	draw.rectangle((0, 0, width, height), outline=0, fill=0) # clear screen
	draw.rectangle((padding, padding, width - padding - padding, height - padding - padding), outline=255, fill=0)
	draw.text((padding, padding+10), "  " + line, font=font, fill=255) # padding of 1 results in 32-2=30 30/3=10px offset for 3 equal lines with default font
	oled.image(image)
	oled.show()


# Show a progressbar (1px white border, fill border with white progressbar according to progress float between 0 and 1)
def disp_show_progressbar(progress):
	padding = 1
	draw.rectangle((0, 0, width, height), outline=0, fill=0) # clear screen
	draw.rectangle((padding, padding, width - padding - padding, height - padding - padding), outline=255, fill=0)
	progress_width = round(((width * min([1, progress])) - (padding*6))*1000) / 1000
	if VERBOSE: print("progress: " + str(progress) + " width: "+ str(progress_width))
	draw.rectangle((padding*3, padding*3, progress_width, height - (padding*6)), outline=255, fill=255)
	oled.image(image)
	oled.show()


# show network info on the screen (hostname and ip-address)
def disp_show_network_info():
	if VERBOSE: print("Printing network info           |")
	padding = 1
	INFO_HOSTNAME = subprocess.check_output("hostname", shell = True)
	INFO_IP = subprocess.check_output("hostname -I | cut -d\' \' -f1", shell = True)

	draw.rectangle((0, 0, width, height), outline=0, fill=0) # clear screen
	draw.rectangle((padding, padding, width - padding - padding, height - padding - padding), outline=255, fill=0)
	draw.text((padding, padding+5),  " h: " + INFO_HOSTNAME.decode('UTF-8'), font=font, fill=255)
	draw.text((padding, padding+15), " ip:" + INFO_IP.decode('UTF-8'), font=font, fill=255)
	oled.image(image)
	oled.show()


# show usage info (cpu, diskusage, memory usage)
def disp_show_usage_info():
	if VERBOSE: print("Printing usage info             |")
	padding = 1
	INFO_CPU = f"{psutil.cpu_percent()}%"
	svmem = psutil.virtual_memory()
	INFO_MEMORY = f"{svmem.percent}% {get_size(svmem.used)}/{get_size(svmem.total)}"
	partitions = psutil.disk_partitions()
	partition_usage = psutil.disk_usage(partitions[0].mountpoint)
	INFO_DISK = f"{get_size(partition_usage.used)}/{get_size(partition_usage.total)}"

	draw.rectangle((0, 0, width, height), outline=0, fill=0) # clear screen
	draw.rectangle((padding, padding, width - padding - padding, height - padding - padding), outline=255, fill=0)
	draw.text((padding, padding+5),  " C:" + INFO_CPU + " D:" + INFO_DISK, font=font, fill=255)
	draw.text((padding, padding+15), " M:" + INFO_MEMORY, font=font, fill=255)
	oled.image(image)
	oled.show()


# main loop handling button presses and cycling through menu and power cycle options
def loop():
	if VERBOSE: print("Starting loop...                |")
	menu_state = 0
	press_threshold = 0.2
	disp_show_network_info()
	oled_sleep_timer = OLED_SLEEP_TIMEOUT
	change_screen = False
	reboot_state = False
	shutdown_state = False
	total_progress = 0
	while True:
		# check for input from pulse button
		press_duration = 0
		if GPIO.input(PULSE_BTN) == False:
			if VERBOSE: print("Push button pressed...          |")
			if menu_state == -1: oled.poweron()
			oled_sleep_timer = OLED_SLEEP_TIMEOUT
			while GPIO.input(PULSE_BTN) == False:
				time.sleep(0.1)
				press_duration += 0.1
				if (reboot_state or shutdown_state) and press_duration > press_threshold:
					if VERBOSE: print("Updating progress bar           |")
					total_progress = REBOOT_TIMEOUT if reboot_state else SHUTDOWN_TIMEOUT
					disp_show_progressbar(press_duration / total_progress)
			if menu_state > 1 and press_duration > press_threshold:
				if VERBOSE: print("Longpress detected              | for " + str(press_duration) + "s")
				if (press_duration / total_progress) < 1:
					change_screen = True
				if reboot_state and press_duration >= REBOOT_TIMEOUT:
					if VERBOSE: print("Reboot initiated                |")
					disp_show_line_nice("Rebooting...")
					subprocess.Popen("sudo reboot now", shell = True)
					break
				if shutdown_state and press_duration >= SHUTDOWN_TIMEOUT:
					if VERBOSE: print("Shutdown initiated              |")
					disp_show_line_nice("Shutting down...")
					subprocess.Popen("sudo shutdown now", shell = True)
					break
			else:
				menu_state += 1
				change_screen = True
		else:
			time.sleep(0.1)
			oled_sleep_timer -= 0.1

			# check if it's time to put the oled to sleep...
			if oled_sleep_timer <= 0:
				if VERBOSE: print("Putting oled to sleep...        |")
				draw.rectangle((0, 0, width, height), outline=0, fill=0)
				oled.image(image)
				oled.show()
				menu_state = -1
				oled.poweroff()
			continue

		if oled_sleep_timer > 0 and change_screen:
			# Handle different menu states
			if menu_state > 3:
				menu_state = 0
			# --0-- Show hostname nicely
			if menu_state == 0:
				shutdown_state = False
				disp_show_network_info()
			# --1-- Show usage information
			elif menu_state == 1:
				disp_show_usage_info()
			# --2-- Reboot screen
			elif menu_state == 2:
				reboot_state = True
				disp_show_line_nice("REBOOT")
			# --3-- Shutdown screen
			elif menu_state == 3:
				reboot_state = False
				shutdown_state = True
				disp_show_line_nice("SHUTDOWN")
			change_screen = False


def endprogram():
	if VERBOSE: print("Ending program and cleaning up |")
	oled.poweroff()
	GPIO.cleanup()


if __name__ == '__main__':
	try:
		loop()

	except KeyboardInterrupt:
		endprogram()
