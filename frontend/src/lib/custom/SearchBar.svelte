<script lang="ts">
	import { Search, Loader2 } from 'lucide-svelte';
	import { Input } from '$lib/components/ui/input';
	import { container } from '$lib/container';
	import { onDestroy } from 'svelte';

	interface Props {
		value?: string;
		loading?: boolean;
		placeholder?: string;
	}

	let { value = $bindable(''), loading = false, placeholder = 'Search datasets...' } = $props();
	
	let suggestions: string[] = $state([]);
	let showSuggestions = $state(false);
	let suggestionsLoading = $state(false);
	let selectedIndex = $state(-1);
	let debounceTimer: ReturnType<typeof setTimeout> | null = null;
	let abortController: AbortController | null = $state(null);
	const searchService = container.getSearchService();

	/**
	 * Fetch suggestions using the service layer
	 * Includes request cancellation to prevent stale requests
	 */
	async function fetchSuggestions(query: string) {
		if (!query.trim() || query.length < 1) {
			suggestions = [];
			showSuggestions = false;
			return;
		}

		// Cancel previous request if still pending
		if (abortController !== null) {
			abortController.abort();
		}
		
		// Create new abort controller for this request
		abortController = new AbortController();

		suggestionsLoading = true;
		try {
			// Use service layer for suggestions
			const result = await searchService.getSuggestions(query, 8);
			suggestions = result;
			showSuggestions = suggestions.length > 0;
			selectedIndex = -1;
		} catch (error) {
			// Only log errors if not aborted
			if (error instanceof Error && error.name !== 'AbortError') {
				console.debug('Suggestions fetch error (non-critical):', error);
			}
			suggestions = [];
			showSuggestions = false;
		} finally {
			suggestionsLoading = false;
		}
	}

	/**
	 * Handle input with debouncing
	 * Prevents excessive API calls while typing
	 */
	function handleInput(e: Event) {
		const target = e.target as HTMLInputElement;
		value = target.value;
		
		// Clear previous debounce
		if (debounceTimer) clearTimeout(debounceTimer);
		
		// Set new debounce timeout
		debounceTimer = setTimeout(() => {
			fetchSuggestions(value);
			debounceTimer = null;
		}, 300);
	}

	/**
	 * Cleanup on component destroy
	 */
	onDestroy(() => {
		if (debounceTimer) clearTimeout(debounceTimer);
		if (abortController !== null) abortController.abort();
	});

	function handleSubmit() {
		if (value.trim()) {
			const event = new CustomEvent('search', { detail: { query: value } });
			window.dispatchEvent(event);
			showSuggestions = false;
		}
	}

	function handleSuggestionClick(suggestion: string) {
		value = suggestion;
		showSuggestions = false;
		handleSubmit();
	}

	function handleKeydown(e: KeyboardEvent) {
		if (!showSuggestions || suggestions.length === 0) {
			if (e.key === 'Enter' && !loading) {
				handleSubmit();
			}
			return;
		}

		switch (e.key) {
			case 'ArrowDown':
				e.preventDefault();
				selectedIndex = Math.min(selectedIndex + 1, suggestions.length - 1);
				break;
			case 'ArrowUp':
				e.preventDefault();
				selectedIndex = Math.max(selectedIndex - 1, -1);
				break;
			case 'Enter':
				e.preventDefault();
				if (selectedIndex >= 0) {
					handleSuggestionClick(suggestions[selectedIndex]);
				} else {
					handleSubmit();
				}
				break;
			case 'Escape':
				e.preventDefault();
				showSuggestions = false;
				selectedIndex = -1;
				break;
		}
	}

	function handleFocus() {
		if (value.trim() && suggestions.length > 0) {
			showSuggestions = true;
		}
	}

	function handleBlur() {
		// Delay to allow clicking on suggestions
		setTimeout(() => {
			showSuggestions = false;
		}, 200);
	}
</script>

