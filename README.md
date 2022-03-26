# Introduction
Python code to be ran on Raspberry Pi with a 128x32 small oled display connected to a raspberry pi over i2c. A pulse button connected to a GPIO pin can be used to cycle through a menu.

# Features
* View networking information (hostname and ip-address) on oled-screen
* View usage information (cpu%, disk usage, memory usage) on oled-screen
* Reboot (issues `sudo reboot now` using 5 seconds press when in the correct menu-state (no worries, a progressbar will tell you when to let go)
* Shutdown (issues `sudo shutdown now` using 10 seconds press when in the correct menu-state (no worries, a progressbar will tell you when to let go)
* Ability to use your own font on the screen (ttf)
* Sleep timeout of 15 seconds (oled screen will poweroff after this time
* All timeouts listed above are configurable at top of script
* Set `VERBOSE = True` if you want more verbose output on the commandline

This piece of code implements the adafruit circuitpython SSD1305 i2c driver for the oled display.

# Dependencies
This piece of code depends on:
* [Adafruit CircuitPython SSD1305](https://github.com/adafruit/Adafruit_CircuitPython_SSD1306/)

# Installing on Raspberry PI
Make sure you have python3, pip for python3, python3-pil, python-smbus and i2ctools installed:
```
sudo apt-get install python3  pyhon3-pip python3-pil python-smbus i2ctools
```
Use pip3 to install adafruit ssd1305 dependency and psutil:
```
sudo pip3 install adafruit-circuitpython-ssd1306
sudo pip3 install psutil
```

Afterwards, you can use `i2cdetect -y 1` to check via commandline whether the oled is recognised (should list the 128x32 version on 3c)

# Usage Example
Just run using python:
```
python infodisp.py
```
You can use `Ctrl + C` to exit. This will also power off the oled display

If you want it to start automatically on boot, know that some of the information might not be ready (e.g. ip-address). Just cycle through the menu until it is there ;)
Here is how to do it;
```
sudo nano -w /etc/rc.local
```
add a new line just before `exit 0`
add following on that new line:
```
sudo python3 /path/to/infodisp.py &
```
Reboot and enjoy the hapiness!

# Contributing
Contributions are welcome! Please use the issues or feature requests functionality of GitHub.
