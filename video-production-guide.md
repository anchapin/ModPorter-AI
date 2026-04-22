# Video Production Guide

Complete guide for recording and producing ModPorter AI tutorial videos.

## Quick Start

**Total time**: 2-3 hours (first video), 1 hour (subsequent)
**Skill level**: Intermediate (familiar with screen recording and basic editing)

### Equipment Checklist

**Minimum (Free)**:
- Computer with 1920x1080 display
- Built-in microphone or USB mic ($20-50)
- OBS Studio (free)
- DaVinci Resolve (free) or iMovie (Mac)

**Recommended (Professional)**:
- 4K monitor
- Shure SM7B microphone ($400)
- Focusrite Scarlett interface ($150)
- OBS Studio
- Adobe Premiere Pro or Final Cut Pro

## Recording Setup

### 1. OBS Studio Configuration

**Video Settings**:
- Resolution: 3840x2160 (4K) or 1920x1080 (1080p)
- Frame rate: 60 FPS
- Codec: NVIDIA NVENC H.264 (or x264 if no GPU)
- Bitrate: 20 Mbps (4K), 8 Mbps (1080p)

**Audio Settings**:
- Sample rate: 48 kHz
- Channels: Stereo
- Bitrate: 320 kbps
- Track 1: System audio
- Track 2: Microphone

### 2. Screen Preparation

**Before Recording**:
1. Clean desktop (remove personal files)
2. Set desktop background (solid color or branded)
3. Organize browser tabs (close unnecessary ones)
4. Clear browser cache and cookies
5. Disable notifications (Do Not Disturb mode)
6. Set display to 4K resolution (if available)

**Browser Setup**:
1. Open portkit.cloud
2. Log in to your account
3. Open DevTools (F12) for demos
4. Set zoom to 100%
5. Hide bookmarks bar
6. Install Full Page Screen Capture extension

### 3. Microphone Setup

**Positioning**:
- Distance: 6-8 inches from mouth
- Angle: 45 degrees off-axis (reduces plosives)
- Pop filter: 2-3 inches from mic
- Shock mount: Isolate from desk vibrations

**Sound Check**:
1. Open Audacity or QuickTime
2. Record 10 seconds of speech
3. Check for:
   - Clipping (waveform hitting top/bottom)
   - Background noise (hiss, hum)
   - Plosives (popping P/B sounds)
4. Adjust gain as needed

## Recording Process

### Phase 1: Voiceover (30 minutes)

**Script Reading Tips**:
- Read at conversational pace (150 WPM)
- Emphasize key words (bold in script)
- Pause for emphasis (2-3 seconds)
- Smile while speaking (warmth comes through)
- Drink water between takes

**Recording Workflow**:
1. Record entire script (5-6 minutes)
2. Listen back
3. Re-record problem sections
4. Do 3 takes total
5. Select best takes

**File Organization**:
```
project/
├── audio/
│   ├── take-01.wav (best)
│   ├── take-02.wav (backup)
│   └── take-03.wav (backup)
├── video/
│   ├── scene-01-intro.mp4
│   ├── scene-02-problem.mp4
│   └── scene-03-demo.mp4
└── assets/
    ├── logo.svg
    ├── diagrams/
    └── music.mp3
```

### Phase 2: Screen Recordings (60 minutes)

**Scene-by-Scene Recording**:

**Scene 1: Intro (30 seconds)**
- Record Minecraft Java gameplay (2 minutes)
- Record Bedrock gameplay (2 minutes)
- Capture split-screen comparison

**Scene 2: Problem (60 seconds)**
- Show Java code (IntelliJ IDEA or VS Code)
- Scroll through mod files
- Show timeline graphic (use Figma prototype)

**Scene 3: Solution (60 seconds)**
- Record portkit.cloud homepage
- Animate multi-agent diagram (After Effects)
- Show before/after code comparison

**Scene 4: Demo (90 seconds)**
- Upload mod file (drag-and-drop)
- Click through conversion process
- Show progress dashboard
- Review conversion report
- Download .mcaddon file

**Scene 5: Testing (30 seconds)**
- Import .mcaddon in Minecraft Bedrock
- Create test world
- Use `/give` command
- Show item in action

**Scene 6: CTA (30 seconds)**
- Show pricing page
- Display social links
- Fade to logo

