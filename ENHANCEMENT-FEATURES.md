# Enhancement Features Documentation

**ModPorter AI - Advanced Features**

---

## Visual Conversion Editor

### Overview

Side-by-side code editor for reviewing and editing converted code with live preview.

### Features

**Split-Pane View:**
- Java code (left) - Read-only
- Bedrock code (right) - Editable
- Syntax highlighting for both
- Line number synchronization

**Live Preview:**
- Real-time JSON validation
- Structure tree view
- Error highlighting
- Auto-complete suggestions

**AI Assistance:**
- Fix errors button
- Improve code suggestions
- Alternative implementations
- Confidence scores

**Templates:**
- Pre-built patterns for common conversions
- Customizable fields
- Instant application
- Category browsing

### Usage

**Access:**
1. Complete a conversion
2. Click "Edit in Visual Editor"
3. Review side-by-side comparison
4. Make edits as needed
5. Download updated .mcaddon

**Keyboard Shortcuts:**
- `Ctrl+S` - Save changes
- `Ctrl+Z` - Undo
- `Ctrl+Y` - Redo
- `Ctrl+F` - Find
- `Ctrl+H` - Find and replace
- `F5` - Refresh preview

---

## Batch Conversion

### Overview

Convert multiple mods simultaneously with centralized tracking.

### Limits

| Tier | Max Files | Concurrent | Priority |
|------|-----------|------------|----------|
| **Free** | 5 | 2 | Normal |
| **Pro** | 20 | 10 | High |
| **Studio** | 50 | 20 | Critical |

### Usage

**Start Batch:**
1. Click "Batch Conversion"
2. Upload 2-20 files (drag & drop)
3. Configure options (optional)
4. Click "Start Batch"
5. Monitor progress dashboard

**Progress Tracking:**
- Real-time status for each file
- Overall batch progress bar
- Estimated completion time
- Individual error reporting

**Results:**
- Download individual files
- Download all as ZIP
- View conversion reports
- Re-run failed conversions

### API Example

```python
# Start batch conversion
response = requests.post(
    "https://api.portkit.cloud/api/v1/batch/convert",
    headers={"Authorization": f"Bearer {token}"},
    json={
        "files": [
            {"filename": "mod1.jar", "data": "..."},
            {"filename": "mod2.jar", "data": "..."},
        ],
        "options": {"target_version": "1.20.0"},
        "priority": "normal",
    }
)

batch_id = response.json()["batch_id"]

# Check status
status = requests.get(
    f"https://api.portkit.cloud/api/v1/batch/{batch_id}/status",
    headers={"Authorization": f"Bearer {token}"}
)

# Download results
results = requests.get(
    f"https://api.portkit.cloud/api/v1/batch/{batch_id}/results",
    headers={"Authorization": f"Bearer {token}"}
)
```

---

## Community Pattern Library

### Overview

Shared collection of conversion patterns contributed by the community.

### Pattern Types

**Items:**
- Basic items
- Tools (sword, pickaxe, etc.)
- Armor pieces
- Food items
- Special items

**Blocks:**
- Basic blocks
- Ores
- Decorative blocks
- Functional blocks
- Multi-block structures

**Entities:**
- Passive mobs
- Hostile mobs
- Boss entities
- Custom AI

### Contributing Patterns

**Submission Process:**
1. Create successful conversion
2. Click "Share as Pattern"
3. Add description and tags
4. Submit for review
5. Community voting
6. Published to library

**Pattern Template:**
```json
{
  "name": "Basic Sword",
  "category": "items/tools",
  "description": "Custom sword with configurable damage",
  "java_pattern": "public class .* extends SwordItem",
  "bedrock_template": "{...}",
  "variables": [
    {"name": "namespace", "type": "string", "required": true},
    {"name": "item_name", "type": "string", "required": true},
    {"name": "damage", "type": "number", "default": 5}
  ],
  "tags": ["sword", "weapon", "tool", "combat"]
}
```

### Browsing Patterns

**Search:**
- By keyword
- By category
- By tags
- By contributor

**Filter:**
- Most popular
- Highest rated
- Recently added
- Verified patterns

**Rating:**
- 1-5 stars
- Usage count
- Success rate
- Comments

---

## Performance Optimizations

### Conversion Speed Improvements

**Caching:**
- Model caching (reduces load time)
- RAG result caching (faster similar conversions)
- Template caching (instant access)

**Parallel Processing:**
- Multi-threaded analysis
- Concurrent AI agent execution
- Batch embedding generation

**Optimizations:**
- Lazy loading of models
- Streaming responses
- Progressive enhancement

### Benchmarks

**Before Optimization:**
- Simple mod: 5-8 minutes
- Moderate mod: 10-15 minutes
- Complex mod: 20-30 minutes

**After Optimization:**
- Simple mod: 2-3 minutes ⚡
- Moderate mod: 5-8 minutes ⚡
- Complex mod: 10-15 minutes ⚡

### Resource Usage

**Memory:**
- Base: 512MB
- Per conversion: +256MB
- Maximum: 4GB

**CPU:**
- Base: 1 core
- Per AI agent: +1 core
- Maximum: 8 cores

---

## API Reference

### Visual Editor Endpoints

```
POST   /api/v1/editor/session      - Create editor session
POST   /api/v1/editor/edit         - Edit code
POST   /api/v1/editor/ai-suggest   - Get AI suggestion
POST   /api/v1/editor/apply-template - Apply template
GET    /api/v1/editor/templates    - List templates
POST   /api/v1/editor/compare      - Compare versions
```

### Batch Conversion Endpoints

```
POST   /api/v1/batch/convert       - Start batch
GET    /api/v1/batch/{id}/status   - Get status
GET    /api/v1/batch/{id}/results  - Get results
GET    /api/v1/batch/{id}/download-all - Download ZIP
DELETE /api/v1/batch/{id}          - Cancel batch
```

### Pattern Library Endpoints

```
GET    /api/v1/patterns            - List patterns
GET    /api/v1/patterns/{id}       - Get pattern
POST   /api/v1/patterns            - Submit pattern
POST   /api/v1/patterns/{id}/rate  - Rate pattern
GET    /api/v1/patterns/search     - Search patterns
```

---

## Troubleshooting

### Visual Editor Issues

**Editor not loading:**
- Clear browser cache
- Check browser console for errors
- Try different browser

**Changes not saving:**
- Check internet connection
- Verify conversion is editable
- Refresh and try again

**AI suggestions slow:**
- Normal during peak hours
- Try again in a few minutes
- Contact support if persistent

### Batch Conversion Issues

**Upload fails:**
- Check file sizes (max 100MB each)
- Verify file formats (.jar, .zip)
- Check total batch size

**Conversions stuck:**
- Check batch status page
- Refresh status
- Contact support if >30 minutes

**Download fails:**
- Check individual conversion status
- Try downloading individually
- Clear browser cache

---

*Enhancement Features Version: 1.0*
*Last Updated: 2026-03-14*
