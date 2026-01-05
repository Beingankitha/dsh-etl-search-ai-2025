import { writable, derived } from 'svelte/store';
import type { Dataset, SearchResult } from '$lib/api/types';
import type { SearchApiService } from '$lib/services/search.service';
import { ApiError } from '$lib/api/errors';

interface SearchState {
	query: string;
	results: SearchResult[];
	loading: boolean;
	error: string | null;
	hasSearched: boolean;
}

const initialState: SearchState = {
	query: '',
	results: [],
	loading: false,
	error: null,
	hasSearched: false
};

/**
 * Creates a search store with injected search service
 * This removes the need for function passing and creates proper dependency injection
 */
export function createSearchStore(searchService: SearchApiService) {
	const store = writable<SearchState>(initialState);

	// Derived stores
	const hasResults = derived(store, ($store) => $store.results.length > 0);
	const resultCount = derived(store, ($store) => $store.results.length);
	const isLoading = derived(store, ($store) => $store.loading);
	const hasError = derived(store, ($store) => $store.error !== null);

	return {
		subscribe: store.subscribe,
		hasResults: { subscribe: hasResults.subscribe },
		resultCount: { subscribe: resultCount.subscribe },
		isLoading: { subscribe: isLoading.subscribe },
		hasError: { subscribe: hasError.subscribe },

		setQuery: (query: string) => {
			store.update((state) => ({ ...state, query }));
		},

		executeSearch: async (query: string) => {
			store.update((state) => ({
				...state,
				query,
				loading: true,
				error: null,
				hasSearched: true
			}));

			try {
				const response = await searchService.search(query, 10);
				store.update((state) => ({
					...state,
					results: response.results || [],
					loading: false,
					error: null
				}));
			} catch (error) {
				const errorMessage = error instanceof ApiError
					? error.message
					: error instanceof Error ? error.message : 'Search failed';
				store.update((state) => ({
					...state,
					error: errorMessage,
					loading: false,
					results: []
				}));
				throw error;
			}
		},

		clear: () => {
			store.set(initialState);
		},

		getState: () => {
			let state: SearchState;
			store.subscribe((s) => {
				state = s;
			})();
			return state!;
		}
	};
}
