#!/bin/bash

# Unofficial Bash Strict Mode http://redsymbol.net/articles/unofficial-bash-strict-mode/
set -euo pipefail
IFS=$'\n\t'

# Get current dir
TOP_DIR=`pwd`

# Change to export dir
cd export
for i in *.flv; do
	# Get file name without extension
	_filename=`basename "${i}" ".flv"`

	# Split .flv in .264/.aac files. Needs ffmpeg installed.
	echo "Spliting video of file ${_filename}.flv"
	ffmpeg -i "${_filename}.flv" -vcodec copy -vbsf h264_mp4toannexb "${_filename}.h264" -acodec copy "${_filename}.aac" 
	
	# Merge .264/.aac/.ass files in .mkv. Needs mkvtoolnix installed.
	echo "Starting mkvmerge of file ${_filename}"
	if [ ! -f ${_filename}.ass ]; then
		mkvmerge -o "${_filename}.mkv" "${_filename}.h264" --aac-is-sbr 0 "${_filename}.aac"
	else
		mkvmerge -o "${_filename}.mkv" "${_filename}.ass" "${_filename}.h264" --aac-is-sbr 0 "${_filename}.aac"
	fi
done

# Delete all temporary files
echo "Cleaning temporary files"
for i in *.mkv; do
        _filename=`basename "${i}" ".mkv"`
        # Time to get rid of those ass and flv files
        if [ -e "${_filename}.flv" ]; then rm "${_filename}.flv"; fi
        if [ -e "${_filename}.ass" ]; then rm "${_filename}.ass"; fi
        if [ -e "${_filename}.aac" ]; then rm "${_filename}.aac"; fi
        if [ -e "${_filename}.h264" ]; then rm "${_filename}.h264"; fi
done
#find . -type f ! -iname '*.mkv' -delete


# Go back to original dir
cd "${TOP_DIR}"
