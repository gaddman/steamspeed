#!/usr/bin/env python3
# Measure Steam download speed
# Chris Gadd
# https://github.com/gaddman/steamspeed
# 2018-03-11

import argparse
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

logfile = str(Path.home()) + "/.steam/logs/content_log.txt"

# Parse arguments and set defaults
parser = argparse.ArgumentParser()
# Steam game ID. https://store.steampowered.com/app/xxx
parser.add_argument("-a", help="Application ID", default="232370")
parser.add_argument("-u", help="Steam username", default="anonymous")
parser.add_argument("-p", help="Steam password", default="")
parser.add_argument("-v", help="Verbose", action="store_true")
args = parser.parse_args()
appID = args.a
user = args.u
passwd = args.p
verbose = args.v

# Steamcmd strings to remove and install application
info = "steamcmd +login " + user + " " + passwd + " +app_info_print " + appID + " +quit"
download = (
    "steamcmd +login " + user  + " "  + passwd
    + " +@sSteamCmdForcePlatformType windows"
	+ " +app_uninstall -complete " + appID
    + " +app_update " + appID
    + " +download_sources"
	+ " +quit"
)

# Get info on application
output = subprocess.check_output(info.split()).decode(sys.stdout.encoding)
appName = re.search(r'\s+"common"\s+{\s+"name"\s+"([^"]+)', output).group(1)
print(
    "Download test for application {} [{}] (also see https://steamdb.info/app/{}/)".format(
        appID, appName, appID
    )
)

# Kick off download of new application
p = subprocess.Popen(download.split(), stdout=subprocess.PIPE)
# Watch log for events
f = open(logfile, "r")
f.seek(0, 2)  # jump to end of file
while True:
    line = f.readline()
    if line:
        if verbose:
            print(">>> " + line, end="")
        if "Update Required,Fully Installed,Files Missing,Uninstalling" in line:
            # Completed removal
            print("Removed existing copy")
        elif "update started" in line:
            # Started download
            starttime = re.search(r"(\d+:\d+:\d+)", line).group(1)
            size = int(re.search(r"(\d+)\s+$", line).group(1))
            if verbose:
                print("Downloading " + str(int(size / 1024 / 1024)) + " MB...")
        elif "download sources" in line:
            # Identified download sources
            sources, proxies = re.search(
                r"(\d+) download sources and (\d+) caching proxies", line
            ).groups()
            print(sources + " download sources (and " + proxies + " caching proxies)")
        elif "Created download interface" in line:
            # Adding new download source
            host = re.search(r"host ([^\(]+)", line).group(1)
            print("Adding download source: " + host)
        elif "update changed : Running,Committing" in line:
            # Finished downloading
            endtime = re.search(r"(\d+:\d+:\d+)", line).group(1)
            delta = (
                datetime.strptime(endtime, "%H:%M:%S")
                - datetime.strptime(starttime, "%H:%M:%S")
            ).seconds
            break
        elif "Failed" in line:
            # Something went wrong
            sys.exit("Failed to download, check log (" + logfile + ")")
    else:
        # wait for next line
        time.sleep(0.5)
f.close()

# Extract source info from stdout
response, _ = p.communicate()
sources = re.search(
    r"(Download sources.*failed = \d+)", response.decode(), re.DOTALL
).group(1)
if verbose:
    print("\n" + sources + "\n")

# Print summary of performance
speed = size * 8 / 1024 / 1024 / delta  # Mbps
print(
    "Completed download of {:d} MB in {:d} seconds at {:d} Mbps ({:0.1f} MB/s), from {:s} to {:s}".format(
        int(size / 1024 / 1024), delta, int(speed), speed / 8, starttime, endtime
    )
)
