<script lang="ts">
	import { Button } from '$lib/components/ui/button';
	import SearchBar from '$lib/custom/SearchBar.svelte';
	import SearchResults from '$lib/custom/SearchResults.svelte';
	import { container } from '$lib/container';
	import { ApiError } from '$lib/api/errors';

	const searchStore = container.getSearchStore();

	let searchQuery = $state('');
	let errorMessage = $state('');

	// Watch searchStore.hasSearched and clear input when search is cleared
	$effect(() => {
		if (!$searchStore.hasSearched) {
			searchQuery = '';
		}
	});

	const exampleQueries = [
		'water quality monitoring UK',
		'biodiversity surveys',
		'land cover classification',
		'climate change impacts',
		'soil carbon data'
	];

	async function handleSearch(event: Event) {
		const customEvent = event as CustomEvent;
		const query = customEvent.detail?.query || searchQuery;

		if (!query.trim()) return;

		errorMessage = '';
		try {
			await searchStore.executeSearch(query);
		} catch (error) {
			if (error instanceof ApiError) {
				errorMessage = error.message;
			} else {
				errorMessage = error instanceof Error ? error.message : 'Search failed';
			}
			console.error('Search error:', error);
		}
	}

	function handleExampleClick(query: string) {
		searchQuery = query;
		// Trigger search after setting the query
		setTimeout(() => {
			const event = new CustomEvent('search', { detail: { query } });
			window.dispatchEvent(event);
		}, 0);
	}

	// Listen for custom search events
	if (typeof window !== 'undefined') {
		window.addEventListener('search', handleSearch);
	}
</script>

<svelte:head>
	<title>CEH Dataset Search</title>
	<meta name="description" content="Search and discover environmental datasets from the CEH Environmental Data Centre using natural language" />
</svelte:head>

<div class="search-page">
	<!-- Hero Section -->
	<div class="hero-section" class:hero-compact={$searchStore.hasSearched && $searchStore.results.length > 0}>
		<div class="hero-content">
			<h1 class="hero-title">Discover Environmental Datasets</h1>
			<p class="hero-subtitle">Search the CEH Environmental Data Centre using natural language. Find datasets about ecology, hydrology, land use, and more.</p>
		</div>

		<!-- Search Bar -->
		<div class="search-bar-wrapper">
			<SearchBar bind:value={searchQuery} loading={$searchStore.loading} />
		</div>

		<!-- Example Queries -->
		{#if !$searchStore.hasSearched || $searchStore.results.length === 0}
			<div class="examples-section">
				<p class="examples-label">Try these example searches:</p>
				<div class="examples-grid">
					{#each exampleQueries as query (query)}
						<button
							class="example-tag"
							onclick={() => handleExampleClick(query)}
							disabled={$searchStore.loading}
						>
							{query}
						</button>
					{/each}
				</div>
			</div>
		{/if}
	</div>

	<!-- Search Results -->
	{#if $searchStore.hasSearched || $searchStore.loading}
		<div class="results-section">
			<SearchResults
				results={$searchStore.results}
				loading={$searchStore.loading}
				error={$searchStore.error}
				hasSearched={$searchStore.hasSearched}
			/>
		</div>
	{/if}
</div>

<style>
	.search-page {
		width: 100%;
		max-width: 100%;
		margin: 0 auto;
		display: flex;
		flex-direction: column;
		height: 100%;
	}

	.hero-section {
		display: flex;
		flex-direction: column;
		gap: 2rem;
		padding: 2.5rem 2rem;
		transition: all 300ms ease-in-out;
		text-align: center;
		flex: 1;
		justify-content: center;
		align-items: center;
	}

	.hero-section.hero-compact {
		padding: 1.5rem 2rem;
		justify-content: flex-start;
		flex: 0;
	}

	.hero-content {
		display: flex;
		flex-direction: column;
		gap: 1rem;
		max-width: 900px;
		margin: 0 auto;
	}

	.hero-title {
		font-size: 3.5rem;
		font-weight: 700;
		letter-spacing: -0.02em;
		color: #1a202c;
		margin: 0;
		line-height: 1.1;
	}

	.hero-subtitle {
		font-size: 1.125rem;
		color: #64748b;
		margin: 0;
		line-height: 1.6;
		max-width: 800px;
		margin-left: auto;
		margin-right: auto;
	}

	.search-bar-wrapper {
		max-width: 600px;
		margin: 0 auto;
		width: 100%;
	}

	.examples-section {
		max-width: 700px;
		margin: 0 auto;
		width: 100%;
	}

	.examples-label {
		font-size: 0.95rem;
		font-weight: 500;
		color: #64748b;
		text-align: center;
		margin: 0 0 1rem 0;
	}

	.examples-grid {
		display: flex;
		flex-wrap: wrap;
		gap: 0.75rem;
		justify-content: center;
	}

	.example-tag {
		padding: 0.5rem 1rem;
		border: 1px solid #cbd5e1;
		border-radius: 0.375rem;
		background-color: #ffffff;
		color: #1a5c47;
		font-size: 0.875rem;
		font-weight: 500;
		cursor: pointer;
		transition: all 0.2s ease-in-out;
		text-decoration: none;
	}

	.example-tag:hover:not(:disabled) {
		background-color: #1a5c47;
		color: #ffffff;
		border-color: #1a5c47;
	}

	.example-tag:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.results-section {
		width: 100%;
		padding: 2rem;
		overflow-y: auto;
	}

	@media (max-width: 1024px) {
		.hero-title {
			font-size: 2.5rem;
		}

		.hero-subtitle {
			font-size: 1rem;
		}
	}

	@media (max-width: 768px) {
		.hero-section {
			padding: 1.5rem 1rem;
			gap: 1.5rem;
		}

		.hero-title {
			font-size: 2rem;
		}

		.hero-subtitle {
			font-size: 0.95rem;
		}

		.examples-grid {
			display: flex;
			flex-direction: column;
			gap: 0.5rem;
		}

		.example-tag {
			width: 100%;
		}

		.results-section {
			padding: 1.5rem;
		}
	}

	@media (max-width: 480px) {
		.hero-section {
			padding: 1rem;
			gap: 1rem;
		}

		.hero-title {
			font-size: 1.5rem;
		}

		.hero-subtitle {
			font-size: 0.875rem;
		}

		.search-bar-wrapper {
			max-width: 100%;
		}

		.results-section {
			padding: 1rem;
		}
	}
</style>
