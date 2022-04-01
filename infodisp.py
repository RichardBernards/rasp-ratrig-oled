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
import math
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
menu_state = -1
button_click_time = 0
click_smoothing_time = 0.1
progressbar_completed = False
# Callback for button pressed event (needs to be in front of callback declaration)
def button_pressed(channel):
	global button_click_time, inactivity_time, sleeping
	if GPIO.input(PULSE_BTN):
		pressed_duration = time.time() - button_click_time - click_smoothing_time
		button_click_time = 0
		if VERBOSE: print("Button released                 | dT: " + str(pressed_duration) + "s")
	else:
		time.sleep(click_smoothing_time)
		if GPIO.input(PULSE_BTN) == False:
			if VERBOSE: print("Button pressed                  |")
			button_click_time = time.time()
			menu_change_state()

GPIO.setmode(GPIO.BCM)
GPIO.setup(PULSE_BTN, GPIO.IN)
GPIO.add_event_detect(PULSE_BTN, GPIO.BOTH, callback=button_pressed)

# Configure OLED display
i2c = busio.I2C(SCL, SDA)
oled = adafruit_ssd1306.SSD1306_I2C(128, 32, i2c)
oled.rotation = 2
oled.fill(0)
oled.show()

width = oled.width
height = oled.height
if VERBOSE: print("OLED disp size                  | width: " + str(width) + " height: " + str(height))
image = Image.new("1", (width, height))

draw = ImageDraw.Draw(image)
draw.rectangle((0, 0, width, height), outline=0, fill=0)


# Change the menu state and handle rotation of menu
def menu_change_state():
	global menu_state
	menu_state += 1
	if menu_state > 3: menu_state = 0
	if VERBOSE: print("Menu state changed              | State: " + str(menu_state))
	show_current_screen()


# Show current screen on OLED following current menu state
def show_current_screen():
	global progressbar_completed
	if menu_state == -1:
		## startup state
		disp_show_network_info()
	elif menu_state == 0:
		# check for shutdown progress bar
		show_progress_bar(SHUTDOWN_TIMEOUT)
		if progressbar_completed:
			progressbar_completed = False
			if VERBOSE: print("Shutting down now               |")
			subprocess.Popen("sudo shutdown now", shell = True)
			endprogram()
		disp_show_network_info()
	elif menu_state == 1:
		disp_show_usage_info()
	elif menu_state == 2:
		disp_show_line_nice("REBOOT")
		print("reboot")
	elif menu_state == 3:
		# check for reboot progress bar
		show_progress_bar(REBOOT_TIMEOUT)
		if progressbar_completed:
			progressbar_completed = False
			if VERBOSE: print("Rebooting now                   |")
			subprocess.Popen("sudo reboot now", shell = True)
			endprogram()
		disp_show_line_nice("SHUTDOWN")
		print("shutdown")
	else:
		if VERBOSE: print("No view for current menu state  | State: " + str(menu_state))


# Show a progressbar in 20% intervals
def show_progress_bar(total):
	global progressbar_completed
	while True:
		pressed_duration = time.time() - button_click_time - click_smoothing_time
		if button_click_time == 0 or GPIO.input(PULSE_BTN):
			progressbar_completed = True  if pressed_duration >= total else False
			break
		else:
			if math.floor(pressed_duration) % math.floor(total / 5) == 0:
				disp_show_progressbar(math.floor(pressed_duration) / total)


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
	if VERBOSE: print("Progressbar                     | p: " + str(progress) + ", w: " + str(progress_width))
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


# Main loop to keep program running
def loop():
	while True:
		something = 1


# Cleanup
def endprogram():
	if VERBOSE: print("Ending program and cleaning up |")
	oled.poweroff()
	GPIO.cleanup()


if __name__ == '__main__':
	try:
		show_current_screen()
		loop()

	except KeyboardInterrupt:
		endprogram()
