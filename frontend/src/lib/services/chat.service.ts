/**
 * Chat API Service
 * 
 * Encapsulates chat operations with:
 * - Message validation
 * - History management
 * - Error handling
 * - Response transformation
 */

import * as apiClient from '$lib/api/client';
import type { ChatMessage, ChatResponse } from '$lib/api/types';
import { ApiError } from '$lib/api/errors';

export interface ChatApiService {
	sendMessage(message: string, history?: ChatMessage[]): Promise<ChatResponse>;
	validateMessage(message: string): boolean;
}

export class DefaultChatApiService implements ChatApiService {
	validateMessage(message: string): boolean {
		const trimmed = message.trim();
		return trimmed.length > 0 && trimmed.length <= 5000;
	}

	async sendMessage(message: string, history: ChatMessage[] = []): Promise<ChatResponse> {
		// Validate input
		if (!this.validateMessage(message)) {
			throw new ApiError(400, 'Invalid message: must be between 1 and 5000 characters', false);
		}

		const sanitizedMessage = message.trim();

		try {
			const response = await apiClient.sendChatMessage(sanitizedMessage, history);

			// Ensure response has expected structure
			if (!response.message || !response.message.content) {
				throw new ApiError(500, 'Invalid response structure from server', false);
			}

			return response;
		} catch (error) {
			if (error instanceof ApiError) {
				throw error;
			}
			throw new ApiError(500, `Chat failed: ${error instanceof Error ? error.message : 'Unknown error'}`, false);
		}
	}
}
