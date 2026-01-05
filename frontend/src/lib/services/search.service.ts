/**
 * Search API Service
 * 
 * Encapsulates search operations with:
 * - Input validation
 * - Error handling
 * - Response transformation
 * - Query caching (optional)
 */

import * as apiClient from '$lib/api/client';
import type { SearchResponse, SearchResult } from '$lib/api/types';
import { ApiError } from '$lib/api/errors';

export interface SearchApiService {
	search(query: string, limit?: number): Promise<SearchResponse>;
	getSuggestions(query: string, limit?: number): Promise<string[]>;
}

export class DefaultSearchApiService implements SearchApiService {
	private queryCache: Map<string, SearchResponse> = new Map();
	private readonly CACHE_TTL = 5 * 60 * 1000; // 5 minutes
	private cacheExpiry: Map<string, number> = new Map();

	async search(query: string, limit: number = 10): Promise<SearchResponse> {
		// Validate input
		const sanitizedQuery = this.sanitizeQuery(query);
		if (!sanitizedQuery) {
			throw new ApiError(400, 'Search query cannot be empty', false);
		}

		// Check cache
		const cached = this.getFromCache(sanitizedQuery);
		if (cached) {
			return cached;
		}

		try {
			const response = await apiClient.searchDatasets(sanitizedQuery, limit);

			// Cache result
			this.setCache(sanitizedQuery, response);

			return response;
		} catch (error) {
			if (error instanceof ApiError) {
				throw error;
			}
			throw new ApiError(500, `Search failed: ${error instanceof Error ? error.message : 'Unknown error'}`, false);
		}
	}

	async getSuggestions(query: string, limit: number = 5): Promise<string[]> {
		const sanitizedQuery = this.sanitizeQuery(query);
		if (!sanitizedQuery || sanitizedQuery.length < 2) {
			return [];
		}

		try {
			const response = await apiClient.getSearchSuggestions(sanitizedQuery, limit);
			// Ensure we return string array
			return Array.isArray(response) ? response : [];
		} catch (error) {
			console.warn('Failed to get suggestions:', error);
			return [];
		}
	}

	clearCache(): void {
		this.queryCache.clear();
		this.cacheExpiry.clear();
	}

	private sanitizeQuery(query: string): string {
		return query
			.trim()
			.replace(/\s+/g, ' ')
			.slice(0, 1000);
	}

	private getFromCache(key: string): SearchResponse | null {
		const expiry = this.cacheExpiry.get(key);
		if (expiry && Date.now() > expiry) {
			this.queryCache.delete(key);
			this.cacheExpiry.delete(key);
			return null;
		}
		return this.queryCache.get(key) ?? null;
	}

	private setCache(key: string, value: SearchResponse): void {
		this.queryCache.set(key, value);
		this.cacheExpiry.set(key, Date.now() + this.CACHE_TTL);
	}
}
