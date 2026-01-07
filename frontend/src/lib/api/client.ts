import type { SearchResponse, ChatResponse, ChatMessage } from './types';
import { HttpClient } from './http-client';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const httpClient = new HttpClient(API_BASE_URL, 30000, 3);

/**
 * Search for datasets
 */
export async function searchDatasets(query: string, limit: number = 10): Promise<SearchResponse> {
	return httpClient.request<SearchResponse>('/api/search', {
		method: 'POST',
		body: {
			query,
			top_k: limit
		},
		config: { timeout: 30000, retries: 2 }
	});
}

/**
 * Send a chat message
 */
export async function sendChatMessage(
	message: string,
	history: ChatMessage[] = []
): Promise<ChatResponse> {
	return httpClient.request<ChatResponse>('/api/chat/send', {
		method: 'POST',
		body: {
			messages: [...history, { role: 'user', content: message }]
		},
		config: { timeout: 60000, retries: 1 }
	});
}

/**
 * Get all datasets (paginated)
 */
export async function getDatasets(limit: number = 20, offset: number = 0) {
	return httpClient.request('/api/datasets', {
		method: 'GET',
		config: { timeout: 15000, retries: 2 }
	});
}

/**
 * Get single dataset by ID
 */
export async function getDatasetById(fileIdentifier: string) {
	return httpClient.request(`/api/datasets/${fileIdentifier}`, {
		method: 'GET',
		config: { timeout: 15000, retries: 2 }
	});
}

/**
 * Get related datasets
 */
export async function getRelatedDatasets(fileIdentifier: string, limit: number = 5) {
	return httpClient.request(`/api/datasets/${fileIdentifier}/related`, {
		method: 'GET',
		config: { timeout: 20000, retries: 2 }
	});
}

/**
 * Get search suggestions
 */
export async function getSearchSuggestions(query: string, limit: number = 5) {
	const params = new URLSearchParams({ q: query });
	const response = await httpClient.request<{ suggestions: string[] }>(`/api/search/suggestions?${params.toString()}`, {
		method: 'GET',
		config: { timeout: 10000, retries: 2 }
	});
	return response.suggestions || [];
}

/**
 * Check API health
 */
export async function checkHealth() {
	return httpClient.request('/api/health', {
		method: 'GET',
		config: { timeout: 5000, retries: 1 }
	});
}

export default {
	searchDatasets,
	sendChatMessage,
	getDatasets,
	getDatasetById,
	checkHealth
};
