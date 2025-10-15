# Using the Example Theme in PDF Rendering

## Overview

The `/themes/render-pdfs` endpoint now supports an optional `use_example_theme` flag that allows you to render PDFs using the reference example theme instead of a stored theme package.

## Why Use the Example Theme?

The example theme is the **well-proportioned, professional theme** that was created to demonstrate proper spacing and prevent the "summary taking up a whole page" issue. It features:

- ✅ Compact summary section (10pt font, 1.4 line-height, ~1.2in height)
- ✅ Proper proportions: Header 15%, Summary 11%, Experience 50-60%
- ✅ Professional appearance with efficient space usage
- ✅ Summary and Experience on the same page
- ✅ Minimal spacing (0.1-0.15in between sections)

## API Changes

### Before (Required theme_package_id):
```json
POST /api/v1/themes/render-pdfs
{
  "theme_package_id": "507f1f77bcf86cd799439011",
  "resume_id": "507f191e810c19729de860ea",
  "cover_letter_id": "507f191e810c19729de860eb",
  "upload": true
}
```

### After (Optional use_example_theme):
```json
POST /api/v1/themes/render-pdfs
{
  "resume_id": "507f191e810c19729de860ea",
  "cover_letter_id": "507f191e810c19729de860eb",
  "use_example_theme": true,
  "upload": true
}
```

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `resume_id` | string | Yes | - | MongoDB ObjectId of the resume to render |
| `cover_letter_id` | string | Yes | - | MongoDB ObjectId of the cover letter to render |
| `theme_package_id` | string | No* | null | ID of stored theme package to use |
| `use_example_theme` | boolean | No | false | If true, uses the reference example theme |
| `upload` | boolean | No | true | Whether to upload PDFs to Cloudinary |

*Either `theme_package_id` OR `use_example_theme=true` must be provided

## Usage Examples

### Example 1: Render with Example Theme
```bash
curl -X POST "http://localhost:8000/api/v1/themes/render-pdfs" \
  -H "Content-Type: application/json" \
  -d '{
    "resume_id": "507f191e810c19729de860ea",
    "cover_letter_id": "507f191e810c19729de860eb",
    "use_example_theme": true,
    "upload": true
  }'
```

### Example 2: Render with Stored Theme (Original Behavior)
```bash
curl -X POST "http://localhost:8000/api/v1/themes/render-pdfs" \
  -H "Content-Type: application/json" \
  -d '{
    "resume_id": "507f191e810c19729de860ea",
    "cover_letter_id": "507f191e810c19729de860eb",
    "theme_package_id": "507f1f77bcf86cd799439011",
    "upload": true
  }'
```

### Example 3: Generate Local PDFs Only (No Upload)
```bash
curl -X POST "http://localhost:8000/api/v1/themes/render-pdfs" \
  -H "Content-Type: application/json" \
  -d '{
    "resume_id": "507f191e810c19729de860ea",
    "cover_letter_id": "507f191e810c19729de860eb",
    "use_example_theme": true,
    "upload": false
  }'
```

## Response Format

```json
{
  "status": 200,
  "message": "PDFs generated using example theme",
  "data": {
    "resume_pdf_path": "/tmp/resume_a1b2c3d4.pdf",
    "cover_pdf_path": "/tmp/cover_e5f6g7h8.pdf",
    "resume_url": "https://res.cloudinary.com/...",
    "cover_url": "https://res.cloudinary.com/..."
  }
}
```

## Error Cases

### Missing Both theme_package_id and use_example_theme
```json
{
  "detail": "Either theme_package_id must be provided or use_example_theme must be true"
}
```

### Resume Not Found
```json
{
  "detail": "Resume not found"
}
```

### Cover Letter Not Found
```json
{
  "detail": "Cover letter not found"
}
```

### Theme Package Not Found (when using stored theme)
```json
{
  "detail": "Theme package not found"
}
```

## When to Use Each Option

### Use Example Theme When:
- ✅ Testing the system without creating themes
- ✅ You want a guaranteed good layout
- ✅ You need a quick PDF without theme setup
- ✅ Demonstrating the app to clients
- ✅ Comparing against AI-generated themes

### Use Stored Theme When:
- ✅ You have a specific brand/design requirement
- ✅ You've created a custom theme you like
- ✅ You want consistent branding across documents
- ✅ You need to match company style guides

## Code Implementation

### New Function in `app/services/designer_pdf.py`:
```python
def get_example_theme() -> ThemeSchema:
    """Return the reference example theme used in agent training."""
    from app.schemas.theme import ThemeTemplate
    from app.agents.theme_examples import (
        get_resume_example_for_agent, 
        get_cover_letter_example_for_agent
    )
    
    resume_example = get_resume_example_for_agent()
    cover_example = get_cover_letter_example_for_agent()
    
    return ThemeSchema(
        name="Example Professional Theme",
        description="Reference theme demonstrating proper proportions...",
        resume_template=ThemeTemplate(
            template=resume_example['template'],
            styles=resume_example['styles'],
        ),
        cover_letter_template=ThemeTemplate(
            template=cover_example['template'],
            styles=cover_example['styles'],
        ),
    )
```

### Updated Endpoint in `app/api/v1/endpoints/themes.py`:
The endpoint now:
1. Checks if `use_example_theme` is True
2. If yes, calls `get_example_theme()` instead of fetching from database
3. If no, follows original logic to fetch theme package from database

## Testing

To verify the example theme works:

1. **Get resume and cover letter IDs** from your database
2. **Call the endpoint** with `use_example_theme: true`
3. **Download the PDFs** and verify:
   - Summary is compact (~1.2in height)
   - Experience starts on page 1
   - Professional appearance with minimal spacing

## Benefits

1. **Quick Testing**: No need to create themes for testing
2. **Baseline Comparison**: Compare AI-generated themes against the example
3. **Guaranteed Quality**: Always have a fallback "good" theme
4. **Development Efficiency**: Faster iteration during development
5. **Demo/Prototype**: Show clients working PDFs immediately

## Related Files

- `app/agents/theme_examples.py` - Contains the example templates
- `app/services/designer_pdf.py` - PDF rendering service with new function
- `app/api/v1/endpoints/themes.py` - Updated endpoint with flag support
- `THEME_EXAMPLES_IMPLEMENTATION.md` - Full documentation on examples
- `THEME_BEFORE_AFTER_COMPARISON.md` - Visual comparison and metrics

---

**Pro Tip**: Use the example theme when first testing your resume data to ensure it looks good, then generate custom themes for branding needs.
