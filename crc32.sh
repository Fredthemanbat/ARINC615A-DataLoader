#!/bin/bash
#Gets system info
SYSTEM_INFO=$(uname -a)
#Returns OS info
OS_INFO=$(cat /etc/os-release)
#Returns all of the installed packages
INSTALLED_PACKAGES=$(dpkg -l)
#Creates one string with all the info
SYSTEM="$SYSTEM_INFO $OS_INFO $INSTALLED_PACKAGES"
#Saves the string to a temporary file
echo -n "$SYSTEM" > /tmp/system_info.txt
#Gets the crc32 of the temporary file
CRC32=$(crc32 /tmp/system_info.txt)
#Returns the CRC32 to the console
echo "CRC32: $CRC32"
#Deletes the temporary file
rm /tmp/system_info.txt
