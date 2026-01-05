/**
 * API Error Hierarchy
 * 
 * Structured error handling for API operations with:
 * - Status codes for HTTP errors
 * - Retryable flag for transient failures
 * - Cause chain for debugging
 */

export class ApiError extends Error {
	constructor(
		public status: number,
		message: string,
		public retryable: boolean = false,
		public cause?: Error
	) {
		super(message);
		this.name = 'ApiError';
		Object.setPrototypeOf(this, ApiError.prototype);
	}
}

/**
 * Network-related errors (transient, retryable)
 */
export class NetworkError extends ApiError {
	constructor(message: string, cause?: Error) {
		super(0, message, true, cause);
		this.name = 'NetworkError';
		Object.setPrototypeOf(this, NetworkError.prototype);
	}
}

/**
 * Request validation errors (client error, not retryable)
 */
export class ValidationError extends ApiError {
	constructor(message: string, public details?: Record<string, string>) {
		super(400, message, false);
		this.name = 'ValidationError';
		Object.setPrototypeOf(this, ValidationError.prototype);
	}
}

/**
 * Authentication/Authorization errors (not retryable)
 */
export class AuthError extends ApiError {
	constructor(status: number, message: string) {
		super(status, message, false);
		this.name = 'AuthError';
		Object.setPrototypeOf(this, AuthError.prototype);
	}
}

/**
 * Server errors (5xx, retryable)
 */
export class ServerError extends ApiError {
	constructor(status: number, message: string) {
		super(status, message, status >= 500);
		this.name = 'ServerError';
		Object.setPrototypeOf(this, ServerError.prototype);
	}
}

/**
 * Request timeout errors (retryable)
 */
export class TimeoutError extends ApiError {
	constructor(message: string = 'Request timeout') {
		super(408, message, true);
		this.name = 'TimeoutError';
		Object.setPrototypeOf(this, TimeoutError.prototype);
	}
}

/**
 * Not found errors (not retryable)
 */
export class NotFoundError extends ApiError {
	constructor(message: string = 'Resource not found') {
		super(404, message, false);
		this.name = 'NotFoundError';
		Object.setPrototypeOf(this, NotFoundError.prototype);
	}
}

/**
 * Check if an error is retryable
 */
export function isRetryable(error: unknown): boolean {
	if (error instanceof ApiError) {
		return error.retryable;
	}
	return false;
}
