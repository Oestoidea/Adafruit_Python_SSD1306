# Copyright (c) 2017
# Author: Oestoidea

import time

import Adafruit_GPIO.SPI as SPI
import Adafruit_SSD1306

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

import os, re, sys
import psutil
from datetime import datetime
from time import sleep

from collections import defaultdict

import logging

logger_path = sys.path[0] + '/log_shapes.log'
logging.basicConfig(format = u'%(levelname)-8s [%(asctime)s] %(message)s', level = logging.INFO, filename = logger_path)

# Raspberry Pi pin configuration:
RST = 24

times = 0

# 128x64 display with hardware I2C:
disp = Adafruit_SSD1306.SSD1306_128_64(rst = RST)

# Initialize library.
disp.begin()

# Clear display.
disp.clear()
disp.display()

# Create blank image for drawing.
# Make sure to create image with mode '1' for 1-bit color.
width = disp.width
height = disp.height
logo = Image.new('1', (width, height))

# Get drawing object to draw on image.
draw = ImageDraw.Draw(logo)

logo_path = sys.path[0] + '/pi_logo.png'
logo = Image.open(logo_path).convert('1')
draw.bitmap((1, 1), logo, fill = 255)

disp.image(logo)
disp.display()
time.sleep(5)

# Draw some shapes.
# First define some constants to allow easy resizing of shapes.
pad = 1
# Move left to right keeping track of the current x position for drawing shapes.
row = 10

# Load default font.
#font = ImageFont.load_default()
font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 9)

while True:
  times += 1
  image = Image.new('1', (width, height))
  draw = ImageDraw.Draw(image)
  draw.rectangle((0, 0, width, height), outline = 0, fill = 0)
  
  top = pad
  
  # get load average
  def get_uptime():
    try:
      uptime = os.popen("tail /proc/loadavg")
      ut = str(uptime.read()).rstrip('\r\n')
      loadavg = re.findall(r'^\d+\.\d+\s\d+\.\d+\s\d+\.\d+', ut)[0]
      tasks = re.findall(r'\/\d+', ut)[0].lstrip('/')
    except IndexError:
      logging.info(u'get_uptime')
      loadavg = '0.00 0.00 0.00'
      tasks = '0'
  
    return "%s %s tasks" % (loadavg, tasks)
  
  get_uptime = get_uptime()
  draw.text((pad, top), get_uptime, font = font, fill = 255)

  top += row

  # get amount of memory and SDcard in use
  def mem_usage(dir):
    try:
      virt_usage = psutil.virtual_memory()
    except Exception:
      logging.info(u'virt_usage')
      virt_usage = 0
    
    try:
      disk_usage = psutil.disk_usage(dir)
    except Exception:
      logging.info(u'disk_usage')
      disk_usage = 0
    
    return "Mem: %.1fMB SD: %.0f%%" % (int(str(virt_usage.used)) / 1024 / 1024, disk_usage.percent)
  
  mem_usage = mem_usage('/')
  draw.text((pad, top), mem_usage, font = font, fill = 255)
    
  top += row

  # get, return CPU's current temperature (or command 'vcgencmd measure_temp')
  def cpu_temp():
    try:
      tempC = int(open('/sys/class/thermal/thermal_zone0/temp').read()) / 1000
      tempF = (tempC * 9 / 5) + 32
    except Exception:
      logging.info(u'cpu_temp')
      tempC = 0
      tempF = 0
    
    return "CPU: %.1f°C/%.0d°F" % (tempC, tempF)

  cpu_temp = cpu_temp()
  draw.text((pad, top), cpu_temp, font = font, fill = 255)
  
  top += row

  # get external IP, ping delay to 8.8.8.8
  def get_wandata():
    try:
      ifconf = os.popen('ifconfig eth0 | grep "inet\ addr" | cut -f12 -d " " | cut -c 6-')
      wan_ip = str(ifconf.read()).rstrip(' \r\n')
    except Exception:
      logging.info(u'wan_ip')
      wan_ip = 'N/С'

    try:
      external = os.popen('ping 8.8.8.8 -c 1 | grep "time=" | cut -f7 -d " " | cut -c 6-')
      ping = str(external.read()).rstrip(' \r\n')
    except IndexError:
      logging.info(u'ping')
      ping = 'N/С'
        
    return "%s %sms" % (wan_ip, ping)

  get_wandata = get_wandata()
  draw.text((pad, top), get_wandata, font = font, fill = 255)
  
  top += row

  # get gate`s IP, channel and dBm
  def get_apdata():
    try:
      ifconf = os.popen('ifconfig wlan0 | grep "inet\ addr" | cut -f12 -d " " | cut -c 6-')
      wlan_ip = str(ifconf.read()).rstrip(' \r\n')
    except Exception:
      logging.info(u'wlan_ip')
      wlan_ip = 'N/С'
    
    try:
      channel = os.popen("cat /etc/hostapd/hostapd.conf | grep channel=")
      ch = re.findall(r'\d+$', str(channel.read()).rstrip('\r\n'))[0]
    except IndexError:
      logging.info(u'ch')
      ch = 'N/С'
    
    try:
      level = os.popen("iwconfig wlan0 | grep Tx-Power")
      dbm = re.findall(r'=\d+\sdBm', str(level.read()).rstrip('\r\n'))[0].lstrip('=').rstrip(' dBm')
    except IndexError:
      logging.info(u'dbm')
      dbm = 'N/С'
        
    return "%s %sch %sdBm" % (wlan_ip, ch, dbm)
  
  get_apdata = get_apdata()
  draw.text((pad, top), get_apdata, font = font, fill = 255)
  
  top += row
  
  # get SSID and number of clients
  def get_ssid():
    try:
      id = os.popen("iw wlan0 info | grep ssid")
      ssid = str(re.findall(r'\S+$', str(id.read()).rstrip('\r\n'))[0])
    except IndexError:
      logging.info(u'SSID')
      ssid = ' N/С'
    
    try:    
      clients = os.popen("iw dev wlan0 station dump | grep Station")
      word_list = str(clients.read()).split()

      word_count = 0
      
      for word in word_list:
        if word == 'Station':
          word_count += 1

      if word_count >= 2:
        suffix = 's'
      else:
        suffix = ''
    except Exception:
      logging.info(u'word_count')
      word_count = 0
      suffix = ''

    return "SSID: %s %d client%s" % (ssid, word_count, suffix)

  get_ssid = get_ssid()
  draw.text((pad, top), get_ssid, font = font, fill = 255)

  print('%2.f %.2f | %s | %s | %s | %s | %s | %s' % (times, time.time(), get_uptime, mem_usage, cpu_temp, get_wandata, get_apdata, get_ssid))
  
  if times >= 60: # one time on about one minute
    times = 0
    disp.begin() # to avoid the screen freezes

  disp.image(image)
  disp.display()
  time.sleep(1)
