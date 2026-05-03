/**
 * Error types for conversion failures
 * Used to categorize errors and provide user-friendly messages
 */

export enum ConversionErrorType {
  UNSUPPORTED_MOD_TYPE = 'UNSUPPORTED_MOD_TYPE',
  CONVERSION_TIMEOUT = 'CONVERSION_TIMEOUT',
  AI_ENGINE_UNAVAILABLE = 'AI_ENGINE_UNAVAILABLE',
  FILE_TOO_LARGE = 'FILE_TOO_LARGE',
  INVALID_FILE_FORMAT = 'INVALID_FILE_FORMAT',
  PARTIAL_CONVERSION = 'PARTIAL_CONVERSION',
  NETWORK_ERROR = 'NETWORK_ERROR',
  FILE_UPLOAD_FAILED = 'FILE_UPLOAD_FAILED',
  JOB_NOT_FOUND = 'JOB_NOT_FOUND',
  PERMISSION_DENIED = 'PERMISSION_DENIED',
  QUOTA_EXCEEDED = 'QUOTA_EXCEEDED',
  INTERNAL_ERROR = 'INTERNAL_ERROR',
  UNKNOWN = 'UNKNOWN',
}

export interface UserFriendlyError {
  type: ConversionErrorType;
  title: string;
  message: string;
  userTips: string[];
  retryable: boolean;
  reportToSentry: boolean;
}

/**
 * Categorize error code/message into a conversion error type
 */
export function categorizeError(error: unknown): ConversionErrorType {
  const errorString = String(error).toLowerCase();

  if (
    errorString.includes('unsupported') ||
    errorString.includes('mod type') ||
    errorString.includes('not supported')
  ) {
    return ConversionErrorType.UNSUPPORTED_MOD_TYPE;
  }

  if (
    errorString.includes('timeout') ||
    errorString.includes('timed out') ||
    errorString.includes('deadline')
  ) {
    return ConversionErrorType.CONVERSION_TIMEOUT;
  }

  if (
    errorString.includes('ai') ||
    errorString.includes('engine') ||
    errorString.includes('openai') ||
    errorString.includes('anthropic') ||
    errorString.includes('service unavailable')
  ) {
    return ConversionErrorType.AI_ENGINE_UNAVAILABLE;
  }

  if (
    errorString.includes('file too large') ||
    errorString.includes('size limit') ||
    errorString.includes('exceeds')
  ) {
    return ConversionErrorType.FILE_TOO_LARGE;
  }

  if (
    errorString.includes('invalid') ||
    errorString.includes('format') ||
    errorString.includes('corrupted') ||
    errorString.includes('not a valid')
  ) {
    return ConversionErrorType.INVALID_FILE_FORMAT;
  }

  if (
    errorString.includes('partial') ||
    errorString.includes('some features') ||
    errorString.includes('skipped')
  ) {
    return ConversionErrorType.PARTIAL_CONVERSION;
  }

  if (
    errorString.includes('network') ||
    errorString.includes('connection') ||
    errorString.includes('fetch') ||
    errorString.includes('econnrefused')
  ) {
    return ConversionErrorType.NETWORK_ERROR;
  }

  if (errorString.includes('upload') || errorString.includes('upload failed')) {
    return ConversionErrorType.FILE_UPLOAD_FAILED;
  }

  if (
    errorString.includes('not found') ||
    errorString.includes('job not found')
  ) {
    return ConversionErrorType.JOB_NOT_FOUND;
  }

  if (
    errorString.includes('permission') ||
    errorString.includes('denied') ||
    errorString.includes('unauthorized')
  ) {
    return ConversionErrorType.PERMISSION_DENIED;
  }

  if (
    errorString.includes('quota') ||
    errorString.includes('limit') ||
    errorString.includes('exceeded') ||
    errorString.includes('monthly') ||
    errorString.includes('conversions') ||
    errorString.includes('used all')
  ) {
    return ConversionErrorType.QUOTA_EXCEEDED;
  }

  if (
    errorString.includes('internal') ||
    errorString.includes('server error') ||
    errorString.includes('500')
  ) {
    return ConversionErrorType.INTERNAL_ERROR;
  }

  return ConversionErrorType.UNKNOWN;
}

/**
 * Get user-friendly error information based on error type
 */
