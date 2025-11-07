# Demo GIF Recording Instructions for v0.1.0-MVP

## 30-Second Demo GIF Requirements

### Recording Setup
- **Tool**: Use screen recording software like OBS, LICEcap, or similar
- **Duration**: 30 seconds maximum
- **Resolution**: 1920x1080 or similar high quality
- **Frame Rate**: 30 FPS for smooth playback
- **Output**: Convert to GIF format, optimize for web (< 5MB)

### Demo Flow Script

#### Scene 1: Application Launch (5 seconds)
1. Open browser to `http://localhost:3000`
2. Show the ModPorter AI landing page with upload interface
3. Highlight the "Drag & Drop Java Mod" area

#### Scene 2: File Upload (8 seconds)
1. Drag a sample `.jar` file to the upload area
2. Show file being accepted with visual feedback
3. Display upload progress and file information

#### Scene 3: Conversion Process (10 seconds)
1. Show conversion progress bar with real-time updates
2. Display agent activity logs (JavaAnalyzerAgent, BedrockBuilderAgent)
3. Show progress through different conversion stages

#### Scene 4: Download & Install (7 seconds)
1. Show successful conversion completion
2. Display download button for `.mcaddon` file
3. Quick preview of the generated Bedrock addon structure
4. Show "Ready for Minecraft Bedrock" message

### Key Features to Highlight
- ✅ **Drag & Drop Interface**: Easy file upload
- ✅ **Real-time Progress**: Live conversion tracking
- ✅ **AI Processing**: Multi-agent conversion system
- ✅ **Bedrock Output**: Valid `.mcaddon` file generation
- ✅ **Texture Preservation**: Original textures maintained

### Sample Files for Demo
Use one of the test fixtures:
- `/tests/fixtures/simple_copper_block.jar`
- Any small block mod from test fixtures

### Post-Recording
1. Optimize GIF file size while maintaining quality
2. Add to repository as `demo/mvp-demo.gif`
3. Update README.md to include the demo GIF
4. Consider hosting on GitHub or CDN for better loading

### Recording Checklist
- [ ] Clean desktop/browser (close unnecessary tabs)
- [ ] Clear any previous conversion outputs
- [ ] Ensure good lighting and contrast
- [ ] Test run through the demo flow first
- [ ] Record at consistent speed (not too fast/slow)
- [ ] Include mouse cursor for better user guidance
- [ ] Verify all text is readable in the recording

### Technical Notes
- Record in development environment with docker-compose
- Ensure all services are running and responsive
- Use a representative test mod that showcases core functionality
- Keep file sizes reasonable for web viewing

This demo will showcase the core MVP functionality: converting a simple Java block mod into a functional Bedrock add-on through an intuitive web interface.
