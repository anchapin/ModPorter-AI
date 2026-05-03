# Minecraft Version Compatibility and Update Process

This document outlines the version tracking and update process for PortKit's Minecraft conversion capabilities.

## Version Tracking

### Current Supported Versions

- **Java Edition**: 1.18 - 1.21
- **Bedrock Edition Target**: 1.21.0

Display format: `Java 1.18-1.21 → Bedrock 1.21.0`

### Version Information API

Version information is available via:
- Backend endpoint: `GET /api/v1/info/versions`
- Frontend landing page version badge
- Conversion report metadata

## Release Monitoring

### Automated Monitoring

PortKit monitors for new Minecraft releases via:
1. Mojang bug tracker RSS feed
2. Minecraft.net download page checks
3. Modrinth/CurseForge announcement feeds

### Check Frequency

- Automated checks run every 24 hours
- Manual checks can be triggered via admin endpoint

### Detection Response

When a new version is detected:
1. GitHub issue is automatically created
2. Labels applied: `version-update`, `needs-analysis`
3. Assigned to Research Scout + Software Developer agents

## Post-Release Update Checklist

When a new Minecraft major version is released, the following components need updating:

### 1. Item/Block ID Mappings (minecraft-data)

- [ ] Update `minecraft-data` npm package or data files
- [ ] Verify item ID mappings for new blocks/items
- [ ] Update block state definitions
- [ ] Test with known working conversions

### 2. Bedrock Behavior Pack Schemas

- [ ] Check `bedrock_block_schema.json` for format changes
- [ ] Update `bedrock_item_schema.json` if item format changed
- [ ] Verify `bedrock_recipe_schema.json` compatibility
- [ ] Update `bedrock_entity_schema.json` for new entity components
- [ ] Validate all schema files against official Minecraft documentation

### 3. Format Version Updates

- [ ] Identify new format_version string (e.g., "1.22.0")
- [ ] Update default `target_version` in conversion service
- [ ] Update schema loaders to handle new format versions
- [ ] Add backward compatibility with old format versions

### 4. AI Conversion Engine

- [ ] Update RAG index with new version examples
- [ ] Retrain or fine-tune conversion models if needed
- [ ] Update conversion prompts to reference new version
- [ ] Test existing conversion patterns against new format

### 5. Documentation

- [ ] Update landing page version display
- [ ] Update conversion report template
- [ ] Document breaking changes in release notes
- [ ] Notify beta users via email/newsletter

### 6. Validation & Testing

- [ ] Run full test suite against new version
- [ ] Validate sample mod conversions
- [ ] Check Marketplace Toolkit compatibility
- [ ] Verify with real-world mod if available

## Maintenance Schedule

After each Mojang release (typically every 6 months):

| Week | Activity |
|------|----------|
| 1 | Monitor release, create tracking issue |
| 2 | Analyze schema changes, update mappings |
| 3 | Update converters, run tests |
| 4 | Deploy to staging, validate with beta users |
| 5 | Production deployment, notify users |

## User Communication

### Version Update Notifications

Beta users receive notifications when:
1. New Minecraft version becomes supported
2. Existing conversions use an older format that should be re-run

### Notification Channels

- Email newsletter for major version support
- In-app banner on landing page
- Conversion report includes version info

## Known Breaking Changes Patterns

When updating versions, watch for:

1. **Block IDs**: New blocks added, removed, or renamed
2. **Item Components**: New component syntax or deprecated components
3. **Entity Format**: Component-based vs old entity format changes
4. **Recipe Changes**: New recipe types or syntax changes
5. **Dimension Definitions**: New dimensions or biome ID changes

## Emergency Response

If a broken conversion is detected post-release:

1. Identify affected conversions via format_version mismatch
2. Add warning banner to affected users
3. Prioritize fix based on user impact
4. Document incident in post-mortem

## References

- [Minecraft Data Registry](https://github.com/PrismarineJS/minecraft-data)
- [Bedrock Protocol Documentation](https://learn.microsoft.com/en-us/minecraft/creator/)
- [Minecraft Changelog](https://www.minecraft.net/en-us/article/minecraft-java-edition-1-21)