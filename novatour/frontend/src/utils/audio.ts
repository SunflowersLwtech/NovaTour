/**
 * Audio utilities for PCM capture and playback.
 * Captures mic at browser rate, resamples to 16kHz PCM, sends as base64.
 * Plays back 16kHz PCM from backend.
 */

export function pcmToBase64(pcmData: Int16Array): string {
  const bytes = new Uint8Array(pcmData.buffer);
  let binary = "";
  for (let i = 0; i < bytes.length; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

export function base64ToPcm(b64: string): Float32Array {
  const binary = atob(b64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  const int16 = new Int16Array(bytes.buffer);
  const float32 = new Float32Array(int16.length);
  for (let i = 0; i < int16.length; i++) {
    float32[i] = int16[i] / 32768;
  }
  return float32;
}

/**
 * Resample audio from source rate to target rate using linear interpolation.
 */
export function resample(
  input: Float32Array,
  srcRate: number,
  targetRate: number
): Float32Array {
  if (srcRate === targetRate) return input;
  const ratio = srcRate / targetRate;
  const outputLength = Math.round(input.length / ratio);
  const output = new Float32Array(outputLength);
  for (let i = 0; i < outputLength; i++) {
    const srcIndex = i * ratio;
    const low = Math.floor(srcIndex);
    const high = Math.min(low + 1, input.length - 1);
    const frac = srcIndex - low;
    output[i] = input[low] * (1 - frac) + input[high] * frac;
  }
  return output;
}

/**
 * Convert Float32Array audio to Int16Array PCM.
 */
export function float32ToInt16(input: Float32Array): Int16Array {
  const output = new Int16Array(input.length);
  for (let i = 0; i < input.length; i++) {
    const s = Math.max(-1, Math.min(1, input[i]));
    output[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
  }
  return output;
}

/**
 * Play PCM audio data through AudioContext.
 */
export class AudioPlayer {
  private context: AudioContext | null = null;
  private nextStartTime = 0;

  async init() {
    this.context = new AudioContext({ sampleRate: 16000 });
    this.nextStartTime = this.context.currentTime;
  }

  play(samples: Float32Array) {
    if (!this.context) return;

    const buffer = this.context.createBuffer(1, samples.length, 16000);
    buffer.getChannelData(0).set(samples);

    const source = this.context.createBufferSource();
    source.buffer = buffer;
    source.connect(this.context.destination);

    const now = this.context.currentTime;
    const startTime = Math.max(now, this.nextStartTime);
    source.start(startTime);
    this.nextStartTime = startTime + buffer.duration;
  }

  clearBuffer() {
    if (this.context) {
      this.nextStartTime = this.context.currentTime;
    }
  }

  async close() {
    if (this.context) {
      await this.context.close();
      this.context = null;
    }
  }
}
