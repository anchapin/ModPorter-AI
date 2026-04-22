# Frequently Asked Questions

Everything you need to know about Portkit, from basic usage to advanced features.

## General Questions

### 1. What is Portkit?

Portkit is the first AI-powered tool that converts Minecraft Java Edition mods to Bedrock Edition add-ons automatically. It uses advanced multi-agent AI systems to analyze Java code, translate it to JavaScript (Bedrock Script API), convert assets, and package everything into a ready-to-use .mcaddon file.

**Key benefits**:
- Saves 3-6 months of manual rewriting
- 60-80% automation for most mods
- Supports complex features (entities, dimensions, GUI)
- Continuous learning from community conversions

### 2. How accurate is the conversion?

Accuracy depends on mod complexity:

| Mod Type | Accuracy | Manual Work |
|----------|----------|-------------|
| Simple items/blocks | 95%+ | 0-1 hours |
| Moderate (entities, recipes) | 80-90% | 2-5 hours |
| Complex (custom logic, GUI) | 60-80% | 5-20 hours |
| Very complex (dimensions, networking) | 40-60% | 20+ hours |

The AI improves with each conversion, learning from manual corrections.

### 3. What Java editions are supported?

**Supported**:
- Minecraft Forge (1.12.2 - 1.20.x)
- Fabric (1.14+)
- Quilt (experimental)
- Vanilla mods (no loader)

**Not supported**:
- Rift, LiteLoader (older loaders)
- Highly obfuscated mods
- Mods with native libraries (JNI)

### 4. What Bedrock features are supported?

**Fully supported**:
- Items, blocks, entities
- Recipes, loot tables
- Textures, models, sounds
- Script API (JavaScript)
- Components system

**Partially supported**:
- Custom GUI (needs manual work)
- Network packets (Script API workaround)
- Custom rendering (manual Bedrock implementation)
- Dimensions (experimental features)

**Not supported**:
- Native code mods
- Server-side only mods
- Some client-side rendering

### 5. Is this against Minecraft EULA?

No. Portkit:
- Does not modify Minecraft's code
- Creates original add-on content
- Respects Mojang's Terms of Use
- Requires you to own Minecraft Bedrock

**Important**: You own the converted add-on, but must respect the original mod's license.

## Pricing and Limits

### 6. Is Portkit free?

We have a **freemium model**:

**Free Tier**:
- 5 conversions per month
- Simple to moderate mods
- Community support (Discord)
- Basic conversion reports

**Pro Tier** ($9.99/month or $99/year):
- Unlimited conversions
- Complex mods (entities, dimensions)
- Priority support (24hr response)
- Advanced features (API, batch processing)
- Visual editor access

**Studio Tier** ($29.99/month):
- Everything in Pro
- Team collaboration (10 seats)
- API access (1,000 calls/month)
- Custom templates
- White-label options

**Enterprise** (Custom):
- On-premise deployment
- Unlimited API access
- Dedicated support
- SLA guarantees (99.9% uptime)

### 7. What are the file size limits?

| Plan | Max File Size | Storage |
|------|---------------|---------|
| Free | 100MB | 1GB |
| Pro | 500MB | 10GB |
| Studio | 2GB | 100GB |
| Enterprise | Unlimited | Unlimited |

### 8. Can I cancel my subscription?

Yes. Cancel anytime from your account settings:
- Access until billing period ends
- No refunds for partial months
- Re-subscribe anytime
- Data retained for 30 days after cancellation

## Usage Questions

### 9. How long does conversion take?

Depends on mod complexity:

| Mod Size | Files | Time |
|----------|-------|------|
| Small | <50 files | 2-5 minutes |
| Medium | 50-500 files | 5-15 minutes |
| Large | 500-2000 files | 15-30 minutes |
| Very Large | 2000+ files | 30+ minutes |

**Factors affecting time**:
- Code complexity
- Number of assets
- Server load (peak hours slower)
- Your plan priority (Pro users get priority)

### 10. What happens if conversion fails?

You'll see a detailed error report:
- **What failed** (specific file/feature)
- **Why it failed** (error explanation)
- **How to fix it** (suggested solutions)
- **Retry options** (fix and re-upload)

**Common fixes**:
- Deobfuscate Java code
- Include missing dependencies
- Split large mods into parts
- Use simpler mod version

### 11. Can I edit the converted files?

Yes! The .mcaddon file is just a ZIP archive:

