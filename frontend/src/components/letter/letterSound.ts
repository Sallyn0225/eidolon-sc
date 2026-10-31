import { api } from "@/lib/api";
import { musicPlan, segmentsFrom, type LetterMusic, type MusicSegment } from "@/lib/letter";

/** 配乐的音量（她的声音是 1）：她念的时候压低，念完起来。音量在验收时调。 */
const MUSIC_LEVEL = 0.7;
const MUSIC_UNDER_VOICE = 0.25;
/** 配乐压低、起来、开头渐入的时间常数（秒，`setTargetAtTime`）。 */
const MUSIC_EASE = 0.4;
/** 配乐淡出多久（秒）。 */
const MUSIC_FADE = 3;

/**
 * 一封信的声音（GLOSSARY.md「信」）：她念信的声音，一块一个 mp3（第 0 块是抬头，之后每段一块），和底下的配乐。
 * 信封一出来就开始取；拆开那一下（`unlock`，要在点击里调，浏览器才让它出声）建 Web Audio 的上下文、解码语音，
 * 得到每块的时长，拿去排时间轴；信纸展开后按时间轴把每块排在音频时钟上（`play`），字跟着音频时钟写（lib/letter 的 `tick`）。
 * 配乐和语音接在同一个总音量后面，静音键一起静掉；按签名时刻对齐（lib/letter 的 `musicPlan`），解码得晚就从那一秒接着放，
 * 晚过签名就不放了；取不到、解码不了时安静地没有配乐。
 * 整封信的声音都在内存里，放起来以后网络再卡也不会让声音停下；音频时钟停了（被系统打断）由拆信层改按时钟写、`stop`。
 */
export class LetterSound {
  private readonly fetched: Promise<ArrayBuffer[] | null>;
  private readonly fetchedTrack: Promise<ArrayBuffer | null>;
  private context: AudioContext | null = null;
  private gain: GainNode | null = null;
  private buffers: AudioBuffer[] | null = null;
  private decodedTrack: Promise<AudioBuffer | null> = Promise.resolve(null);
  private sources: AudioBufferSourceNode[] = [];
  private isClosed = false;
  /** 停掉过（`stop`）：之后解码好的配乐也不再排上。 */
  private isStopped = false;
  /** 配乐解码好、排上了音频时钟（来晚了、放不了时为 false）。 */
  readonly musicPlaying: Promise<boolean>;
  private resolveMusicPlaying: (isPlaying: boolean) => void = () => {};

  constructor(
    urls: string[] | null,
    /** 这封信的配乐（地址、高潮、淡出、循环段）；没有时为 null。 */
    private readonly track: LetterMusic | null,
  ) {
    this.fetched = urls
      ? Promise.all(
          urls.map(async (url) => {
            const res = await api(url);
            if (!res.ok) throw new Error(`voice ${res.status}`);
            return res.arrayBuffer();
          }),
        ).catch(() => null)
      : Promise.resolve(null);
    // 配乐在立绘素材的存储桶里（跨域、不带凭据）；部署者没上传时 404，就没有配乐。
    this.fetchedTrack = track
      ? fetch(track.url)
          .then((res) => (res.ok ? res.arrayBuffer() : null))
          .catch(() => null)
      : Promise.resolve(null);
    this.musicPlaying = new Promise((resolve) => {
      this.resolveMusicPlaying = resolve;
    });
  }

  /**
   * 拆开：在这一下点击里建音频的上下文，等它跑起来、每块语音都解码好，给出每块的时长（秒）。没有语音、取不到、
   * 解码失败、浏览器不让出声，或者 `waitMs` 毫秒内没好，给 null：不要她的声音了（上下文跑起来了的话配乐照放）。
   * 配乐不等：另外解码，好了再排上。
   */
  unlock(waitMs: number): Promise<number[] | null> {
    if (this.isClosed || typeof AudioContext === "undefined") return Promise.resolve(null);
    let context: AudioContext;
    try {
      context = new AudioContext();
    } catch {
      return Promise.resolve(null);
    }
    this.context = context;
    this.gain = context.createGain();
    this.gain.connect(context.destination);
    this.decodedTrack = this.fetchedTrack
      .then((data) => (data ? context.decodeAudioData(data) : null))
      .catch(() => null);
    const ready = Promise.all([
      context.resume(),
      this.fetched.then((data) => (data ? Promise.all(data.map((d) => context.decodeAudioData(d))) : null)),
    ]).then(([, buffers]) => buffers);
    let timer = 0;
    const late = new Promise<null>((resolve) => {
      timer = window.setTimeout(() => resolve(null), waitMs);
    });
    return Promise.race([ready, late])
      .catch(() => null)
      .then((buffers) => {
        window.clearTimeout(timer);
        this.buffers = buffers;
        return buffers?.map((b) => b.duration) ?? null;
      });
  }

