#!/usr/bin/env bash
# Writes the FilmCraft fixtures from ffmpeg's built-in test sources (testsrc2, aevalsrc); no camera footage.
# Tested with ffmpeg 4.4 (libx264, libaom-av1). Licence: MIT OR Apache-2.0, like the rest of this repository.
set -euo pipefail
cd "$(dirname "$0")"

# 1. Frame times rounded to whole milliseconds in a 90 kHz MP4 track (as phones and messaging apps write them):
#    30 fps -> durations of 33/34 ms, 60 fps -> 16/17 ms.
for r in 30 60; do
  ffmpeg -v error -y -f lavfi -i testsrc2=size=640x360:rate=$r -t 4 \
    -vf "settb=1/1000,setpts='floor(N*1000/$r+0.5)/1000/TB'" -enc_time_base:v 1/1000 \
    -c:v libx264 -preset veryfast -bf 0 -pix_fmt yuv420p -video_track_timescale 90000 -vsync passthrough \
    fps${r}_ms_timestamps.mp4
done

# 2. 5.1 with one tone per channel: FL 300 Hz, FR 400 Hz, C 500 Hz, LFE 60 Hz, SL 700 Hz, SR 800 Hz (-12 dBFS each).
AE="aevalsrc=0.25*sin(2*PI*300*t)|0.25*sin(2*PI*400*t)|0.25*sin(2*PI*500*t)|0.25*sin(2*PI*60*t)|0.25*sin(2*PI*700*t)|0.25*sin(2*PI*800*t):s=48000:c=5.1(side)"
for c in ac3 eac3; do
  ffmpeg -v error -y -f lavfi -i testsrc2=size=640x360:rate=25 -f lavfi -i "$AE" -t 3 \
    -c:v libx264 -preset veryfast -pix_fmt yuv420p -c:a $c -b:a 384k surround51_$c.mp4
done
ffmpeg -v error -y -i surround51_ac3.mp4 -c copy surround51_ac3.mov   # control: same stream in MOV
ffmpeg -v error -y -i surround51_ac3.mp4 -c copy surround51_ac3.mkv   # control: same stream in Matroska
# AAC 5.1 in the 5.1(side) layout: ffmpeg writes it with a program config element
ffmpeg -v error -y -f lavfi -i testsrc2=size=640x360:rate=25 -f lavfi -i "$AE" -t 3 \
  -c:v libx264 -preset veryfast -pix_fmt yuv420p -c:a aac -b:a 384k surround51side_aac_pce.mp4

# 3. Pixel format label: AV1 in MP4, H.264 in Matroska.
ffmpeg -v error -y -f lavfi -i testsrc2=size=320x240:rate=25 -t 1 -c:v libaom-av1 -cpu-used 8 -b:v 300k -pix_fmt yuv420p av1_in_mp4.mp4
ffmpeg -v error -y -f lavfi -i testsrc2=size=320x240:rate=25 -t 1 -c:v libx264 -preset veryfast -pix_fmt yuv420p h264_in_mkv.mkv
