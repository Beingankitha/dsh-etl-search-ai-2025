<script lang="ts">
	import { Search, Loader2 } from 'lucide-svelte';
	import { Input } from '$lib/components/ui/input';

	interface Props {
		value?: string;
		loading?: boolean;
		placeholder?: string;
	}

	let { value = $bindable(''), loading = false, placeholder = 'Search datasets...' } = $props();

	function handleSubmit() {
		if (value.trim()) {
			const event = new CustomEvent('search', { detail: { query: value } });
			window.dispatchEvent(event);
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' && !loading) {
			handleSubmit();
		}
	}
</script>

<div class="search-bar-container">
	<div class="search-bar-wrapper">
		<Input
			bind:value
			{placeholder}
			disabled={loading}
			onkeydown={handleKeydown}
			class="search-input"
		/>
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
		align-items: center;
	}

	.search-input {
		flex: 1;
		height: 2.75rem;
		font-size: 1rem;
		padding: 0.5rem 1rem;
		box-sizing: border-box;
	}

	:global(.search-input),
	:global(.search-input input) {
		height: 2.50rem !important;
		padding: 0.5rem 1rem !important;
		line-height: 1.75rem;
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

	.dark .search-button {
		background-color: #4ade80;
		color: #0f172a;
		box-shadow: 0 2px 8px rgba(74, 222, 128, 0.15);
	}

	.dark .search-button:hover:not(:disabled) {
		background-color: #22c55e;
		box-shadow: 0 4px 12px rgba(74, 222, 128, 0.3);
		transform: translateY(-1px);
	}

	.dark .search-button:active:not(:disabled) {
		background-color: #16a34a;
		box-shadow: 0 2px 6px rgba(74, 222, 128, 0.2);
		transform: translateY(0);
	}

	.dark .search-button:disabled {
		background-color: #4ade80;
		color: #0f172a;
	}

	@media (max-width: 640px) {
		.search-bar-wrapper {
			gap: 0.25rem;
		}

		.search-input {
			font-size: 0.875rem;
		}

		.search-button {
			min-width: 2.5rem;
			padding: 0 1rem;
			font-size: 0.875rem;
		}
	}
</style>