  /**
   * 开口：时间轴的第 0 秒是现在（信纸展开）。有她的声音时（`starts` 不为 null），第 i 块排在第 `starts[i]` 秒放；
   * 配乐按签名在第 `signsAt` 秒、写完在第 `finishesAt` 秒对齐。给出第 0 秒那一刻的音频时钟（秒）；上下文没跑起来、放不了时 null。
   */
  play(starts: number[] | null, signsAt: number, finishesAt: number): number | null {
    const { context, gain, buffers } = this;
    if (this.isClosed || !context || !gain || context.state !== "running") {
      this.resolveMusicPlaying(false);
      return null;
    }
    const base = context.currentTime;
    let speaking: [number, number] | null = null;
    if (starts && buffers) {
      this.sources = buffers.map((buffer, i) => {
        const source = context.createBufferSource();
        source.buffer = buffer;
        source.connect(gain);
        source.start(base + (starts[i] ?? 0));
        return source;
      });
      const last = buffers.length - 1;
      if (last >= 0) speaking = [starts[0] ?? 0, (starts[last] ?? 0) + buffers[last].duration];
    }
    void this.decodedTrack.then((buffer) => {
      const isPlaying = buffer !== null && this.playMusic(buffer, base, speaking, signsAt, finishesAt);
      this.resolveMusicPlaying(isPlaying);
    });
    return base;
  }

  /** 把配乐排上音频时钟（时间轴的第 0 秒在 `base`）；解码得晚就从现在接着放，晚过签名就不放。 */
  private playMusic(
    buffer: AudioBuffer,
    base: number,
    speaking: [number, number] | null,
    signsAt: number,
    finishesAt: number,
  ): boolean {
    const { context, gain, track } = this;
    if (this.isClosed || this.isStopped || !context || !gain || !track || context.state !== "running") return false;
    // 从现在稍后一点起排，免得排在已经过去的时刻上。
    const from = context.currentTime + 0.05 - base;
    if (from >= signsAt) return false;
    const plan = musicPlan(track, signsAt, finishesAt);
    const level = context.createGain();
    level.connect(gain);
    const t = (at: number) => base + Math.max(at, from);
    // 渐入：她还要念（开口前的 1.2 秒也算）就渐入到压低的音量，念完起来；没有她的声音、或者已经念完了就渐入到原本的音量。
    const isSpeaking = speaking !== null && from < speaking[1];
    level.gain.setValueAtTime(0, t(from));
    level.gain.setTargetAtTime(isSpeaking ? MUSIC_UNDER_VOICE : MUSIC_LEVEL, t(from), MUSIC_EASE);
    if (speaking && isSpeaking) level.gain.setTargetAtTime(MUSIC_LEVEL, t(speaking[1]), MUSIC_EASE);
    // 淡出：四个时间常数以后差不多听不见了，再停掉。
    if (plan.fadeAt !== null) level.gain.setTargetAtTime(0, t(plan.fadeAt), MUSIC_FADE / 4);
    for (const segment of segmentsFrom(plan.segments, from)) {
      const source = this.segment(buffer, segment, base, level);
      if (plan.fadeAt !== null) source.stop(base + plan.fadeAt + MUSIC_FADE);
      this.sources.push(source);
    }
    return true;
  }

  private segment(buffer: AudioBuffer, segment: MusicSegment, base: number, to: AudioNode): AudioBufferSourceNode {
    const source = this.context!.createBufferSource();
    source.buffer = buffer;
    source.connect(to);
    if (segment.to === null) source.start(base + segment.at, segment.from);
    else source.start(base + segment.at, segment.from, Math.max(0, segment.to - segment.from));
    return source;
  }

  /** 现在的音频时钟（秒）。 */
  time(): number {
    return this.context?.currentTime ?? 0;
  }

  setMuted(isMuted: boolean): void {
    if (this.gain) this.gain.gain.value = isMuted ? 0 : 1;
  }

  /** 停掉声音：排好的、在放的都停，配乐也是。 */
  stop(): void {
    for (const source of this.sources) {
      try {
        source.stop();
      } catch {
        // 还没 start 过的不会走到这里；已经停了的照样往下走。
      }
    }
    this.sources = [];
    this.isStopped = true;
  }

  /** 在 `ms` 毫秒里淡出，然后关掉。 */
  fadeOut(ms: number): void {
    const { context, gain } = this;
    if (this.isClosed || !context || !gain || ms <= 0) {
      this.close();
      return;
    }
    const now = context.currentTime;
    gain.gain.cancelScheduledValues(now);
    gain.gain.setValueAtTime(gain.gain.value, now);
    gain.gain.linearRampToValueAtTime(0, now + ms / 1000);
    window.setTimeout(() => this.close(), ms);
  }

  /** 停掉声音，放掉音频的上下文。 */
  close(): void {
    if (this.isClosed) return;
    this.isClosed = true;
    this.stop();
    this.resolveMusicPlaying(false);
    void this.context?.close().catch(() => {});
  }
}
