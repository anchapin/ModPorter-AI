/**
 * Bundle size report generator
 * Outputs JSON report of bundle sizes for tracking and monitoring
 */

const { readdirSync, statSync, writeFileSync } = require('fs');
const { join } = require('path');
const zlib = require('zlib');

const DIST_DIR = process.argv[2] || './dist';
const WARNING_KB = 500;
const ERROR_KB = 1000;

function getGzippedSize(filePath) {
  try {
    const content = require('fs').readFileSync(filePath);
    return zlib.gzipSync(content).length;
  } catch {
    return 0;
  }
}

function generateReport() {
  const files = [];
  let totalSize = 0;
  let totalSizeGzipped = 0;

  const assetsDir = join(DIST_DIR, 'assets');
  
  try {
    const dirFiles = readdirSync(assetsDir);
    
    for (const file of dirFiles) {
      const filePath = join(assetsDir, file);
      const stat = statSync(filePath);
      
      if (stat.isFile()) {
        const ext = file.split('.').pop()?.toLowerCase() || 'other';
        let type = 'other';
        
        if (ext === 'js') type = 'js';
        else if (ext === 'css') type = 'css';
        else if (ext === 'html') type = 'html';
        
        const size = stat.size;
        const sizeGzipped = getGzippedSize(filePath);
        
        totalSize += size;
        totalSizeGzipped += sizeGzipped;
        
        files.push({
          name: file,
          size,
          sizeGzipped,
          type,
        });
      }
    }
  } catch (error) {
    console.error(`Error reading ${assetsDir}:`, error);
  }

  // Determine status based on thresholds
  const totalSizeKB = totalSize / 1024;
  let status = 'ok';
  
  if (totalSizeKB > ERROR_KB * 15) {
    status = 'error';
  } else if (totalSizeKB > WARNING_KB * 20) {
    status = 'warning';
  }

  const report = {
    timestamp: new Date().toISOString(),
    totalSize,
    totalSizeGzipped,
    files: files.sort((a, b) => b.size - a.size),
    thresholds: {
      warningKB: WARNING_KB,
      errorKB: ERROR_KB,
    },
    status,
  };

  return report;
}

function main() {
  console.log('Generating bundle size report...');
  console.log(`Dist directory: ${DIST_DIR}`);
  
  const report = generateReport();
  
  // Output to console
  console.log('\nBundle Size Report');
  console.log('=================');
  console.log(`Total Size: ${(report.totalSize / 1024).toFixed(2)} KB`);
  console.log(`Total Size (gzipped): ${(report.totalSizeGzipped / 1024).toFixed(2)} KB`);
  console.log(`Status: ${report.status.toUpperCase()}`);
  console.log('\nFiles:');
  
  for (const file of report.files) {
    console.log(`  ${file.name}: ${(file.size / 1024).toFixed(2)} KB (~${(file.sizeGzipped / 1024).toFixed(2)} KB gzipped)`);
  }
  
  // Write JSON report
  const reportPath = join(DIST_DIR, 'bundle-report.json');
  writeFileSync(reportPath, JSON.stringify(report, null, 2));
  console.log(`\nReport saved to: ${reportPath}`);
  
  // Exit with error code if status is error
  if (report.status === 'error') {
    console.error('\n❌ Bundle size exceeds error threshold!');
    process.exit(1);
  } else if (report.status === 'warning') {
    console.warn('\n⚠️ Bundle size exceeds warning threshold!');
  }
}

main();
