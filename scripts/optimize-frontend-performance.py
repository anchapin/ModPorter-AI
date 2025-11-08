#!/usr/bin/env python3
"""
Frontend Performance Optimizer for ModPorter AI

This script analyzes and optimizes frontend performance by:
- Analyzing bundle size and dependencies
- Implementing code splitting strategies
- Optimizing asset loading
- Adding performance budgets
- Setting up monitoring

Usage: python scripts/optimize-frontend-performance.py [--analyze-only]
"""

import json
import os
import sys
import subprocess
import shutil
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import requests

@dataclass
class FrontendPerformanceMetrics:
    bundle_size_kb: float
    chunk_count: int
    largest_chunk_kb: float
    dependencies_count: int
    unused_dependencies: List[str]
    optimization_suggestions: List[str]
    lighthouse_score: Optional[int] = None

class FrontendPerformanceOptimizer:
    def __init__(self):
        self.frontend_dir = Path(__file__).parent.parent / "frontend"
        self.package_json_path = self.frontend_dir / "package.json"
        self.vite_config_path = self.frontend_dir / "vite.config.ts"
        self.dist_dir = self.frontend_dir / "dist"
        
    def analyze_dependencies(self) -> Dict[str, Any]:
        """Analyze frontend dependencies for optimization opportunities"""
        print("📦 Analyzing frontend dependencies...")
        
        if not self.package_json_path.exists():
            return {"error": "package.json not found"}
        
        with open(self.package_json_path, 'r') as f:
            package_data = json.load(f)
        
        dependencies = package_data.get('dependencies', {})
        dev_dependencies = package_data.get('devDependencies', {})
        
        # Analyze dependency sizes (approximate)
        large_deps = []
        unused_deps = []
        
        # Common large dependencies to watch
        large_dep_threshold_kb = 1000
        known_large_deps = {
            '@mui/material': 8000,
            '@emotion/react': 2000,
            '@emotion/styled': 1500,
            'monaco-editor': 3000,
            'mermaid': 2000,
            'axios': 1000
        }
        
        for dep, version in dependencies.items():
            if dep in known_large_deps:
                size_kb = known_large_deps[dep]
                if size_kb > large_dep_threshold_kb:
                    large_deps.append({
                        "name": dep,
                        "version": version,
                        "estimated_size_kb": size_kb,
                        "category": "large"
                    })
        
        # Potential unused dependencies (based on import analysis)
        potential_unused = [
            '@testing-library/jest-dom',  # Dev dependency
            '@testing-library/user-event',  # Dev dependency
            '@vitejs/plugin-react',  # Build tool
            'eslint',  # Dev tool
            'prettier',  # Dev tool
            'patch-package',  # Dev tool
        ]
        
        for dep in potential_unused:
            if dep in dependencies and dep not in dev_dependencies:
                unused_deps.append(dep)
        
        return {
            "total_dependencies": len(dependencies),
            "dev_dependencies": len(dev_dependencies),
            "large_dependencies": large_deps,
            "unused_dependencies": unused_deps,
            "total_estimated_size_kb": sum(dep["estimated_size_kb"] for dep in large_deps)
        }
    
    def analyze_bundle_structure(self) -> Dict[str, Any]:
        """Analyze built bundle structure"""
        print("📊 Analyzing bundle structure...")
        
        if not self.dist_dir.exists():
            return {"error": "Build directory not found. Run 'pnpm run build' first."}
        
        # Find all JS/CSS files in dist
        js_files = list(self.dist_dir.rglob("*.js"))
        css_files = list(self.dist_dir.rglob("*.css"))
        
        total_js_size = sum(f.stat().st_size for f in js_files) / 1024  # KB
        total_css_size = sum(f.stat().st_size for f in css_files) / 1024  # KB
        
        chunks = []
        for js_file in js_files:
            size_kb = js_file.stat().st_size / 1024
            chunks.append({
                "file": js_file.name,
                "size_kb": size_kb,
                "type": "chunk"
            })
        
        # Sort by size
        chunks.sort(key=lambda x: x["size_kb"], reverse=True)
        
        return {
            "total_js_size_kb": total_js_size,
            "total_css_size_kb": total_css_size,
            "total_bundle_size_kb": total_js_size + total_css_size,
            "chunk_count": len(chunks),
            "largest_chunk_kb": chunks[0]["size_kb"] if chunks else 0,
            "chunks": chunks[:10],  # Top 10 chunks
            "css_files": len(css_files)
        }
    
    def generate_optimization_suggestions(self, dependency_analysis: Dict, bundle_analysis: Dict) -> List[str]:
        """Generate optimization suggestions based on analysis"""
        suggestions = []
        
        # Bundle size suggestions
        if bundle_analysis.get("total_bundle_size_kb", 0) > 5000:  # 5MB
            suggestions.append("🎯 Bundle size is large (>5MB). Consider:")
            suggestions.append("   • Implement code splitting with dynamic imports")
            suggestions.append("   • Use tree shaking to remove unused code")
            suggestions.append("   • Consider lighter alternatives for large dependencies")
        
        # Largest chunk suggestions
        if bundle_analysis.get("largest_chunk_kb", 0) > 2000:  # 2MB
            suggestions.append("📦 Large chunk detected. Consider:")
            suggestions.append("   • Split large chunks with lazy loading")
            suggestions.append("   • Implement vendor chunk separation")
        
        # Dependency suggestions
        large_deps = dependency_analysis.get("large_dependencies", [])
        if large_deps:
            suggestions.append("📚 Large dependencies found:")
            for dep in large_deps[:3]:
                suggestions.append(f"   • {dep['name']}: {dep['estimated_size_kb']}KB - consider alternatives")
            
            # Specific suggestions for known large deps
            large_dep_names = [dep["name"] for dep in large_deps]
            
            if '@mui/material' in large_dep_names:
                suggestions.append("   • Consider MUI tree shaking and import only used components")
            
            if 'monaco-editor' in large_dep_names:
                suggestions.append("   • Use Monaco Editor web workers and load only required languages")
        
        # Unused dependencies
        unused_deps = dependency_analysis.get("unused_dependencies", [])
        if unused_deps:
            suggestions.append("🧹 Potential unused dependencies:")
            for dep in unused_deps:
                suggestions.append(f"   • {dep} - move to devDependencies or remove")
        
        # General performance suggestions
        suggestions.extend([
            "⚡ General optimizations:",
            "   • Implement image lazy loading and compression",
            "   • Add service worker for offline caching",
            "   • Use CDN for static assets",
            "   • Implement resource hints (preload, prefetch)",
            "   • Add compression (gzip/brotli) for server responses",
            "   • Consider using web workers for heavy computations"
        ])
        
        return suggestions
    
    def generate_optimized_vite_config(self) -> str:
        """Generate optimized Vite configuration"""
        config_content = '''
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'

export default defineConfig({
  plugins: [react()],
  
  // Build optimizations
  build: {
    // Enable code splitting
    rollupOptions: {
      output: {
        manualChunks: {
          // Vendor chunk separation
          vendor: ['react', 'react-dom'],
          ui: ['@mui/material', '@emotion/react', '@emotion/styled'],
          editor: ['monaco-editor', '@monaco-editor/react'],
          utils: ['axios', 'date-fns']
        },
        
        // Optimize chunk naming
        chunkFileNames: 'assets/js/[name]-[hash].js',
        entryFileNames: 'assets/js/[name]-[hash].js',
        assetFileNames: (assetInfo) => {
          const extType = assetInfo.name.split('.').pop()
          if (/png|jpe?g|svg|gif|tiff|bmp|ico/i.test(extType)) {
            return 'assets/images/[name]-[hash][extname]'
          }
          if (/woff2?|eot|ttf|otf/i.test(extType)) {
            return 'assets/fonts/[name]-[hash][extname]'
          }
          return 'assets/[name]-[hash][extname]'
        }
      }
    },
    
    // Optimize bundle size
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true, // Remove console.log in production
        drop_debugger: true,
        pure_funcs: ['console.log']
      }
    },
    
    // Chunk size warning limit
    chunkSizeWarningLimit: 1000,
    
    // CSS code splitting
    cssCodeSplit: true,
    
    // Asset optimization
    assetsInlineLimit: 4096, // 4kb inline limit
  },
  
  // Development server optimizations
  server: {
    hmr: {
      overlay: true
    },
    fs: {
      // Improve file serving performance
      strict: false
    }
  },
  
  // Preview server optimizations
  preview: {
    port: 3000,
    strictPort: true
  },
  
  // Resolve optimizations
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
      '@components': resolve(__dirname, 'src/components'),
      '@hooks': resolve(__dirname, 'src/hooks'),
      '@utils': resolve(__dirname, 'src/utils'),
      '@services': resolve(__dirname, 'src/services')
    }
  },
  
  // CSS optimizations
  css: {
    devSourcemap: true,
    preprocessorOptions: {
      scss: {
        additionalData: `@import "@/styles/variables.scss";`
      }
    }
  },
  
  // Optimizations for large dependencies
  optimizeDeps: {
    include: [
      'react',
      'react-dom',
      '@mui/material',
      '@emotion/react',
      '@emotion/styled'
    ]
  }
})
'''
        return config_content
    
    def generate_performance_budgets(self) -> Dict[str, Any]:
        """Generate performance budgets configuration"""
        return {
            "budgets": [
                {
                    "path": "*.js",
                    "limit": "4 MB",
                    "type": "initial"
                },
                {
                    "path": "vendor.*.js",
                    "limit": "2 MB",
                    "type": "initial"
                },
                {
                    "path": "*.css",
                    "limit": "500 KB",
                    "type": "initial"
                },
                {
                    "path": "*.png",
                    "limit": "1 MB",
                    "type": "any"
                },
                {
                    "path": "*.jpg",
                    "limit": "500 KB",
                    "type": "any"
                }
            ],
            "performance_thresholds": {
                "first_contentful_paint": 2000,
                "largest_contentful_paint": 4000,
                "time_to_interactive": 5000,
                "cumulative_layout_shift": 0.25,
                "total_blocking_time": 600
            }
        }
    
    def create_service_worker(self) -> str:
        """Create optimized service worker"""
        service_worker_content = '''
// Service Worker for ModPorter AI
const CACHE_NAME = 'modporter-ai-v1';
const urlsToCache = [
  '/',
  '/static/js/bundle.js',
  '/static/css/main.css',
  '/manifest.json'
];

// Install event - cache resources
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('Opened cache');
        return cache.addAll(urlsToCache);
      })
  );
});

// Fetch event - serve from cache when offline
self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request)
      .then((response) => {
        // Cache hit - return response
        if (response) {
          return response;
        }

        // Clone request
        const fetchRequest = event.request.clone();

        return fetch(fetchRequest).then(
          (response) => {
            // Check if valid response
            if (!response || response.status !== 200 || response.type !== 'basic') {
              return response;
            }

            // Clone response
            const responseToCache = response.clone();

            caches.open(CACHE_NAME)
              .then((cache) => {
                // Don't cache API requests
                if (!fetchRequest.url.includes('/api/')) {
                  cache.put(event.request, responseToCache);
                }
              });

            return response;
          }
        );
      })
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME) {
            console.log('Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});
'''
        return service_worker_content
    
    async def run_lighthouse_audit(self) -> Optional[Dict[str, Any]]:
        """Run Lighthouse performance audit if available"""
        print("🚀 Running Lighthouse audit...")
        
        try:
            # Check if Lighthouse CLI is available
            subprocess.run(['lighthouse', '--version'], capture_output=True, check=True)
            
            # Run Lighthouse audit
            result = subprocess.run([
                'lighthouse',
                'http://localhost:3000',
                '--output=json',
                '--output-path=lighthouse-report.json',
                '--chrome-flags="--headless"'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                with open('lighthouse-report.json', 'r') as f:
                    lighthouse_data = json.load(f)
                
                performance_score = lighthouse_data['lhr']['categories']['performance']['score'] * 100
                
                return {
                    "performance_score": performance_score,
                    "fcp": lighthouse_data['lhr']['audits']['first-contentful-paint']['numericValue'],
                    "lcp": lighthouse_data['lhr']['audits']['largest-contentful-paint']['numericValue'],
                    "tti": lighthouse_data['lhr']['audits']['interactive']['numericValue'],
                    "cls": lighthouse_data['lhr']['audits']['cumulative-layout-shift']['numericValue'],
                    "tbt": lighthouse_data['lhr']['audits']['total-blocking-time']['numericValue']
                }
        
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("⚠️ Lighthouse not available. Install with: npm install -g lighthouse")
        
        return None
    
    def apply_optimizations(self) -> None:
        """Apply performance optimizations"""
        print("🔧 Applying frontend optimizations...")
        
        # 1. Backup existing config
        if self.vite_config_path.exists():
            backup_path = self.vite_config_path.with_suffix('.ts.backup')
            shutil.copy2(self.vite_config_path, backup_path)
            print(f"✅ Backed up existing config to {backup_path}")
        
        # 2. Write optimized Vite config
        optimized_config = self.generate_optimized_vite_config()
        with open(self.vite_config_path, 'w') as f:
            f.write(optimized_config)
        print("✅ Optimized Vite configuration applied")
        
        # 3. Create performance budgets file
        budgets = self.generate_performance_budgets()
        budgets_path = self.frontend_dir / "performance-budgets.json"
        with open(budgets_path, 'w') as f:
            json.dump(budgets, f, indent=2)
        print(f"✅ Performance budgets created: {budgets_path}")
        
        # 4. Create service worker
        sw_content = self.create_service_worker()
        sw_path = self.frontend_dir / "public" / "sw.js"
        sw_path.parent.mkdir(exist_ok=True)
        with open(sw_path, 'w') as f:
            f.write(sw_content)
        print(f"✅ Service worker created: {sw_path}")
        
        # 5. Create performance monitoring utilities
        self.create_performance_utils()
        
        # 6. Create build optimization script
        self.create_build_script()
    
    def create_performance_utils(self) -> None:
        """Create performance monitoring utilities"""
        utils_content = '''
// Performance monitoring utilities
export const reportWebVitals = (onPerfEntry?: (metric: any) => void) => {
  if (onPerfEntry && onPerfEntry instanceof Function) {
    import('web-vitals').then(({ getCLS, getFID, getFCP, getLCP, getTTFB }) => {
      getCLS(onPerfEntry);
      getFID(onPerfEntry);
      getFCP(onPerfEntry);
      getLCP(onPerfEntry);
      getTTFB(onPerfEntry);
    });
  }
};

// Custom performance tracking
export class PerformanceTracker {
  private static instance: PerformanceTracker;
  private metrics: Map<string, number> = new Map();
  
  static getInstance(): PerformanceTracker {
    if (!PerformanceTracker.instance) {
      PerformanceTracker.instance = new PerformanceTracker();
    }
    return PerformanceTracker.instance;
  }
  
  startTimer(name: string): void {
    this.metrics.set(name, performance.now());
  }
  
  endTimer(name: string): number {
    const startTime = this.metrics.get(name);
    if (!startTime) return 0;
    
    const duration = performance.now() - startTime;
    this.metrics.delete(name);
    
    // Send to analytics if needed
    this.reportMetric(name, duration);
    return duration;
  }
  
  private reportMetric(name: string, duration: number): void {
    // Report to analytics service
    if (process.env.NODE_ENV === 'production') {
      // Example: gtag('event', 'performance_metric', {
      //   metric_name: name,
      //   metric_value: duration
      // });
    }
  }
}

// React hook for performance tracking
export const usePerformanceTracking = () => {
  const tracker = PerformanceTracker.getInstance();
  
  return {
    startTimer: tracker.startTimer.bind(tracker),
    endTimer: tracker.endTimer.bind(tracker)
  };
};
'''
        
        utils_path = self.frontend_dir / "src" / "utils" / "performance.ts"
        with open(utils_path, 'w') as f:
            f.write(utils_content)
        print(f"✅ Performance utilities created: {utils_path}")
    
    def create_build_script(self) -> None:
        """Create optimized build script"""
        build_script_content = '''
#!/bin/bash
# Optimized build script for ModPorter AI frontend

echo "🚀 Starting optimized frontend build..."

# Clean previous build
rm -rf dist

# Run type checking
echo "🔍 Running type checking..."
pnpm run type-check

# Run linting
echo "🧹 Running linting..."
pnpm run lint

# Run unit tests
echo "🧪 Running unit tests..."
pnpm run test:ci

# Build application
echo "📦 Building application..."
pnpm run build

# Analyze bundle size
echo "📊 Analyzing bundle size..."
if [ -f "dist/index.html" ]; then
    npx bundlesize
fi

# Generate bundle analyzer report
echo "📈 Generating bundle analyzer..."
npx vite-bundle-analyzer dist/static/js/*.js --mode=json --output=bundle-analysis.json

echo "✅ Build completed successfully!"
echo "📄 Bundle analysis saved to bundle-analysis.json"
'''
        
        build_script_path = self.frontend_dir / "scripts" / "build.sh"
        build_script_path.parent.mkdir(exist_ok=True)
        with open(build_script_path, 'w') as f:
            f.write(build_script_content)
        
        # Make script executable
        os.chmod(build_script_path, 0o755)
        print(f"✅ Build script created: {build_script_path}")
    
    async def generate_performance_report(self) -> FrontendPerformanceMetrics:
        """Generate comprehensive frontend performance report"""
        print("🚀 Starting frontend performance analysis...\n")
        
        # Analyze dependencies
        dependency_analysis = self.analyze_dependencies()
        
        # Analyze bundle structure
        bundle_analysis = self.analyze_bundle_structure()
        
        # Generate optimization suggestions
        suggestions = self.generate_optimization_suggestions(dependency_analysis, bundle_analysis)
        
        # Run Lighthouse audit if available
        lighthouse_result = await self.run_lighthouse_audit()
        
        # Calculate metrics
        bundle_size_kb = bundle_analysis.get("total_bundle_size_kb", 0)
        chunk_count = bundle_analysis.get("chunk_count", 0)
        largest_chunk_kb = bundle_analysis.get("largest_chunk_kb", 0)
        dependencies_count = dependency_analysis.get("total_dependencies", 0)
        unused_deps = dependency_analysis.get("unused_dependencies", [])
        
        metrics = FrontendPerformanceMetrics(
            bundle_size_kb=bundle_size_kb,
            chunk_count=chunk_count,
            largest_chunk_kb=largest_chunk_kb,
            dependencies_count=dependencies_count,
            unused_dependencies=unused_deps,
            optimization_suggestions=suggestions,
            lighthouse_score=lighthouse_result["performance_score"] if lighthouse_result else None
        )
        
        return metrics
    
    def save_optimization_report(self, metrics: FrontendPerformanceMetrics) -> None:
        """Save optimization report to file"""
        report = {
            "timestamp": "2024-01-01T00:00:00Z",  # Would use actual timestamp
            "metrics": {
                "bundle_size_kb": metrics.bundle_size_kb,
                "chunk_count": metrics.chunk_count,
                "largest_chunk_kb": metrics.largest_chunk_kb,
                "dependencies_count": metrics.dependencies_count,
                "unused_dependencies": metrics.unused_dependencies,
                "lighthouse_score": metrics.lighthouse_score
            },
            "optimization_suggestions": metrics.optimization_suggestions
        }
        
        report_path = Path("frontend-performance-report.json")
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"📄 Performance report saved: {report_path}")

async def main():
    """Main function"""
    analyze_only = False
    
    if len(sys.argv) > 1:
        if sys.argv[1] in ["-h", "--help"]:
            print("Usage: python optimize-frontend-performance.py [--analyze-only]")
            print("  --analyze-only: Only run analysis without applying optimizations")
            return
        if sys.argv[1] == "--analyze-only":
            analyze_only = True
    
    optimizer = FrontendPerformanceOptimizer()
    
    # Run performance analysis
    metrics = await optimizer.generate_performance_report()
    
    # Print results
    print("\n" + "="*60)
    print("🎨 FRONTEND PERFORMANCE ANALYSIS RESULTS")
    print("="*60)
    print(f"📦 Bundle Size: {metrics.bundle_size_kb:.1f} KB")
    print(f"🧩 Chunks: {metrics.chunk_count}")
    print(f"📏 Largest Chunk: {metrics.largest_chunk_kb:.1f} KB")
    print(f"📚 Dependencies: {metrics.dependencies_count}")
    if metrics.lighthouse_score:
        print(f"🚀 Lighthouse Score: {metrics.lighthouse_score}")
    
    if metrics.unused_dependencies:
        print(f"\n🧹 Unused Dependencies:")
        for dep in metrics.unused_dependencies:
            print(f"   • {dep}")
    
    print(f"\n💡 Optimization Suggestions:")
    for suggestion in metrics.optimization_suggestions[:5]:  # Top 5
        print(f"   {suggestion}")
    
    # Apply optimizations if requested
    if not analyze_only:
        print(f"\n🔧 Applying optimizations...")
        optimizer.apply_optimizations()
        optimizer.save_optimization_report(metrics)
        
        print(f"\n✅ Frontend optimizations applied!")
        print(f"📄 Next steps:")
        print(f"   1. Run 'pnpm install' to update dependencies")
        print(f"   2. Run 'pnpm run build' to test optimized build")
        print(f"   3. Test application functionality")
        print(f"   4. Monitor performance improvements")
    else:
        print(f"\n📄 Analysis completed. Use without --analyze-only to apply optimizations.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
