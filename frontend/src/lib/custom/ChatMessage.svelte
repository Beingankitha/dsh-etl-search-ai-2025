<script lang="ts">
	import { Badge } from '$lib/components/ui/badge';
	import { MessageCircle, User } from 'lucide-svelte';
	import type { ChatMessage } from '$lib/api/types';
	import type { SearchResult } from '$lib/api/types';

	interface Props {
		message: ChatMessage;
		sources?: SearchResult[];
	}

	const { message, sources = [] } = $props();

	const isUser = message.role === 'user';
	const isAssistant = message.role === 'assistant';
</script>

<div class="chat-message" class:user-message={isUser}>
	<div class="message-avatar">
		{#if isUser}
			<div class="avatar-circle user-avatar">
				<User size={18} />
			</div>
		{:else if isAssistant}
			<div class="avatar-circle assistant-avatar">
				<MessageCircle size={18} />
			</div>
		{/if}
	</div>

	<div class="message-content-wrapper">
		<div class="message-content" class:user-content={isUser} class:assistant-content={isAssistant}>
			<p class="message-text">
				{message.content}
			</p>
		</div>

		{#if sources && sources.length > 0 && isAssistant}
			<div class="sources-section">
				<p class="sources-label">Related datasets:</p>
				<div class="sources-list">
					{#each sources as source}
						<Badge variant="outline" class="source-badge">
							{source.dataset.title}
						</Badge>
					{/each}
				</div>
			</div>
		{/if}
	</div>
</div>

<style>
	.chat-message {
		display: flex;
		gap: 1rem;
		margin-bottom: 1rem;
		animation: fadeIn 200ms ease;
	}

	@keyframes fadeIn {
		from {
			opacity: 0;
			transform: translateY(10px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}

	.chat-message.user-message {
		flex-direction: row-reverse;
	}

	.message-avatar {
		flex-shrink: 0;
	}

	.avatar-circle {
		width: 2rem;
		height: 2rem;
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
		color: white;
	}

	.user-avatar {
		background-color: #3b82f6;
	}

	.assistant-avatar {
		background-color: #8b5cf6;
	}

	.message-content-wrapper {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		max-width: 70%;
	}

	.chat-message.user-message .message-content-wrapper {
		align-items: flex-end;
	}

	.message-content {
		padding: 0.75rem 1rem;
		border-radius: 0.75rem;
		word-wrap: break-word;
		white-space: pre-wrap;
	}

	.user-content {
		background-color: #3b82f6;
		color: white;
	}

	.dark .user-content {
		background-color: #2563eb;
	}

	.assistant-content {
		background-color: var(--secondary);
		color: var(--foreground);
	}

	.dark .assistant-content {
		background-color: #1e293b;
	}

	.message-text {
		margin: 0;
		line-height: 1.5;
	}

	.sources-section {
		padding: 0.5rem 0;
	}

	.sources-label {
		font-size: 0.75rem;
		font-weight: 600;
		color: var(--muted-foreground);
		margin: 0 0 0.5rem 0;
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.sources-list {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
	}

	.source-badge {
		font-size: 0.75rem;
		cursor: pointer;
		transition: background-color 200ms;
	}

	.source-badge:hover {
		background-color: var(--primary);
		color: var(--primary-foreground);
	}

	@media (max-width: 640px) {
		.message-content-wrapper {
			max-width: 85%;
		}

		.message-content {
			padding: 0.625rem 0.875rem;
			font-size: 0.875rem;
		}

		.avatar-circle {
			width: 1.75rem;
			height: 1.75rem;
		}

		.avatar-circle svg {
			width: 1rem;
			height: 1rem;
		}
	}
</style>
