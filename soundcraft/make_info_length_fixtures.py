# make_info_length_fixtures.py - synthetic SoundCraft fixture: AAC-LC in MP4 whose last sample has a longer stts duration.
# Needs ffmpeg/ffprobe (tested with 7.1.1) and the Python 3 standard library. Usage: python make_info_length_fixtures.py <outdir>
#  fx_m4a_lastdur.m4a  10 s 48 kHz stereo AAC-LC (330 Hz sine) in MP4; the last sample has an stts duration of 1145 instead of 1024
#                      (as phone recorders write it: the last audio sample lasts until the track end); remux only, no re-encode,
#                      no edit list, so a decoder yields exactly packets x 1024 frames (470 x 1024 = 481,280)
import os, sys, subprocess, shutil
FFM = shutil.which('ffmpeg'); FFP = shutil.which('ffprobe')
out = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
BE = ['-map_metadata', '-1', '-fflags', '+bitexact', '-flags:a', '+bitexact']
def ff(args):
    subprocess.run([FFM, '-v', 'error', '-nostdin', '-y'] + args, check=True)
p = lambda n: os.path.join(out, n)
# MP4 with a longer last stts entry
tmp = p('_tmp_aac.m4a')
ff(['-f', 'lavfi', '-i', 'sine=f=330:sample_rate=48000:duration=10', '-ac', '2', '-c:a', 'aac', '-b:a', '160k'] + BE + [tmp])
n = int(subprocess.run([FFP, '-v', 'error', '-select_streams', 'a:0', '-count_packets', '-show_entries', 'stream=nb_read_packets', '-of', 'csv=p=0', tmp],
                       capture_output=True, text=True, check=True).stdout.strip())
ff(['-i', tmp, '-c:a', 'copy', '-bsf:a', 'setts=duration=if(eq(N\\,%d)\\,1145\\,DURATION)' % (n - 1)] + BE + ['-use_editlist', '0', p('fx_m4a_lastdur.m4a')])
os.remove(tmp)
print('ok', n)