**To edit**:
1. Extract .mcaddon (it's a ZIP)
2. Edit JSON/JavaScript files
3. Re-package as .mcaddon
4. Or use our Visual Editor (Pro feature)

**Common edits**:
- Adjust damage values
- Fix texture paths
- Tweak crafting recipes
- Add custom behaviors

### 12. Do I need to know JavaScript?

**For simple conversions**: No
- Items, blocks, recipes work automatically
- AI generates all JavaScript

**For complex features**: Yes (helpful)
- Custom behaviors
- Entity AI
- Script API events

**Resources**:
- [Bedrock Script API Docs](https://wiki.bedrock.dev/documents/scriptapi.html)
- Our interactive tutorials
- Community examples

### 13. Can I convert mods I didn't create?

**Legal considerations**:
- You must respect the original mod's license
- MIT/Apache: Usually OK to convert
- Custom license: Check permissions
- All rights reserved: Contact author

**Best practices**:
- Credit original mod author
- Link to original mod
- Don't monetize without permission
- Check license on Modrinth/CurseForge

## Technical Questions

### 14. What Java version is required?

None! Portkit:
- Accepts compiled .jar files
- No Java installation needed
- Works on any device with a browser
- Server-side processing (your device doesn't do the work)

**For developers**:
- Java 8+ syntax supported
- Java 17+ features (experimental)
- Records, enums (partial support)

### 15. What's the difference between .mcaddon, .mcpack, .zip?

| Format | Use Case | Contents |
|--------|----------|----------|
| .mcaddon | Complete add-on | Behavior + Resource packs |
| .mcpack | Single pack | Behavior OR resource pack |
| .zip | Archive | Any files |

**Portkit exports**: .mcaddon (complete add-on)

**For distribution**: .mcaddon is recommended (auto-installs)

### 16. Can I convert Fabric mods to Forge?

No. Portkit only converts:
- Java Edition → Bedrock Edition
- Forge/Fabric → Bedrock Script API

**For Forge ↔ Fabric**: Use other tools like:
- [Fabric2Forge](https://github.com/FabricMC/fabric2forge)
- [ForgeTranslator](https://github.com/MinecraftForge/ForgeTranslator)

### 17. How does the AI work?

**Multi-agent system**:

1. **Java Analyzer Agent**
   - Parses Java code (Tree-sitter AST)
   - Builds data flow graphs
   - Identifies patterns

2. **Bedrock Architect Agent**
   - Designs Bedrock conversion strategy
   - Maps Java features to Bedrock equivalents
   - Identifies incompatibilities

3. **Logic Translator Agent**
   - Converts Java → JavaScript
   - Uses CodeT5+ model with RAG
   - Applies conversion patterns

4. **Asset Converter Agent**
   - Transforms textures (PNG optimization)
   - Converts models (JSON format)
   - Adapts sounds (OGG format)

5. **Packaging Agent**
   - Assembles .mcaddon structure
   - Creates manifests
   - Validates schemas

6. **QA Validator Agent**
   - Syntax checking
   - Semantic validation
   - Error reporting

**RAG (Retrieval Augmented Generation)**:
- Searches database of 100+ successful conversions
- Finds similar patterns
- Applies proven solutions
- Learns from user corrections

### 18. Is my code safe?

**Security**:
- Encrypted upload (TLS 1.3)
- Isolated processing environment
- Auto-deletion after 30 days (free) or 90 days (paid)
- Never shared with third parties

**Privacy**:
- Your mods are not used for training without consent
- Opt-in to contribute to AI learning
- GDPR compliant (EU users)
- SOC 2 Type II certified (Enterprise)

## Platform Questions

### 19. Which Bedrock platforms are supported?

**Fully supported**:
- Windows 10/11
- iOS (iPhone/iPad)
- Android
- Xbox One, Series S/X
- PlayStation 4/5
- Nintendo Switch

**Limitations**:
- Console: No custom scripts (Marketplace only)
- Mobile: Performance limits (complex mods may lag)
- PS4/Switch: No experimental features

### 20. Do converted add-ons work on Realms?

**Partially**:
- Simple items/blocks: Yes
- Custom scripts: No (Realms disables Script API)
- Experimental features: No

**Workaround**:
- Test in local world first
- Use for features that don't require scripts
- Consider dedicated server instead

### 21. Can I publish converted mods to Marketplace?

**Yes, but**:
1. Must pass Mojang's review
2. Must meet quality standards
3. Must respect original mod's license
4. Must comply with Marketplace rules

**Marketplace requirements**:
- No trademarked content (without permission)
- Original assets or properly licensed
- Stable, tested add-on
- Professional presentation

**Tips**:
- Start with free distribution (Modrinth)
- Gather feedback and bug reports
- Polish thoroughly before Marketplace submission
- Consider partnership program

## Advanced Questions

### 22. How do I use the API?

**REST API** (Pro/Studio/Enterprise):

```bash
# Convert a mod
curl -X POST https://api.portkit.cloud/v1/convert \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -F "file=@mod.jar" \
  -F "options={\"complexity\":\"high\"}"
```

**Rate limits**:
- Free: N/A
- Pro: 1,000 calls/month
- Studio: 10,000 calls/month
- Enterprise: Unlimited

**Documentation**: [docs.portkit.cloud/api](https://docs.portkit.cloud/api)

### 23. Can I batch convert multiple mods?

**Pro feature**:
- Upload up to 50 mods at once
- Monitor progress in dashboard
- Download all conversions as ZIP
- Priority processing

**Via API**:
```python
import requests

mods = ["mod1.jar", "mod2.jar", "mod3.jar"]
for mod in mods:
  requests.post(
    "https://api.portkit.cloud/v1/convert",
    files={"file": open(mod, "rb")},
    headers={"Authorization": f"Bearer {API_KEY}"}
  )
```

### 24. How does batch conversion work?

**Automatic** (Pro+):
1. Upload multiple mods (drag-drop or API)
2. AI processes in parallel
3. Email notification when complete
4. Download all conversions

**Use cases**:
- Converting mod packs
- Migrating entire projects
- Testing compatibility

### 25. Can I integrate Portkit into my workflow?

**Enterprise feature**:
- CI/CD integration
- GitHub Actions
- Jenkins, GitLab CI
- Custom webhooks

**Example GitHub Action**:
```yaml
- name: Convert to Bedrock
  uses: portkit/action@v1
  with:
    api-key: ${{ secrets.MODPORTER_KEY }}
    input: build/java-mod.jar
    output: dist/bedrock.mcaddon
```

## Support and Community

### 26. How do I get help?

**Free users**:
- Discord community (usually <1hr response)
- Public forums
- Documentation
- YouTube tutorials

**Pro users**:
- Priority email support (24hr response)
- Discord priority channel
- Screen sharing sessions
- Conversion review

**Enterprise**:
- Dedicated support manager
- 24/7 phone support
- SLA guarantees
- On-premise training

### 27. How can I contribute?

**Ways to help**:
1. **Share successful conversions** (opt-in to AI training)
2. **Report bugs** on GitHub Issues
3. **Suggest features** on Discord
4. **Write documentation** (community guides)
5. **Help others** on Discord/forums

**Benefits**:
- Pro badge on Discord
- Early access to features
- Discount on Pro subscription
- Impact on product direction

### 28. Is there an affiliate program?

Yes! Earn 20% commission:
- Share your referral link
- Earn 20% of subscription revenue
- Paid out monthly via PayPal
- Real-time analytics dashboard

**Sign up**: [portkit.cloud/affiliates](https://portkit.cloud/affiliates)

## Legal and Licensing

### 29. Who owns the converted add-on?

**You do**, with conditions:
- Original mod author retains copyright
- You own the Bedrock implementation
- Must respect original license
- Can't remove attribution

**For redistribution**:
- Check original mod's license
- Credit original author
- Link to original mod
- Don't claim as your own

### 30. Can I use converted add-ons commercially?

**Depends on original license**:

| Original License | Commercial Use | Action Needed |
|------------------|----------------|---------------|
| MIT/Apache/BSD | Yes | Credit author |
| CC BY-NC | No | Non-commercial only |
| All Rights Reserved | No | Contact author |
| Custom | Varies | Check license |

**Marketplace sales**:
- Must have original author's permission
- Or use only your own original mods
- Mojang takes 30% commission

## Still Have Questions?

- **Documentation**: [docs.portkit.cloud](https://docs.portkit.cloud)
- **Discord**: [discord.gg/modporter](https://discord.gg/modporter)
- **Email**: support@portkit.cloud
- **Twitter**: [@modporterai](https://twitter.com/modporterai)

We typically respond within 1 hour on Discord, 24 hours via email (Pro users get priority).
