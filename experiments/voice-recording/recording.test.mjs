import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import OpusScript from 'opusscript';
import { WavTrack } from './wav.mjs';
import { config } from './config.mjs';

function fixture(t) {
  const dir = mkdtempSync(join(tmpdir(), 'chiru-audio-'));
  t.after(() => rmSync(dir, { recursive: true, force: true }));
  return join(dir, 'voice.wav');
}

test('Opus音声をデコードし、再生可能なステレオPCM WAVを生成する', t => {
  const path = fixture(t);
  const encoder = new OpusScript(48000, 2, OpusScript.Application.AUDIO);
  const decoder = new OpusScript(48000, 2, OpusScript.Application.AUDIO);
  const wav = new WavTrack(path);
  t.after(() => { wav.close(); encoder.delete(); decoder.delete(); });
  const pcm = Buffer.alloc(960 * 4);
  for (let frame = 0; frame < 960; frame++) {
    const sample = Math.round(12000 * Math.sin(2 * Math.PI * 440 * frame / 48000));
    pcm.writeInt16LE(sample, frame * 4);
    pcm.writeInt16LE(sample, frame * 4 + 2);
  }
  for (let i = 0; i < 10; i++) wav.append(decoder.decode(encoder.encode(pcm, 960)), i * 20);
  wav.close();
  const file = readFileSync(path);
  assert.equal(file.toString('ascii', 0, 4), 'RIFF');
  assert.equal(file.toString('ascii', 8, 16), 'WAVEfmt ');
  assert.equal(file.readUInt32LE(4), file.length - 8);
  assert.equal(file.readUInt32LE(40), 38400);
  assert.equal(file.readUInt16LE(22), 2);
  assert.equal(file.readUInt32LE(24), 48000);
  assert.equal(file.readUInt16LE(34), 16);
  assert.ok(file.subarray(44).some(byte => byte !== 0));
  assert.equal(wav.packets.length, 10);
});

test('無音区間を時刻メタデータに残し、書き込み済みヘッダを更新する', t => {
  const path = fixture(t);
  const wav = new WavTrack(path);
  t.after(() => wav.close());
  wav.append(Buffer.alloc(3840), 100);
  wav.append(Buffer.alloc(3840), 5000);
  assert.deepEqual(wav.packets.map(p => [p.offsetMs, p.byteOffset]), [[100, 0], [5000, 3840]]);
  assert.equal(readFileSync(path).readUInt32LE(40), 7680);
});

test('サイズ超過時にもそれまでの音声を保持し、終了は二重に実行できる', t => {
  const path = fixture(t);
  const wav = new WavTrack(path, 8);
  t.after(() => wav.close());
  wav.append(Buffer.alloc(8), 0);
  assert.throws(() => wav.append(Buffer.alloc(4), 20), /上限/);
  assert.throws(() => wav.append(Buffer.alloc(1), 20), /フレーム/);
  wav.close();
  wav.close();
  assert.equal(readFileSync(path).length, 52);
  assert.throws(() => wav.append(Buffer.alloc(4), 30), /終了済み/);
  assert.throws(() => new WavTrack(path), /EEXIST/);
});

test('設定不足・不正なIDでは接続前に失敗する', () => {
  assert.throws(() => config({}), /CHIRU_TEST_TOKEN/);
  const env = { CHIRU_TEST_TOKEN: 'test-placeholder', TEST_GUILD_ID: '12345678901234567', TEST_USER_ID: '12345678901234568' };
  assert.equal(config(env).userId, env.TEST_USER_ID);
  assert.throws(() => config({ ...env, TEST_GUILD_ID: '../path' }), /Discord ID/);
});
