<script lang="ts">
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import ChatMessage from './ChatMessage.svelte';
	import { Send, Trash2, Loader2 } from 'lucide-svelte';
	import { container } from '$lib/container';
	import { ApiError } from '$lib/api/errors';
	import type { ChatMessage as ChatMessageType } from '$lib/api/types';
	import { onMount } from 'svelte';

	const chatStore = container.getChatStore();

	let messageInput = $state('');
	let scrollContainer: HTMLDivElement | null = null;
	let errorMessage = $state('');

	const welcomeMessage: ChatMessageType = {
		role: 'assistant',
		content: 'Hello! I am a dataset discovery assistant. Ask me anything about environmental datasets in the CEH catalogue.'
	};

	onMount(() => {
		const state = chatStore.getState();
		// Add welcome message if empty
		if (state.messages.length === 0) {
			chatStore.addMessage(welcomeMessage);
		}
	});

	function autoScroll() {
		setTimeout(() => {
			if (scrollContainer) {
				scrollContainer.scrollTop = scrollContainer.scrollHeight;
			}
		}, 0);
	}

	async function handleSendMessage() {
		if (!messageInput.trim() || $chatStore.loading) return;

		const userMessage = messageInput;
		messageInput = '';
		errorMessage = '';

		try {
			await chatStore.sendMessage(userMessage);
			autoScroll();
		} catch (error) {
			if (error instanceof ApiError) {
				errorMessage = error.message;
			} else {
				errorMessage = error instanceof Error ? error.message : 'Failed to send message';
			}
			console.error('Chat error:', error);
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' && !e.shiftKey && !$chatStore.loading) {
			e.preventDefault();
			handleSendMessage();
		}
	}

	function handleClear() {
		if (confirm('Are you sure you want to clear the conversation?')) {
			chatStore.clear();
			messageInput = '';
			errorMessage = '';
		}
	}

	$effect(() => {
		if ($chatStore.messages.length > 0) {
			autoScroll();
		}
	});
</script>

<div class="chat-interface">
	<!-- Header -->
	<div class="chat-header">
		<h2 class="chat-title">Dataset Assistant</h2>
		<Button
			variant="ghost"
			size="sm"
			onclick={handleClear}
			disabled={$chatStore.messages.length === 0 || $chatStore.loading}
			title="Clear conversation"
		>
			<Trash2 size={18} />
		</Button>
	</div>

	<!-- Messages Container -->
	<div class="messages-container" bind:this={scrollContainer}>
		{#each $chatStore.messages as message}
			<ChatMessage {message} />
		{/each}

		{#if $chatStore.loading}
			<div class="typing-indicator">
				<div class="typing-dot"></div>
				<div class="typing-dot"></div>
				<div class="typing-dot"></div>
			</div>
		{/if}

		{#if $chatStore.error}
			<div class="error-message">
				<span>Error: {$chatStore.error}</span>
			</div>
		{/if}
	</div>

	<!-- Input Area -->
	<div class="input-area">
		<div class="input-wrapper">
			<Input
				bind:value={messageInput}
				placeholder="Ask about datasets..."
				disabled={$chatStore.loading}
				onkeydown={handleKeydown}
				class="message-input"
			/>
			<Button
				onclick={handleSendMessage}
				disabled={!messageInput.trim() || $chatStore.loading}
				class="send-button"
			>
				{#if $chatStore.loading}
					<Loader2 size={18} class="animate-spin" />
				{:else}
					<Send size={18} />
				{/if}
			</Button>
		</div>
	</div>
</div>

<style>
	.chat-interface {
		display: flex;
		flex-direction: column;
		height: 100%;
		max-height: calc(100vh - 150px);
	}

	.chat-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 1rem;
		border-bottom: 1px solid var(--border);
		background-color: var(--secondary);
	}

	.chat-title {
		margin: 0;
		font-size: 1.125rem;
		font-weight: 600;
	}

	.messages-container {
		flex: 1;
		overflow-y: auto;
		padding: 1.5rem;
		display: flex;
		flex-direction: column;
	}

	.messages-container::-webkit-scrollbar {
		width: 0.5rem;
	}

	.messages-container::-webkit-scrollbar-track {
		background: transparent;
	}

	.messages-container::-webkit-scrollbar-thumb {
		background: var(--border);
		border-radius: 0.25rem;
	}

	.messages-container::-webkit-scrollbar-thumb:hover {
		background: var(--muted-foreground);
	}

	.typing-indicator {
		display: flex;
		gap: 0.375rem;
		padding: 1rem 0;
	}

	.typing-dot {
		width: 0.5rem;
		height: 0.5rem;
		border-radius: 50%;
		background-color: var(--muted-foreground);
		animation: typing 1.4s infinite;
	}

	.typing-dot:nth-child(2) {
		animation-delay: 0.2s;
	}

	.typing-dot:nth-child(3) {
		animation-delay: 0.4s;
	}

	@keyframes typing {
		0%,
		60%,
		100% {
			opacity: 0.5;
			transform: translateY(0);
		}
		30% {
			opacity: 1;
			transform: translateY(-0.75rem);
		}
	}

	.error-message {
		padding: 0.75rem 1rem;
		background-color: #fee2e2;
		border: 1px solid #fecaca;
		border-radius: 0.5rem;
		color: #dc2626;
		font-size: 0.875rem;
	}

	.dark .error-message {
		background-color: #7f1d1d;
		border-color: #991b1b;
		color: #fca5a5;
	}

	.input-area {
		padding: 1rem;
		border-top: 1px solid var(--border);
		background-color: var(--background);
	}

	.input-wrapper {
		display: flex;
		gap: 0.5rem;
		max-width: 100%;
	}

	.message-input {
		flex: 1;
		height: 2.75rem;
		resize: none;
	}

	.send-button {
		height: 2.75rem;
		min-width: 3rem;
		padding: 0 1.5rem;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	@media (max-width: 768px) {
		.chat-interface {
			max-height: calc(100vh - 100px);
		}

		.messages-container {
			padding: 1rem;
		}

		.message-input {
			font-size: 0.875rem;
		}

		.send-button {
			min-width: 2.75rem;
			padding: 0 1rem;
		}
	}
</style>
