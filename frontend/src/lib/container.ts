/**
 * Dependency Injection Container
 * 
 * Centralizes creation and configuration of all services and stores.
 * Provides:
 * - Single point of dependency management
 * - Easy mocking for tests
 * - Loose coupling between components
 * - Clear service registration
 */

import { HttpClient } from '$lib/api/http-client';
import { DefaultSearchApiService, type SearchApiService } from '$lib/services/search.service';
import { DefaultChatApiService, type ChatApiService } from '$lib/services/chat.service';
import { createSearchStore } from '$lib/stores/searchStore';
import { createChatStore } from '$lib/stores/chatStore';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Application container - holds all singleton instances
 */
export class Container {
	private httpClient: HttpClient;
	private searchService: SearchApiService;
	private chatService: ChatApiService;
	private searchStore: any;
	private chatStore: any;

	constructor() {
		// Initialize HTTP client
		this.httpClient = new HttpClient(API_BASE_URL, 30000, 3);

		// Initialize services
		this.searchService = new DefaultSearchApiService();
		this.chatService = new DefaultChatApiService();

		// Initialize stores
		this.searchStore = createSearchStore(this.searchService);
		this.chatStore = createChatStore(this.chatService);
	}

	// Getters for services and stores
	getHttpClient(): HttpClient {
		return this.httpClient;
	}

	getSearchService(): SearchApiService {
		return this.searchService;
	}

	getChatService(): ChatApiService {
		return this.chatService;
	}

	getSearchStore() {
		return this.searchStore;
	}

	getChatStore() {
		return this.chatStore;
	}

	/**
	 * Update API base URL (useful for different environments)
	 */
	setApiBaseUrl(url: string) {
		this.httpClient = new HttpClient(url, 30000, 3);
	}

	/**
	 * Reset to initial state (useful for tests)
	 */
	reset() {
		this.searchStore.clear();
		this.chatStore.clear();
		// SearchService may have clearCache method, but it's optional
		if (typeof (this.searchService as any).clearCache === 'function') {
			(this.searchService as any).clearCache();
		}
	}
}

// Create and export singleton container instance
export const container = new Container();

// Export convenient shortcuts for common usage
export const { getSearchStore, getChatStore, getSearchService, getChatService } = {
	getSearchStore: () => container.getSearchStore(),
	getChatStore: () => container.getChatStore(),
	getSearchService: () => container.getSearchService(),
	getChatService: () => container.getChatService()
};
