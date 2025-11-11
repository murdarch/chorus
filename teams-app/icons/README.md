# Teams App Icons

You need two icon files for your Teams app:

1. **color-icon.png**: 192x192 pixels, full color
2. **outline-icon.png**: 32x32 pixels, transparent outline (white on transparent)

## Quick Creation

### Option 1: Use an online tool
- https://favicon.io/favicon-generator/
- https://www.canva.com/

### Option 2: Use ImageMagick (if installed)
```bash
# Create simple placeholder
convert -size 192x192 xc:#5558AF -pointsize 120 -fill white -gravity center -annotate +0+0 'C' color-icon.png
convert -size 32x32 xc:none -pointsize 24 -fill white -gravity center -annotate +0+0 'C' outline-icon.png
```

### Option 3: Download free icons
- https://www.flaticon.com/
- https://icons8.com/

## Requirements

- **color-icon.png**: Must be exactly 192x192 pixels
- **outline-icon.png**: Must be exactly 32x32 pixels
- Both must be PNG format
- Outline icon should have transparent background
