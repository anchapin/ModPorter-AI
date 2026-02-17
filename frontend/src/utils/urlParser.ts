/**
 * URL Parser utility for CurseForge and Modrinth URLs
 */

export interface ParsedModURL {
  platform: 'curseforge' | 'modrinth' | 'unknown';
  slug: string;
  url: string;
  isValid: boolean;
  error?: string;
}

/**
 * Parse a CurseForge or Modrinth URL to extract mod information
 * 
 * Supports URLs like:
 * - https://www.curseforge.com/minecraft/mods/mod-name
 * - https://curseforge.com/minecraft/mods/mod-name
 * - https://modrinth.com/mod/mod-name
 * - https://modrinth.com/resourcepack/resourcepack-name
 * - https://modrinth.com/plugin/plugin-name
 */
export function parseModUrl(url: string): ParsedModURL {
  if (!url || typeof url !== 'string') {
    return {
      platform: 'unknown',
      slug: '',
      url: url || '',
      isValid: false,
      error: 'URL is required',
    };
  }

  // Try CurseForge patterns
  const curseforgePatterns = [
    /(?:https?:\/\/)?(?:www\.)?curseforge\.com\/minecraft\/mods\/([^\/?]+)/i,
    /(?:https?:\/\/)?(?:www\.)?curseforge\.com\/minecraft\/modpacks\/([^\/?]+)/i,  // Modpacks
  ];

  for (const pattern of curseforgePatterns) {
    const match = url.match(pattern);
    if (match) {
      const slug = match[1];
      return {
        platform: 'curseforge',
        slug,
        url: `https://www.curseforge.com/minecraft/mods/${slug}`,
        isValid: true,
      };
    }
  }

  // Try Modrinth patterns
  const modrinthPatterns = [
    /(?:https?:\/\/)?(?:www\.)?modrinth\.com\/(mod|resourcepack|plugin|pack)\/([^\/?]+)/i,
    /(?:https?:\/\/)?modrinth\.com\/([^\/?]+)/i,  // Short URL
  ];

  for (const pattern of modrinthPatterns) {
    const match = url.match(pattern);
    if (match) {
      if (match.length >= 3) {
        // Type and slug
        const projectType = match[1];
        const slug = match[2];
        return {
          platform: 'modrinth',
          slug,
          url: `https://modrinth.com/${projectType}/${slug}`,
          isValid: true,
        };
      } else {
        // Short URL - assume mod
        const slug = match[1];
        return {
          platform: 'modrinth',
          slug,
          url: `https://modrinth.com/mod/${slug}`,
          isValid: true,
        };
      }
    }
  }

  return {
    platform: 'unknown',
    slug: '',
    url,
    isValid: false,
    error: 'Unable to parse URL. Supported platforms: CurseForge, Modrinth',
  };
}

/**
 * Get platform display name
 */
export function getPlatformDisplayName(platform: 'curseforge' | 'modrinth' | 'unknown'): string {
  switch (platform) {
    case 'curseforge':
      return 'CurseForge';
    case 'modrinth':
      return 'Modrinth';
    default:
      return 'Unknown';
  }
}

/**
 * Get platform icon/color
 */
export function getPlatformInfo(platform: 'curseforge' | 'modrinth' | 'unknown'): {
  name: string;
  color: string;
  bgColor: string;
} {
  switch (platform) {
    case 'curseforge':
      return {
        name: 'CurseForge',
        color: '#f16436',
        bgColor: 'rgba(241, 100, 54, 0.1)',
      };
    case 'modrinth':
      return {
        name: 'Modrinth',
        color: '#00b5a0',
        bgColor: 'rgba(0, 181, 160, 0.1)',
      };
    default:
      return {
        name: 'Unknown',
        color: '#6b7280',
        bgColor: 'rgba(107, 114, 128, 0.1)',
      };
  }
}

/**
 * Format download count
 */
export function formatDownloadCount(count?: number): string {
  if (!count || count === 0) return '0';
  
  if (count >= 1000000) {
    return `${(count / 1000000).toFixed(1)}M`;
  }
  if (count >= 1000) {
    return `${(count / 1000).toFixed(1)}K`;
  }
  return count.toString();
}

/**
 * Format file size
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
}