<div class="search-bar-container">
	<div class="search-bar-wrapper">
		<div class="search-input-wrapper">
			<Input
				bind:value
				{placeholder}
				disabled={loading}
				oninput={handleInput}
				onkeydown={handleKeydown}
				onfocus={handleFocus}
				onblur={handleBlur}
				class="search-input"
				autocomplete="off"
			/>
			
			{#if showSuggestions && suggestions.length > 0}
				<div class="suggestions-dropdown">
					{#each suggestions as suggestion, index}
						<button
							type="button"
							class="suggestion-item"
							class:selected={index === selectedIndex}
							onmousedown={() => handleSuggestionClick(suggestion)}
							onmousemove={() => (selectedIndex = index)}
						>
						<Search size={16} class="suggestion-icon" />
							<span>{suggestion}</span>
						</button>
					{/each}
				</div>
			{/if}
		</div>
		
		<button
			type="button"
			onclick={handleSubmit}
			disabled={!value.trim() || loading}
			class="search-button"
			aria-label="Search"
		>
			{#if loading}
				<Loader2 size={18} class="animate-spin" />
			{:else}
				<Search size={18} />
			{/if}
		</button>
	</div>
</div>

<style>
	.search-bar-container {
		width: 100%;
		display: flex;
		justify-content: center;
	}

	.search-bar-wrapper {
		display: flex;
		gap: 0.5rem;
		width: 100%;
		max-width: 42rem;
		align-items: flex-start;
	}

	.search-input-wrapper {
		flex: 1;
		position: relative;
	}

	:global(.search-input) {
		flex: 1;
		height: 2.75rem;
		font-size: 1rem;
		padding: 0.5rem 1rem;
		box-sizing: border-box;
		width: 100%;
	}

	:global(.search-input),
	:global(.search-input input) {
		height: 2.50rem !important;
		padding: 0.5rem 1rem !important;
		line-height: 1.75rem;
	}

	.suggestions-dropdown {
		position: absolute;
		top: 100%;
		left: 0;
		right: 0;
		background: white;
		border: 1px solid #e2e8f0;
		border-top: none;
		border-radius: 0 0 0.375rem 0.375rem;
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
		max-height: 300px;
		overflow-y: auto;
		z-index: 50;
	}

	:global(.dark .suggestions-dropdown) {
		background: #1e293b;
		border-color: #334155;
	}

	.suggestion-item {
		width: 100%;
		padding: 0.75rem 1rem;
		text-align: left;
		background: none;
		border: none;
		cursor: pointer;
		display: flex;
		align-items: center;
		gap: 0.75rem;
		font-size: 0.875rem;
		color: #64748b;
		transition: background-color 150ms;
	}

	.suggestion-item:hover,
	.suggestion-item.selected {
		background-color: #f1f5f9;
		color: #1a5c47;
	}

	:global(.dark .suggestion-item:hover),
	:global(.dark .suggestion-item.selected) {
		background-color: #334155;
		color: #4ade80;
	}

	:global(.suggestion-icon) {
		flex-shrink: 0;
		opacity: 0.5;
	}

	.search-button {
		height: 2.75rem;
		min-width: 3rem;
		padding: 0 1.5rem;
		display: flex;
		align-items: center;
		justify-content: center;
		background-color: #1a5c47;
		color: #ffffff;
		border: none;
		border-radius: 0.375rem;
		font-weight: 500;
		font-size: 1rem;
		line-height: 2.75rem;
		transition: all 0.2s ease-in-out;
		cursor: pointer;
		box-shadow: 0 2px 8px rgba(26, 92, 71, 0.15);
		flex-shrink: 0;
		margin: 0;
	}

	.search-button:hover:not(:disabled) {
		background-color: #0d3a2e;
		box-shadow: 0 4px 12px rgba(26, 92, 71, 0.3);
		transform: translateY(-1px);
	}

	.search-button:active:not(:disabled) {
		background-color: #082d23;
		box-shadow: 0 2px 6px rgba(26, 92, 71, 0.2);
		transform: translateY(0);
	}

	.search-button:disabled {
		opacity: 0.5;
		cursor: not-allowed;
		background-color: #1a5c47;
	}

	:global(.dark .search-button) {
		background-color: #4ade80;
		color: #0f172a;
		box-shadow: 0 2px 8px rgba(74, 222, 128, 0.15);
	}

	:global(.dark .search-button:hover:not(:disabled)) {
		background-color: #22c55e;
		box-shadow: 0 4px 12px rgba(74, 222, 128, 0.3);
		transform: translateY(-1px);
	}

	:global(.dark .search-button:active:not(:disabled)) {
		background-color: #16a34a;
		box-shadow: 0 2px 6px rgba(74, 222, 128, 0.2);
		transform: translateY(0);
	}

	:global(.dark .search-button:disabled) {
		background-color: #4ade80;
		color: #0f172a;
	}

	@media (max-width: 640px) {
		.search-bar-wrapper {
			gap: 0.25rem;
		}

		:global(.search-input) {
			font-size: 0.875rem;
		}

		.search-button {
			min-width: 2.5rem;
			padding: 0 1rem;
			font-size: 0.875rem;
		}

		.suggestions-dropdown {
			max-height: 250px;
		}

		.suggestion-item {
			padding: 0.5rem 0.75rem;
			font-size: 0.75rem;
		}
	}
</style>
