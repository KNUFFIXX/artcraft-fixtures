#!/bin/sh
# Synthetic 30 fps and 60 fps H.264 MP4s whose video track uses a 1000 Hz timescale,
# so frame durations are whole milliseconds (33/34 ms and 16/17 ms), as phone and
# messaging-app exports often are. Each frame shows its frame number and timestamp.
for R in 30 60; do
  ffmpeg -v error -y -f lavfi -i "testsrc2=size=640x360:rate=$R:duration=4" \
    -vf "drawtext=text='frame %{frame_num}  t=%{pts\:hms}':x=20:y=20:fontsize=28:fontcolor=white:box=1:boxcolor=black" \
    -c:v libx264 -pix_fmt yuv420p -g $R -bf 0 -video_track_timescale 1000 ec_fps${R}_ms_timescale.mp4
done
