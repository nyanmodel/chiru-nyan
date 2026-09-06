import { openSync, writeSync, closeSync } from 'node:fs';

export const SAMPLE_RATE = 48000;
export const FRAME_BYTES = 4; // stereo, signed 16-bit little endian
export const MAX_PCM_BYTES = 30 * SAMPLE_RATE * FRAME_BYTES;

export function wavHeader(bytes) {
  const header = Buffer.alloc(44);
  header.write('RIFF', 0);
  header.writeUInt32LE(36 + bytes, 4);
  header.write('WAVEfmt ', 8);
  header.writeUInt32LE(16, 16);
  header.writeUInt16LE(1, 20);
  header.writeUInt16LE(2, 22);
  header.writeUInt32LE(SAMPLE_RATE, 24);
  header.writeUInt32LE(SAMPLE_RATE * FRAME_BYTES, 28);
  header.writeUInt16LE(FRAME_BYTES, 32);
  header.writeUInt16LE(16, 34);
  header.write('data', 36);
  header.writeUInt32LE(bytes, 40);
  return header;
}

function writeAll(fd, buffer, position) {
  let offset = 0;
  while (offset < buffer.length) {
    const written = writeSync(fd, buffer, offset, buffer.length - offset, position + offset);
    if (!written) throw new Error('音声ファイルへの書き込みが停止しました。');
    offset += written;
  }
}

export class WavTrack {
  constructor(path, limit = MAX_PCM_BYTES) {
    this.fd = openSync(path, 'wx', 0o600);
    this.bytes = 0;
    this.limit = limit;
    this.packets = [];
    writeAll(this.fd, wavHeader(0), 0);
  }
  append(pcm, offsetMs) {
    if (this.fd === null) throw new Error('録音終了済みです。');
    if (pcm.length % FRAME_BYTES) throw new Error('PCMのフレーム境界が不正です。');
    if (this.bytes + pcm.length > this.limit) throw new Error('音声サイズ上限に達しました。');
    writeAll(this.fd, pcm, 44 + this.bytes);
    this.packets.push({ offsetMs, byteOffset: this.bytes, pcmBytes: pcm.length });
    this.bytes += pcm.length;
    // Keep already-written audio playable even if the process is interrupted.
    writeAll(this.fd, wavHeader(this.bytes), 0);
  }
  close() {
    if (this.fd === null) return;
    closeSync(this.fd);
    this.fd = null;
  }
}