export function getUserFriendlyError(
  errorType: ConversionErrorType,
  originalError?: string
): UserFriendlyError {
  const errors: Record<ConversionErrorType, UserFriendlyError> = {
    [ConversionErrorType.UNSUPPORTED_MOD_TYPE]: {
      type: ConversionErrorType.UNSUPPORTED_MOD_TYPE,
      title: 'Unsupported Mod Type',
      message:
        'This mod type is not supported for conversion yet. We may be adding support for it in the future.',
      userTips: [
        'Check if there is an updated version of this mod',
        'Look for Bedrock Edition alternatives on CurseForge or Modrinth',
        'File an issue on GitHub to request support for this mod type',
      ],
      retryable: false,
      reportToSentry: true,
    },

    [ConversionErrorType.CONVERSION_TIMEOUT]: {
      type: ConversionErrorType.CONVERSION_TIMEOUT,
      title: 'Conversion Timed Out',
      message:
        'The conversion process took too long and was stopped. Large or complex mods may timeout.',
      userTips: [
        'Try a smaller or simpler mod first',
        'Enable "Smart Assumptions" for faster conversions',
        'Try during off-peak hours when server load is lower',
        'Contact support if this keeps happening',
      ],
      retryable: true,
      reportToSentry: true,
    },

    [ConversionErrorType.AI_ENGINE_UNAVAILABLE]: {
      type: ConversionErrorType.AI_ENGINE_UNAVAILABLE,
      title: 'AI Service Temporarily Unavailable',
      message:
        'Our AI conversion service is currently down or overloaded. Please try again in a few minutes.',
      userTips: [
        'Wait a few minutes and try again',
        'Check our status page at status.portkit.cloud',
        'Try with fewer files in batch mode',
      ],
      retryable: true,
      reportToSentry: true,
    },

    [ConversionErrorType.FILE_TOO_LARGE]: {
      type: ConversionErrorType.FILE_TOO_LARGE,
      title: 'File Too Large',
      message:
        'The file exceeds the maximum allowed size. Large modpacks may need to be split.',
      userTips: [
        'Maximum file size is 100MB',
        'Try splitting large modpacks into smaller parts',
        'Remove unnecessary files or dependencies',
        'Consider converting mods individually',
      ],
      retryable: false,
      reportToSentry: false,
    },

    [ConversionErrorType.INVALID_FILE_FORMAT]: {
      type: ConversionErrorType.INVALID_FILE_FORMAT,
      title: 'Invalid File Format',
      message:
        'The file is not a valid Minecraft mod archive. Please ensure it is a .jar or .zip file.',
      userTips: [
        'Verify the file is a valid Minecraft Java Edition mod',
        'Check that the file is not corrupted or truncated',
        'Try re-downloading the mod',
        'Supported formats: .jar, .zip, .mcaddon',
      ],
      retryable: false,
      reportToSentry: false,
    },

    [ConversionErrorType.PARTIAL_CONVERSION]: {
      type: ConversionErrorType.PARTIAL_CONVERSION,
      title: 'Partial Conversion',
      message:
        'Some features of the mod could not be converted. The conversion completed with warnings.',
      userTips: [
        'View the detailed report to see what was skipped',
        'Manually convert skipped features if possible',
        'Enable "Smart Assumptions" for better compatibility',
        'Some features may require manual editing',
      ],
      retryable: true,
      reportToSentry: false,
    },

    [ConversionErrorType.NETWORK_ERROR]: {
      type: ConversionErrorType.NETWORK_ERROR,
      title: 'Network Error',
      message:
        'A network error occurred during the conversion process. Please check your connection.',
      userTips: [
        'Check your internet connection',
        'Try again in a few minutes',
        'Disable VPN or proxy if using one',
        'Firewall may be blocking our servers',
      ],
      retryable: true,
      reportToSentry: false,
    },

    [ConversionErrorType.FILE_UPLOAD_FAILED]: {
      type: ConversionErrorType.FILE_UPLOAD_FAILED,
      title: 'Upload Failed',
      message:
        'The file could not be uploaded. Please try again with a smaller file or check your connection.',
      userTips: [
        'Try uploading the file again',
        'Check that the file is not corrupted',
        'Try with a different browser',
        'Disable browser extensions that may interfere',
      ],
      retryable: true,
      reportToSentry: false,
    },

    [ConversionErrorType.JOB_NOT_FOUND]: {
      type: ConversionErrorType.JOB_NOT_FOUND,
      title: 'Conversion Job Not Found',
      message:
        'The conversion job could not be found. It may have expired or been deleted.',
      userTips: [
        'Start a new conversion',
        'Conversions are kept for 24 hours',
        'Save your results locally after downloading',
      ],
      retryable: false,
      reportToSentry: false,
    },

    [ConversionErrorType.PERMISSION_DENIED]: {
      type: ConversionErrorType.PERMISSION_DENIED,
      title: 'Permission Denied',
      message:
        'You do not have permission to perform this action. Please log in or check your subscription.',
      userTips: [
        'Log in to your account',
        'Check your subscription status',
        'Contact support if you believe this is an error',
      ],
      retryable: false,
      reportToSentry: false,
    },

    [ConversionErrorType.QUOTA_EXCEEDED]: {
      type: ConversionErrorType.QUOTA_EXCEEDED,
      title: 'Conversion Limit Reached',
      message:
        "You've used all your conversions this month. Upgrade to continue converting mods.",
      userTips: [
        'Check your current plan limits',
        'Upgrade to a higher tier for more conversions',
        'Contact support if you need more conversions',
      ],
      retryable: false,
      reportToSentry: true,
    },

    [ConversionErrorType.INTERNAL_ERROR]: {
      type: ConversionErrorType.INTERNAL_ERROR,
      title: 'Server Error',
      message:
        'Something went wrong on our servers. This has been automatically reported to our team.',
      userTips: [
        'Try again in a few minutes',
        'If the problem persists, contact support',
        'Include the job ID if requesting help',
      ],
      retryable: true,
      reportToSentry: true,
    },

    [ConversionErrorType.UNKNOWN]: {
      type: ConversionErrorType.UNKNOWN,
      title: 'Conversion Failed',
      message:
        originalError ||
        'An unexpected error occurred during conversion. Please try again.',
      userTips: [
        'Try again with the same file',
        'Check that the mod is compatible with Minecraft Java Edition',
        'Contact support if the problem persists',
      ],
      retryable: true,
      reportToSentry: true,
    },
  };

  return errors[errorType];
}

/**
 * Process any error and return user-friendly error information
 */
export function processError(error: unknown): UserFriendlyError {
  const errorType = categorizeError(error);
  return getUserFriendlyError(errorType, String(error));
}
