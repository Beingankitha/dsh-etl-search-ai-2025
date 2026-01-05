/**
 * HTTP Client with Retry Logic
 * 
 * Provides resilient HTTP operations with:
 * - Automatic retry for transient failures
 * - Exponential backoff
 * - Timeout handling
 * - Comprehensive error handling
 * - Request/response transformation hooks
 */

import { ResponseHandler, RequestHandler, type RequestConfig } from './handlers';
import { ApiError, NetworkError, TimeoutError, isRetryable } from './errors';

export interface HttpRequestOptions {
	method?: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
	body?: unknown;
	config?: RequestConfig;
}

export class HttpClient {
	private readonly baseUrl: string;
	private readonly defaultTimeout: number;
	private readonly maxRetries: number;

	constructor(baseUrl: string, defaultTimeout: number = 30000, maxRetries: number = 3) {
		this.baseUrl = baseUrl;
		this.defaultTimeout = defaultTimeout;
		this.maxRetries = maxRetries;
	}

	/**
	 * Make HTTP request with retry logic
	 */
	async request<T>(
		endpoint: string,
		options: HttpRequestOptions = {}
	): Promise<T> {
		const { method = 'GET', body, config = {} } = options;
		const timeout = config.timeout ?? this.defaultTimeout;
		const retries = config.retries ?? this.maxRetries;

		return this.requestWithRetry<T>(endpoint, method, body, timeout, retries, 0);
	}

	private async requestWithRetry<T>(
		endpoint: string,
		method: string,
		body: unknown,
		timeout: number,
		maxRetries: number,
		attempt: number
	): Promise<T> {
		try {
			return await this.executeRequest<T>(endpoint, method, body, timeout);
		} catch (error) {
			const normalizedError = this.normalizeError(error);

			// Retry logic
			if (isRetryable(normalizedError) && attempt < maxRetries) {
				const delay = this.calculateBackoff(attempt);
				await this.sleep(delay);
				return this.requestWithRetry<T>(endpoint, method, body, timeout, maxRetries, attempt + 1);
			}

			throw normalizedError;
		}
	}

	private async executeRequest<T>(
		endpoint: string,
		method: string,
		body: unknown,
		timeout: number
	): Promise<T> {
		const url = `${this.baseUrl}${endpoint}`;
		const headers = RequestHandler.addHeaders();

		const fetchOptions: RequestInit = {
			method,
			headers
		};

		if (body) {
			fetchOptions.body = JSON.stringify(body);
		}

		try {
			// Race between fetch and timeout
			const response = await Promise.race([
				fetch(url, fetchOptions),
				RequestHandler.timeout(timeout)
			]);

			const responseBody = await ResponseHandler.parseJson(response);
			ResponseHandler.validateOk(response, responseBody);

			return responseBody as T;
		} catch (error) {
			throw this.normalizeError(error);
		}
	}

	private normalizeError(error: unknown): ApiError {
		if (error instanceof ApiError) {
			return error;
		}

		if (error instanceof TypeError) {
			return new NetworkError(`Network error: ${error.message}`, error);
		}

		if (error instanceof TimeoutError) {
			return error;
		}

		if (error instanceof Error) {
			return new ApiError(500, error.message, false, error);
		}

		return new ApiError(500, 'Unknown error occurred', false);
	}

	private calculateBackoff(attempt: number): number {
		// Exponential backoff: 100ms, 200ms, 400ms, ...
		const delayMs = 100 * Math.pow(2, attempt);
		// Add jitter (±20%)
		const jitter = delayMs * 0.2 * (Math.random() - 0.5);
		return delayMs + jitter;
	}

	private sleep(ms: number): Promise<void> {
		return new Promise((resolve) => setTimeout(resolve, ms));
	}
}
