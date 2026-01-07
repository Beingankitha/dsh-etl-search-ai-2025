import { writable, derived } from 'svelte/store';
import type { ChatMessage, SearchResult } from '$lib/api/types';
import type { ChatApiService } from '$lib/services/chat.service';
import { ApiError } from '$lib/api/errors';

interface MessageWithSources {
	message: ChatMessage;
	sources: SearchResult[];
}

interface ChatState {
	messages: ChatMessage[];
	messagesSources: Map<number, SearchResult[]>; // Map message index to sources
	loading: boolean;
	error: string | null;
}

const initialState: ChatState = {
	messages: [],
	messagesSources: new Map(),
	loading: false,
	error: null
};

/**
 * Creates a chat store with injected chat service
 * This removes the need for function passing and creates proper dependency injection
 */
export function createChatStore(chatService: ChatApiService) {
	const store = writable<ChatState>(initialState);

	// Derived stores
	const isLoading = derived(store, ($store) => $store.loading);
	const messageCount = derived(store, ($store) => $store.messages.length);
	const hasError = derived(store, ($store) => $store.error !== null);

	return {
		subscribe: store.subscribe,
		isLoading: { subscribe: isLoading.subscribe },
		messageCount: { subscribe: messageCount.subscribe },
		hasError: { subscribe: hasError.subscribe },

		addMessage: (message: ChatMessage) => {
			store.update((state) => ({
				...state,
				messages: [...state.messages, message],
				error: null
			}));
		},

		sendMessage: async (message: string) => {
			try {
				// Validate message
				if (!chatService.validateMessage(message)) {
					throw new ApiError(400, 'Invalid message', false);
				}

				// Add user message
				const userMessage: ChatMessage = { role: 'user', content: message };
				store.update((state) => ({
					...state,
					messages: [...state.messages, userMessage],
					loading: true,
					error: null
				}));

				// Get current messages for context
				let currentMessages: ChatMessage[] = [];
				store.subscribe((state) => {
					currentMessages = state.messages;
				})();

				// Send to API
				const response = await chatService.sendMessage(message, currentMessages);

				// Add assistant response with sources
				if (response.message) {
					store.update((state) => {
						const newMessages = [...state.messages, response.message];
						const newSources = new Map(state.messagesSources);
						// Store sources at the index of the assistant message
						newSources.set(newMessages.length - 1, response.sources || []);
						return {
							...state,
							messages: newMessages,
							messagesSources: newSources,
							loading: false,
							error: null
						};
					});
				}

				return response;
			} catch (error) {
				const errorMessage = error instanceof ApiError
					? error.message
					: error instanceof Error ? error.message : 'Chat failed';
				store.update((state) => ({
					...state,
					error: errorMessage,
					loading: false
				}));
				throw error;
			}
		},

		setError: (error: string | null) => {
			store.update((state) => ({
				...state,
				error,
				loading: false
			}));
		},

		clear: () => {
			store.set(initialState);
		},

		getState: () => {
			let state: ChatState;
			store.subscribe((s) => {
				state = s;
			})();
			return state!;
		},

		getSources: (messageIndex: number) => {
			let sources: SearchResult[] = [];
			store.subscribe((state) => {
				sources = state.messagesSources.get(messageIndex) || [];
			})();
			return sources;
		}
	};
}

