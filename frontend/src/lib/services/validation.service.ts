/**
 * Input Validation Utilities
 * 
 * Centralized validation logic for:
 * - Search queries
 * - Chat messages
 * - API responses
 */

import { ApiError } from '$lib/api/errors';

export class ValidationError extends Error {
	constructor(public field: string, message: string) {
		super(message);
		this.name = 'ValidationError';
	}
}

export class SearchQueryValidator {
	static readonly MIN_LENGTH = 1;
	static readonly MAX_LENGTH = 1000;

	static validate(query: string): void {
		const trimmed = query.trim();

		if (trimmed.length === 0) {
			throw new ValidationError('query', 'Search query cannot be empty');
		}

		if (trimmed.length < this.MIN_LENGTH) {
			throw new ValidationError('query', `Query must be at least ${this.MIN_LENGTH} character`);
		}

		if (trimmed.length > this.MAX_LENGTH) {
			throw new ValidationError('query', `Query cannot exceed ${this.MAX_LENGTH} characters`);
		}
	}

	static sanitize(query: string): string {
		return query
			.trim()
			.replace(/\s+/g, ' ')
			.slice(0, this.MAX_LENGTH);
	}
}

export class ChatMessageValidator {
	static readonly MIN_LENGTH = 1;
	static readonly MAX_LENGTH = 5000;

	static validate(message: string): void {
		const trimmed = message.trim();

		if (trimmed.length === 0) {
			throw new ValidationError('message', 'Message cannot be empty');
		}

		if (trimmed.length < this.MIN_LENGTH) {
			throw new ValidationError('message', `Message must be at least ${this.MIN_LENGTH} character`);
		}

		if (trimmed.length > this.MAX_LENGTH) {
			throw new ValidationError('message', `Message cannot exceed ${this.MAX_LENGTH} characters`);
		}
	}

	static sanitize(message: string): string {
		return message
			.trim()
			.slice(0, this.MAX_LENGTH);
	}
}

export class ResponseValidator {
	static isValidSearchResponse(response: unknown): boolean {
		if (!response || typeof response !== 'object') return false;

		const obj = response as Record<string, unknown>;
		return (
			typeof obj.query === 'string' &&
			Array.isArray(obj.results)
		);
	}

	static isValidChatResponse(response: unknown): boolean {
		if (!response || typeof response !== 'object') return false;

		const obj = response as Record<string, unknown>;
		return (
			obj.message !== undefined &&
			(obj.sources === undefined || Array.isArray(obj.sources))
		);
	}
}
