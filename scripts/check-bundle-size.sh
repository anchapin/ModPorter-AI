#!/bin/bash
# Bundle size check script
# This script checks bundle sizes against defined thresholds

set -e

DIST_DIR="${1:-frontend/dist}"
THRESHOLD_KB="${2:-500}"

echo "========================================"
echo "Bundle Size Analysis"
echo "========================================"
echo ""

# Check if dist directory exists
if [ ! -d "$DIST_DIR" ]; then
    echo "Error: $DIST_DIR does not exist. Run 'pnpm run build' first."
    exit 1
fi

# Get total bundle size
TOTAL_SIZE=$(du -sk "$DIST_DIR" | cut -f1)
echo "Total bundle size: ${TOTAL_SIZE} KB"

# Check for individual JS files and their sizes
echo ""
echo "JavaScript files:"
echo "----------------"
if [ -d "$DIST_DIR/assets" ]; then
    for file in "$DIST_DIR/assets"/*.js; do
        if [ -f "$file" ]; then
            SIZE=$(du -k "$file" | cut -f1)
            BASENAME=$(basename "$file")
            echo "  $BASENAME: ${SIZE} KB"
            
            # Check against threshold
            if [ "$SIZE" -gt "$THRESHOLD_KB" ]; then
                echo "  ⚠️  WARNING: $BASENAME exceeds threshold of ${THRESHOLD_KB} KB"
            fi
        fi
    done
fi

# Calculate gzipped sizes if gzip is available
echo ""
echo "Gzipped sizes (approximate):"
echo "---------------------------"
if command -v gzip &> /dev/null && [ -d "$DIST_DIR/assets" ]; then
    for file in "$DIST_DIR/assets"/*.js; do
        if [ -f "$file" ]; then
            GZ_SIZE=$(gzip -c "$file" | wc -c | awk '{print int($1/1024)}')
            BASENAME=$(basename "$file")
            echo "  $BASENAME: ~${GZ_SIZE} KB (gzipped)"
        fi
    done
fi

# Check stats.html (bundle visualizer output)
if [ -f "$DIST_DIR/stats.html" ]; then
    echo ""
    echo "Bundle visualizer: $DIST_DIR/stats.html"
    echo "  Open in browser to view treemap visualization"
fi

# Exit with error if total size exceeds threshold
if [ "$TOTAL_SIZE" -gt "$((THRESHOLD_KB * 10))" ]; then
    echo ""
    echo "❌ ERROR: Total bundle size (${TOTAL_SIZE} KB) exceeds maximum threshold ($((THRESHOLD_KB * 10)) KB)"
    exit 1
fi

echo ""
echo "✅ Bundle size check passed"
exit 0