**Tips**:
- Use cursor highlight (PointerFocus)
- Smooth mouse movements
- Wait 2 seconds after clicking
- Show keyboard shortcuts
- Record each scene 3 times

### Phase 3: Graphics & Animations (60 minutes)

**Create in Figma**:
1. Multi-agent AI diagram (animated)
2. Before/after code comparison
3. Pricing table screenshot
4. Social icons (Discord, GitHub)
5. Logo variations (color, white, black)

**Export Settings**:
- Format: PNG ( raster), SVG (vector)
- Resolution: 4K (3840x2160)
- Transparent background where needed

## Editing Process

### 1. Rough Cut (2 hours)

**Import to Editor**:
1. Create new project (4K, 60fps)
2. Import all video clips
3. Import audio files
4. Import graphics and music
5. Create bins/folders for organization

**Assembly**:
1. Drag voiceover to timeline (Track 1)
2. Sync video clips to audio
3. Trim clips to match audio
4. Arrange scenes in order
5. Add transitions (0.3-0.5s fade)

**Timeline Structure**:
```
Track 1: Voiceover audio
Track 2: Screen recordings
Track 3: Graphics overlays
Track 4: Background music
Track 5: Sound effects
```

### 2. Fine Cut (1 hour)

**Refine Edits**:
1. Tighten transitions (remove dead air)
2. Add J-cuts and L-cuts (audio overlap)
3. Smooth jump cuts (crossfade 0.2s)
4. Adjust pacing (faster intro, slower demo)
5. Add freeze frames for emphasis

**Visual Enhancements**:
1. Add cursor highlight (yellow circle)
2. Zoom in on important details
3. Add text overlays (key points)
4. Show keyboard shortcuts on screen
5. Add progress bars (conversion demo)

### 3. Audio Mixing (30 minutes)

**Levels**:
- Voiceover: -6 dB (primary)
- Music: -20 dB (background)
- Sound effects: -12 dB (accents)
- System audio: -15 dB (screen recordings)

**Processing**:
- Voiceover: Compressor (4:1 ratio, -20 dB threshold)
- Music: Low-pass filter (reduce high frequencies)
- Sound effects: Reverb (small room)

**Automation**:
- Duck music under voiceover
- Fade music in/out (2 seconds)
- Crossfade between clips

### 4. Color Correction (30 minutes)

**Basic Correction**:
1. White balance (neutral)
2. Exposure (proper brightness)
3. Contrast (enhance details)
4. Saturation (natural colors)

**Stylization** (optional):
- LUT for cinematic look
- Vignette for focus
- Film grain for texture

### 5. Export (30 minutes)

**Settings**:
- Format: H.264
- Resolution: 3840x2160 (4K)
- Frame rate: 60 fps
- Bitrate: 20 Mbps (VBR, 2-pass)
- Audio: AAC, 320 kbps, 48 kHz
- Duration: 5:00

**Create Multiple Versions**:
- 4K master (YouTube, Vimeo)
- 1080p (social media)
- 720p (mobile)
- GIF snippets (social media)

## Publishing

### 1. YouTube Upload

**Metadata**:
- Title: "Convert Java Mods to Bedrock in Minutes 🎮 ModPorter AI Tutorial"
- Description: [Full description with links]
- Tags: #Minecraft #Bedrock #Modding #Java #AI #Tutorial
- Thumbnail: Eye-catching comparison
- Category: Gaming → Tutorials
- License: Creative Commons (optional)

**Optimization**:
- Add timestamps (0:00, 0:30, etc.)
- Enable captions (auto-generate + edit)
- Add end screen (subscribe button)
- Add cards (related videos)
- Pin important comment

**Upload Schedule**:
- Tuesday-Thursday (best days)
- 3-5 PM (peak viewing)
- Schedule in advance ( consistency)

### 2. Social Media

**Twitter**:
- 30-second highlight clip
- GIF of conversion demo
- Thread with key points
- Link to full video
- Hashtags: #Minecraft #Bedrock

**TikTok**:
- 60-second fast-paced version
- Trending music
- Text overlays
- Call to action
- Link in bio

**Reddit**:
- Post to r/Minecraft
- Post to r/Bedrock
- Post to r/FeedtheBeast
- Engage with comments

**Discord**:
- Pin in #announcements
- Share in #general
- Ask for feedback
- Respond to comments

### 3. Website Embed

**Places to Embed**:
- Homepage (autoplay muted)
- Documentation pages
- Blog posts
- Pricing page
- Help center

