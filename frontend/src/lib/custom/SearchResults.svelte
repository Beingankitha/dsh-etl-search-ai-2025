<script lang="ts">
	import DatasetCard from './DatasetCard.svelte';
	import { Loader2, AlertCircle, Search } from 'lucide-svelte';
	import type { SearchResult } from '$lib/api/types';

	interface Props {
		results: SearchResult[];
		loading?: boolean;
		error?: string | null;
		hasSearched?: boolean;
	}

	let { results = $bindable([]), loading = false, error = null, hasSearched = false } = $props();

	let resultCount = $derived(results.length);
</script>

<div class="search-results">
	<!-- Loading State -->
	{#if loading}
		<div class="state-container loading-state">
			<Loader2 size={48} class="spinner" />
			<p class="state-message">Searching datasets...</p>
			<p style="font-size: 0.875rem; opacity: 0.7; margin-top: 0.5rem;">This usually takes 1-2 seconds</p>
		</div>
	{/if}

	<!-- Error State -->
	{#if error && !loading}
		<div class="state-container error-state">
			<AlertCircle size={48} class="error-icon" />
			<p class="state-message error-message">{error}</p>
		</div>
	{/if}

	<!-- Empty State -->
	{#if !loading && !error && hasSearched && resultCount === 0}
		<div class="state-container empty-state">
			<Search size={48} class="empty-icon" />
			<p class="state-message">No datasets found</p>
			<p class="state-submessage">Try adjusting your search query</p>
		</div>
	{/if}

	<!-- Results State -->
	{#if resultCount > 0 && !loading && !error}
		<div class="results-container">
			<div class="results-header">
				<p class="results-count">Found {resultCount} dataset{resultCount !== 1 ? 's' : ''}</p>
			</div>

			<div class="results-grid">
				{#each results as result (result.dataset.file_identifier)}
					<DatasetCard {result} />
				{/each}
			</div>
		</div>
	{/if}
</div>

<style>
	.search-results {
		width: 100%;
		display: flex;
		flex-direction: column;
	}

	.state-container {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 1rem;
		padding: 3rem 1rem;
		text-align: center;
	}

	.loading-state {
		color: var(--muted-foreground);
	}

	:global(.spinner) {
		animation: spin 1s linear infinite;
		color: var(--primary);
	}

	@keyframes spin {
		from {
			transform: rotate(0deg);
		}
		to {
			transform: rotate(360deg);
		}
	}

	.error-state {
		color: #ef4444;
	}

	:global(.error-icon) {
		color: #ef4444;
	}

	.error-message {
		color: #ef4444;
	}

	.empty-state {
		color: var(--muted-foreground);
	}

	:global(.empty-icon) {
		color: var(--muted-foreground);
		opacity: 0.5;
	}

	.state-message {
		font-size: 1.125rem;
		font-weight: 500;
		margin: 0;
	}

	.state-submessage {
		font-size: 0.875rem;
		margin: 0;
		opacity: 0.7;
	}

	.results-container {
		display: flex;
		flex-direction: column;
		gap: 2rem;
	}

	.results-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 0 1rem;
		border-bottom: 2px solid var(--primary);
		padding-bottom: 1rem;
	}

	.results-count {
		font-size: 0.875rem;
		font-weight: 600;
		color: var(--primary);
		margin: 0;
	}

	.results-grid {
		display: grid;
		gap: 1.5rem;
		padding: 0 1rem;
	}

	@media (min-width: 640px) {
		.results-grid {
			grid-template-columns: repeat(2, 1fr);
		}
	}

	@media (min-width: 1024px) {
		.results-grid {
			grid-template-columns: repeat(3, 1fr);
		}
	}

	@media (max-width: 640px) {
		.state-container {
			padding: 2rem 1rem;
		}

		.state-message {
			font-size: 1rem;
		}

		.results-header {
			padding: 0 0.5rem;
		}

		.results-grid {
			padding: 0 0.5rem;
			gap: 1rem;
		}
	}
</style>
