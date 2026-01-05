/**
 * HTTP Request and Response Handlers
 * 
 * Separates cross-cutting concerns:
 * - Request header management
 * - Timeout handling
 * - Response parsing and validation
 * - Error mapping
 */

import {
	ApiError,
	NetworkError,
	TimeoutError,
	ServerError,
	ValidationError,
	NotFoundError
} from './errors';

export interface RequestConfig {
	timeout?: number;
	retries?: number;
	headers?: Record<string, string>;
}

/**
 * Handles request preparation and headers
 */
export class RequestHandler {
	/**
	 * Merge custom headers with defaults
	 */
	static addHeaders(headers: HeadersInit = {}, config?: RequestConfig): HeadersInit {
		const merged = {
			'Content-Type': 'application/json',
			...headers
		};

		if (config?.headers) {
			Object.assign(merged, config.headers);
		}

		return merged;
	}

	/**
	 * Create a timeout promise that rejects after specified milliseconds
	 */
	static timeout(ms: number): Promise<never> {
		return new Promise((_, reject) => {
			setTimeout(() => reject(new TimeoutError(`Request timeout after ${ms}ms`)), ms);
		});
	}
}

/**
 * Handles response parsing and error extraction
 */
export class ResponseHandler {
	/**
	 * Parse response JSON with error handling
	 */
	static async parseJson(response: Response): Promise<unknown> {
		try {
			const contentType = response.headers.get('content-type');
			if (contentType?.includes('application/json')) {
				return await response.json();
			}
			return await response.text();
		} catch (error) {
			throw new ApiError(500, 'Failed to parse response body', false, error as Error);
		}
	}

	/**
	 * Validate response status and throw appropriate error
	 */
	static validateOk(response: Response, body: unknown): void {
		if (response.ok) {
			return;
		}

		const bodyObj = typeof body === 'object' ? body : null;
		const detail = bodyObj && 'detail' in bodyObj ? (bodyObj as any).detail : null;
		const message = bodyObj && 'message' in bodyObj ? (bodyObj as any).message : null;
		const errorMessage = detail || message || response.statusText || 'Unknown error';

		if (response.status === 404) {
			throw new NotFoundError(String(errorMessage));
		}

		if (response.status === 400) {
			const validationDetails =
				bodyObj && 'validation_errors' in bodyObj ? (bodyObj as any).validation_errors : undefined;
			throw new ValidationError(String(errorMessage), validationDetails);
		}

		if (response.status === 401 || response.status === 403) {
			throw new ApiError(response.status, String(errorMessage), false);
		}

		if (response.status >= 500) {
			throw new ServerError(response.status, String(errorMessage));
		}

		throw new ApiError(response.status, String(errorMessage), false);
	}
}