**Embed Code**:
```html
<iframe
  width="560"
  height="315"
  src="https://www.youtube.com/embed/VIDEO_ID"
  frameborder="0"
  allow="accelerometer; autoplay; clipboard-write;
    encrypted-media; gyroscope; picture-in-picture"
  allowfullscreen>
</iframe>
```

## Promotion

### Launch Day (Day 0)

- [ ] Upload to YouTube (scheduled)
- [ ] Post to Twitter (3x throughout day)
- [ ] Post to Reddit (2-3 subreddits)
- [ ] Share in Discord (ping @everyone)
- [ ] Send email newsletter
- [ ] Update website homepage

### Week 1

- [ ] Respond to all comments
- [ ] Create additional clips (shorts)
- [ ] Share on LinkedIn
- [ ] Submit to Minecraft communities
- [ ] Monitor analytics daily

### Month 1

- [ ] Create follow-up videos
- [ ] Compile viewer questions (FAQ video)
- [ ] Share behind-the-scenes content
- [ ] Run YouTube ads (optional)
- [ ] Update based on feedback

## Analytics Tracking

### YouTube Studio

**Metrics to Track**:
- Views (target: 10,000+ in 30 days)
- Watch time (target: 50%+ average)
- Click-through rate (target: 5%+)
- Subscriber conversion (target: 500+)
- Engagement (likes, comments, shares)

**Reports**:
- Daily: Check views and comments
- Weekly: Review retention graph
- Monthly: Comprehensive analysis

### Website Analytics

**Metrics to Track**:
- Traffic increase (target: 30%)
- Sign-ups (target: 100+ new users)
- Conversions (target: 20+ Pro upgrades)
- Video play rate (target: 40%+)

**Tools**:
- Google Analytics
- Hotjar (heatmaps)
- Mixpanel (funnels)

## Troubleshooting

### Audio Issues

**Problem**: Audio is too quiet
- **Fix**: Normalize audio to -3 dB in editing

**Problem**: Background noise
- **Fix**: Use noise reduction plugin (Audacity)

**Problem**: Popping sounds
- **Fix**: Use pop filter or move mic off-axis

### Video Issues

**Problem**: Blurry text
- **Fix**: Record at 4K, use sharper fonts

**Problem**: Laggy cursor
- **Fix**: Higher frame rate (60 fps)

**Problem**: Screen flicker
- **Fix**: Disable window animations

### Export Issues

**Problem**: File too large
- **Fix**: Lower bitrate or use 1080p

**Problem**: Export takes too long
- **Fix**: Use GPU acceleration (NVENC)

**Problem**: Quality loss
- **Fix**: Use VBR 2-pass encoding

## Budget Breakdown

### DIY Approach (Free)

| Item | Cost |
|------|------|
| OBS Studio | $0 |
| DaVinci Resolve | $0 |
| USB Microphone | $50 |
| Pop filter | $15 |
| Shock mount | $25 |
| **Total** | **$90** |

### Professional Setup

| Item | Cost |
|------|------|
| Shure SM7B mic | $400 |
| Focusrite Scarlett | $150 |
| Adobe Premiere Pro | $240/year |
| Stock music | $15/month |
| Graphics designer | $500 |
| **Total** | **$1,305 + $15/month** |

### Outsourced Production

| Service | Cost |
|---------|------|
| Freelance video producer | $2,000-5,000 |
| Voiceover artist | $200-500 |
| Motion graphics | $500-1,000 |
| **Total** | **$2,700-6,500** |

## Resources

### Tools

- **Screen Recording**: OBS Studio, Camtasia
- **Audio Editing**: Audacity, Adobe Audition
- **Video Editing**: DaVinci Resolve, Premiere Pro, Final Cut Pro
- **Motion Graphics**: After Effects, Blender
- **Thumbnail Design**: Canva, Figma

### Learning

- **YouTube Tutorials**: Search "video editing tutorial"
- **Courses**: Udemy, Skillshare, LinkedIn Learning
- **Communities**: r/videoediting, r/NewTubers

### Assets

- **Music**: Epidemic Sound, Artlist, YouTube Audio Library
- **Sound Effects**: Freesound.org, Zapsplat
- **Stock Footage**: Pexels, Mixkit, Pixabay
- **Icons**: Flaticon, Noun Project

---

**Need help?** Contact video@portkit.cloud or join our Discord community.
