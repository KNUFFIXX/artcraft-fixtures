#!/usr/bin/env bash
# Writes the two 25 fps test clips for the EDL round trip: 640x360, 10 s, a 16-bit barcode of the frame number in the
# top 40 px (clip A: frames 0..249, clip B: 1000..1249), a flat background (A dark, B bright) and a 440/660 Hz tone with
# 1 kHz clicks at 0.5 s, 1.5 s, ... From ffmpeg's built-in sources only. Licence: MIT OR Apache-2.0.
set -euo pipefail
cd "$(dirname "$0")"
for spec in "A:0:60:440:128:128" "B:1000:180:660:168:88"; do
  IFS=: read name off y tone cb cr <<< "$spec"
  ffmpeg -v error -y -f lavfi -i "color=c=black:s=640x360:r=25:d=10,format=yuv420p,geq=lum='if(lt(Y\,40)\,if(mod(floor((N+$off)/pow(2\,floor(X/40)))\,2)\,235\,16)\,$y)':cb=$cb:cr=$cr" \
    -f lavfi -i "aevalsrc=0.1*sin(2*PI*$tone*t)+0.8*sin(2*PI*1000*t)*lt(mod(t-0.5\,1)\,0.01)*gte(t\,0.5):s=48000:c=stereo:d=10" \
    -c:v libx264 -crf 6 -preset veryfast -pix_fmt yuv420p -g 25 -c:a pcm_s16le clip$name.mov
done
