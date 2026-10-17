#!/usr/bin/env python3
"""make_fixtures_soundcraft.py - synthetic fixtures for SoundCraft import reports (Python standard library + ffmpeg).

Writes into the current folder:
  tone_mono_48k.wav     1.000 s, 48 kHz, mono, 16-bit: 440 Hz tone at -12 dBFS with a one-sample click (+0.9) at sample 24000
  tone_51_48k.wav       1.000 s, 48 kHz, 6 channels (5.1, WAVE_FORMAT_EXTENSIBLE), a different tone per channel, same click on every channel
  aac_priming.m4a       tone_mono_48k.wav as AAC-LC in MP4 (ffmpeg's native encoder writes an edit list that skips its 1024-sample encoder delay)
  aac_51.m4a            tone_51_48k.wav as 6-channel AAC-LC in MP4
  ac3_51.ac3            tone_51_48k.wav as AC-3 (raw elementary stream)
  eac3_51.eac3          tone_51_48k.wav as E-AC-3 (raw elementary stream)
  noise_left_44k.wav    3.000 s, 44.1 kHz, stereo, 16-bit: white noise (-9 dBFS RMS, seeded) on the left channel, digital silence on the right
  mp3_mf320_left.mp3    noise_left_44k.wav as 320 kbps MP3 from the Windows Media Foundation MP3 encoder (ffmpeg -c:a mp3_mf, Windows only;
                        no Xing/Info frame, no ID3): in many frames the left channel uses all main data and the last right-channel
                        granule is empty (part2_3_length 0)
Usage: python make_fixtures_soundcraft.py [path to ffmpeg]   (tested with ffmpeg 9.0.2)
"""
import math
import struct
import subprocess
import sys
import wave

SR = 48000
N = SR
CLICK = 24000


def write_wav(path, chans):
    nch = len(chans)
    frames = bytearray()
    for i in range(N):
        for c in range(nch):
            frames += struct.pack('<h', max(-32768, min(32767, int(round(chans[c][i] * 32767)))))
    if nch <= 2:
        with wave.open(path, 'wb') as w:
            w.setnchannels(nch)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes(bytes(frames))
        return
    # WAVE_FORMAT_EXTENSIBLE with the 5.1 channel mask (FL FR FC LFE BL BR = 0x3F)
    fmt = struct.pack('<HHIIHHHHIH14s', 0xFFFE, nch, SR, SR * nch * 2, nch * 2, 16, 22, 16, 0x3F, 1,
                      b'\x00\x00\x00\x00\x10\x00\x80\x00\x00\xaa\x00\x38\x9b\x71')
    body = b'WAVE' + b'fmt ' + struct.pack('<I', len(fmt)) + fmt + b'data' + struct.pack('<I', len(frames)) + bytes(frames)
    with open(path, 'wb') as f:
        f.write(b'RIFF' + struct.pack('<I', len(body)) + body)


def tone(freq, amp=0.25):
    x = [amp * math.sin(2 * math.pi * freq * i / SR) for i in range(N)]
    x[CLICK] = 0.9
    return x


def noise_left():
    import random
    sr = 44100
    rnd = random.Random(11)
    frames = bytearray()
    for i in range(3 * sr):
        v = max(-1.0, min(1.0, rnd.gauss(0.0, 0.35)))
        frames += struct.pack('<hh', int(round(v * 32767)), 0)
    with wave.open('noise_left_44k.wav', 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(bytes(frames))


def main():
    ff = sys.argv[1] if len(sys.argv) > 1 else 'ffmpeg'
    write_wav('tone_mono_48k.wav', [tone(440.0)])
    write_wav('tone_51_48k.wav', [tone(f) for f in (220.0, 330.0, 495.0, 55.0, 660.0, 990.0)])
    common = [ff, '-v', 'error', '-y', '-nostdin']
    flags = ['-map_metadata', '-1', '-fflags', '+bitexact', '-flags:a', '+bitexact']
    subprocess.run(common + ['-i', 'tone_mono_48k.wav', '-c:a', 'aac', '-b:a', '96k'] + flags + ['aac_priming.m4a'], check=True)
    subprocess.run(common + ['-i', 'tone_51_48k.wav', '-c:a', 'aac', '-b:a', '384k'] + flags + ['aac_51.m4a'], check=True)
    subprocess.run(common + ['-i', 'tone_51_48k.wav', '-c:a', 'ac3', '-b:a', '448k'] + flags + ['ac3_51.ac3'], check=True)
    subprocess.run(common + ['-i', 'tone_51_48k.wav', '-c:a', 'eac3', '-b:a', '384k'] + flags + ['eac3_51.eac3'], check=True)
    noise_left()
    if sys.platform == 'win32':
        subprocess.run(common + ['-i', 'noise_left_44k.wav', '-c:a', 'mp3_mf', '-b:a', '320k', '-write_xing', '0', '-id3v2_version', '0']
                       + flags + ['mp3_mf320_left.mp3'], check=True)
    print('ok')


if __name__ == '__main__':
    main()
