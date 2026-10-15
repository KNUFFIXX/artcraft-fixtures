#!/usr/bin/env bash
# Writes the EffectCraft audio fixtures from ffmpeg's built-in test sources (testsrc2, aevalsrc); no camera footage.
# Tested with ffmpeg 4.4. Licence: MIT OR Apache-2.0, like the rest of this repository.
# Video in every file: 320x240 25 fps H.264 (testsrc2).
# The ec_surround51* files: 3 s with a 5.1 track in which each channel plays its own tone in its own time slot
# (-12 dBFS, 0.4 s each): FL 300 Hz at 0.0 s, FR 400 Hz at 0.5 s, C 500 Hz at 1.0 s, LFE 60 Hz at 1.5 s,
# SL 700 Hz at 2.0 s, SR 800 Hz at 2.5 s. A stereo downmix (ITU-R BS.775, LFE left out) has in the left channel
# the bursts at 0.0, 1.0 and 2.0 s, in the right channel those at 0.5, 1.0 and 2.5 s.
set -euo pipefail
cd "$(dirname "$0")"
b() { echo "0.25*sin(2*PI*$1*t)*between(t\\,$2\\,$3)"; }
AE="aevalsrc=$(b 300 0.0 0.4)|$(b 400 0.5 0.9)|$(b 500 1.0 1.4)|$(b 60 1.5 1.9)|$(b 700 2.0 2.4)|$(b 800 2.5 2.9):s=48000"
V="-f lavfi -i testsrc2=size=320x240:rate=25"
VC="-c:v libx264 -preset veryfast -pix_fmt yuv420p"

# 1. E-AC-3: 5.1 in MP4 and in Matroska; stereo in MP4 (FL tone at 0.0 s, FR tone at 0.5 s)
ffmpeg -v error -y $V -f lavfi -i "$AE:c=5.1(side)" -t 3 $VC -c:a eac3 -b:a 384k ec_surround51_eac3.mp4
ffmpeg -v error -y -i ec_surround51_eac3.mp4 -c copy ec_surround51_eac3.mkv
ffmpeg -v error -y $V -f lavfi -i "aevalsrc=$(b 300 0.0 0.4)|$(b 400 0.5 0.9):s=48000:c=stereo" -t 3 $VC -c:a eac3 -b:a 192k ec_stereo_eac3.mp4

# 2. AC-3 5.1 in MP4, with the same stream in MOV and in Matroska as controls
ffmpeg -v error -y $V -f lavfi -i "$AE:c=5.1(side)" -t 3 $VC -c:a ac3 -b:a 384k ec_surround51_ac3.mp4
ffmpeg -v error -y -i ec_surround51_ac3.mp4 -c copy ec_surround51_ac3.mov
ffmpeg -v error -y -i ec_surround51_ac3.mp4 -c copy ec_surround51_ac3.mkv
# AAC 5.1 in the 5.1(side) layout: ffmpeg writes it with a program config element (channel configuration 0)
ffmpeg -v error -y $V -f lavfi -i "$AE:c=5.1(side)" -t 3 $VC -c:a aac -b:a 384k ec_surround51side_aac_pce.mp4

# 3. AAC in Matroska (block timestamps in whole milliseconds; an AAC frame lasts 21.33 ms at 48 kHz):
#    a steady 440 Hz tone (stereo, 6 s) and the 5.1 channel test (channel configuration 6), each with the same stream in MP4 as control
ffmpeg -v error -y $V -f lavfi -i "aevalsrc=0.25*sin(2*PI*440*t)|0.25*sin(2*PI*440*t):s=48000" -t 6 $VC -c:a aac -b:a 192k ec_aac_tone440.mp4
ffmpeg -v error -y -i ec_aac_tone440.mp4 -c copy ec_aac_tone440.mkv
ffmpeg -v error -y $V -f lavfi -i "$AE:c=5.1" -t 3 $VC -c:a aac -b:a 384k ec_surround51_aac.mp4
ffmpeg -v error -y -i ec_surround51_aac.mp4 -c copy ec_surround51_aac.mkv
