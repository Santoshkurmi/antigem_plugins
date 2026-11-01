# Audio and captions

## Voice

```json
"audio": {"voice": {"src": "voice.mp3", "words": "voice.words.json", "volume": 1.0, "start": 0}}
```

`start` delays the voice (seconds); word timings shift with it. The words file is JSON
`[{"word": "hello", "start": 0.12, "end": 0.40}, ...]`. A TSV/CSV with `word,start,end` columns also works.

Getting word timings:
- **New voice-over:** `$VS tts script.txt --voice en-US-AndrewNeural --out assets/voice.mp3` (needs `pip install
  edge-tts` and internet) writes `voice.mp3` and `voice.words.json`. Voices include `en-US-AndrewNeural`,
  `en-US-AvaNeural`, `en-GB-RyanNeural`, `en-IN-PrabhatNeural`, `hi-IN-MadhurNeural`, `hi-IN-SwaraNeural`,
  `ne-NP-SagarNeural` and `ne-NP-HemkalaNeural`. `--rate "+10%"` speaks faster.
- **Existing recording:** `$VS align assets/voice.wav --lang en` (needs `pip install faster-whisper`; `--model small`
  is more accurate but slower).
- If the user has another TTS that returns timings, convert its output to the JSON above.

With words available:
- Layer and keyframe cues: `"at": "w:money"`, `"until": "w:money.end+0.2"`.
- Scene ends: `"until": "w:sentence_last_word.end+0.3"`. Scenes then follow the voice exactly.
- `$VS timeline video.json` shows which words fall in each scene. Use it to check the cut points.
- Text `reveal` with `"sync": "voice"`.

## Music

```json
"music": {"src": "music.mp3", "volume": 0.3, "duck": true, "fade_in": 1, "fade_out": 2, "offset": 12, "start": 0, "loop": true}
```

`duck`: `true` or a strength 0.05–1 (lower = ducks more). The music drops automatically while the voice speaks
(sidechain compression). `offset` skips into the track. The music loops and is cut to the video length with a fade-out.
Only use music the user provided or has rights to.

## Beats (cut to the music)

```json
"music": {"src": "song.mp3", "beats": "auto", "volume": 0.8}
```

`beats`: `"auto"` detects tempo and beats once (cached next to the song as `song.beats.json`), or a JSON file of beat
times, or give `"bpm": 120` (+ `"first_beat": 0.35`) when you know the tempo. `$VS beats song.mp3` prints the tempo and
first beats. Then use beat cues anywhere a time is allowed: `"b:9"` (9th beat of the song), `"bar:3"` (first beat of
bar 3, 4 beats per bar), `"nb:2"` (2nd beat after this scene/layer starts), all with offsets (`"b:9-0.05"`).
Scenes can end on beats: `"until": "nb:4"` (4 beats long) or `"until": "bar:5"`. Put camera `punches` and layer
entrances on beats for a montage that hits.

## Sound effects

Anywhere a sound is allowed, `src` can be a file or a **built-in synthesized sound** (no files needed):
`sfx:whoosh` `sfx:swish` `sfx:swoosh_down` `sfx:riser` `sfx:impact` `sfx:boom` `sfx:hit` `sfx:pop` `sfx:click` `sfx:tick`
`sfx:ding` `sfx:chime` `sfx:typing` `sfx:glitch` `sfx:shutter` `sfx:bass_drop` `sfx:pluck` `sfx:heartbeat`
`sfx:drone` (ominous 4 s bed) `sfx:stinger` (horror hit) `sfx:sub_hit` `sfx:scribble` (pencil) `sfx:paper` `sfx:coin`
`sfx:buzz` (wrong) `sfx:success` (right) and 8-bit `sfx:jump8` `sfx:coin8` `sfx:power8` `sfx:blip8` `sfx:hit8`.

- On a layer (plays when it starts): `"sfx": "sfx:pop"` or `{"src": "sfx:whoosh", "volume": 0.5, "offset": -0.1}`.
  A negative offset lets a whoosh lead into the motion.
- On the timeline: `"audio": {"sfx": [{"src": "sfx:impact", "at": "w:boom", "volume": 0.8}, {"src": "click.wav",
  "at": {"scene": "intro", "t": 1.2}}, {"src": "sfx:riser", "at": 12.0, "trim": [0, 1.5]}]}`.
- Video layers with `"audio": true` add their own sound (`volume`).

Sound design rules: whoosh/swish on fast moves and transitions, pop on stickers and icons, hit/impact on reveals and
stamps, typing under typewriter text, riser before a big reveal, ding/chime on positive results. Keep SFX volume
0.3–0.7 under a voice. Don't put a sound on every layer; 1–3 per scene is plenty.

The final mix is limited and normalized to about −14 LUFS (social media loudness). Set `"loudness": false` in `audio`
to skip normalization.

## Captions

```json
"captions": {"style": "karaoke", "max_words": 4, "max_chars": 24, "y": "70%", "font": "display", "size": 70}
```

| style | look |
|---|---|
| `karaoke` | white words, the spoken word turns yellow, slight pop |
| `box` | uppercase; the spoken word sits on a colored box (`active_box`) |
| `pop` | words pop in one by one as spoken |
| `clean` | the whole phrase, no highlight |
| `single` | one big word at a time (TikTok style) |
| `minimal` | small, quiet, documentary |

Keys: `style`, `font`, `size`, `color`, `active_color`, `active_box` (color or `{"color", "padding", "radius"}`),
`stroke_width`, `stroke_color`, `uppercase`, `x`, `y` (default 70 % of the height for vertical, 84 % for horizontal),
`max_width` ("86%"), `max_words`, `max_chars`, `max_lines` (2), `plate` (a box behind the phrase), `shadow` (true/false
or a spec), `pop` (false stops the active-word bump), `line_height`, `weight`, `enabled`.

Captions are drawn above everything and don't move with the camera. Hide them in one scene with `"captions": false`
in that scene. Keep other text out of the caption band. `inspect` warns when text overlaps the captions.
