/**
 * Input Validation Utilities
 * 
 * Provides client-side validation for search queries and API inputs
 * to prevent errors and provide better user feedback.
 * 
 * Usage:
 *   import { validateSearchQuery, validateTopK } from '$lib/validation';
 *   
 *   const error = validateSearchQuery(userInput);
 *   if (error) {
 *     showError(error);
 *     return;
 *   }
 */

export interface ValidationError {
  field: string;
  message: string;
  code: string;
}

/**
 * Validate search query input
 * 
 * Rules:
 * - Required (non-empty after trim)
 * - Min 1 character
 * - Max 1000 characters
 * - No special injection characters
 */
export function validateSearchQuery(query: string | null | undefined): ValidationError | null {
  if (!query) {
    return {
      field: 'query',
      message: 'Search query is required',
      code: 'QUERY_REQUIRED'
    };
  }

  const trimmed = query.trim();

  if (trimmed.length === 0) {
    return {
      field: 'query',
      message: 'Search query cannot be empty',
      code: 'QUERY_EMPTY'
    };
  }

  if (trimmed.length < 1) {
    return {
      field: 'query',
      message: 'Search query must be at least 1 character',
      code: 'QUERY_TOO_SHORT'
    };
  }

  if (trimmed.length > 1000) {
    return {
      field: 'query',
      message: 'Search query must be less than 1000 characters',
      code: 'QUERY_TOO_LONG'
    };
  }

  // Check for potentially malicious patterns (basic check)
  const dangerousPatterns = [
    /<script/i,           // Script injection
    /javascript:/i,       // JavaScript protocol
    /on\w+=/i,           // Event handlers
    /['";]/,             // SQL injection indicators (basic)
  ];

  for (const pattern of dangerousPatterns) {
    if (pattern.test(trimmed)) {
      return {
        field: 'query',
        message: 'Search query contains invalid characters',
        code: 'QUERY_INVALID_CHARS'
      };
    }
  }

  return null;
}

/**
 * Validate top_k parameter (number of results)
 * 
 * Rules:
 * - Must be an integer
 * - Min 1
 * - Max 100
 */
export function validateTopK(topK: any): ValidationError | null {
  if (topK === null || topK === undefined) {
    return {
      field: 'top_k',
      message: 'Number of results is required',
      code: 'TOP_K_REQUIRED'
    };
  }

  const num = Number(topK);

  if (isNaN(num)) {
    return {
      field: 'top_k',
      message: 'Number of results must be a number',
      code: 'TOP_K_NOT_NUMBER'
    };
  }

  if (!Number.isInteger(num)) {
    return {
      field: 'top_k',
      message: 'Number of results must be an integer',
      code: 'TOP_K_NOT_INTEGER'
    };
  }

  if (num < 1) {
    return {
      field: 'top_k',
      message: 'Number of results must be at least 1',
      code: 'TOP_K_TOO_SMALL'
    };
  }

  if (num > 100) {
    return {
      field: 'top_k',
      message: 'Number of results must be at most 100',
      code: 'TOP_K_TOO_LARGE'
    };
  }

  return null;
}

/**
 * Validate complete search request
 */
export function validateSearchRequest(request: {
  query?: string;
  top_k?: any;
}): ValidationError[] {
  const errors: ValidationError[] = [];

  const queryError = validateSearchQuery(request.query);
  if (queryError) errors.push(queryError);

  const topKError = validateTopK(request.top_k ?? 10);
  if (topKError) errors.push(topKError);

  return errors;
}

/**
 * Validate API response structure for search results
 */
export function validateSearchResponse(data: any): ValidationError[] {
  const errors: ValidationError[] = [];

  if (!Array.isArray(data)) {
    errors.push({
      field: 'response',
      message: 'Expected array of results',
      code: 'INVALID_RESPONSE_FORMAT'
    });
    return errors;
  }

  // Validate each result
  for (let i = 0; i < data.length; i++) {
    const result = data[i];

    if (!result.dataset) {
      errors.push({
        field: `results[${i}].dataset`,
        message: 'Result missing dataset',
        code: 'MISSING_DATASET'
      });
    }

    if (typeof result.score !== 'number' || result.score < 0 || result.score > 1) {
      errors.push({
        field: `results[${i}].score`,
        message: 'Invalid relevance score (must be 0-1)',
        code: 'INVALID_SCORE'
      });
    }

    if (!result.dataset.file_identifier) {
      errors.push({
        field: `results[${i}].dataset.file_identifier`,
        message: 'Dataset missing file identifier',
        code: 'MISSING_IDENTIFIER'
      });
    }
  }

  return errors;
}

/**
 * Sanitize search query for safe display
 * Removes/escapes potentially problematic characters
 */
export function sanitizeQuery(query: string): string {
  return query
    .replace(/[<>]/g, '')  // Remove angle brackets
    .replace(/"/g, '&quot;')  // Escape quotes
    .substring(0, 500);  // Limit display length
}

/**
 * Format error message for user display
 */
export function formatValidationError(error: ValidationError): string {
  return error.message;
}
