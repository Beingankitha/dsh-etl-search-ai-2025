<script lang="ts">
	import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '$lib/components/ui/card';
	import { Badge } from '$lib/components/ui/badge';
	import { ExternalLink } from 'lucide-svelte';
	import type { SearchResult } from '$lib/api/types';

	interface Props {
		result: SearchResult;
	}

	const { result } = $props();

	const dataset = result.dataset;
	const relevancePercent = Math.round(result.score * 100);

	// Get display keywords (max 4)
	const displayKeywords = dataset.keywords.slice(0, 4);
	const extraKeywordCount = Math.max(0, dataset.keywords.length - 4);

	// Truncate abstract to 200 chars
	const truncatedAbstract = dataset.abstract.length > 200 
		? dataset.abstract.substring(0, 200) + '...' 
		: dataset.abstract;

	// Build CEH catalogue URL
	const cehUrl = `https://catalogue.ceh.ac.uk/documents/${dataset.file_identifier}`;
</script>

<Card class="dataset-card">
	<CardHeader>
		<div class="card-title-wrapper">
			<CardTitle class="dataset-title">{dataset.title}</CardTitle>
			<Badge variant="outline" class="relevance-badge">{relevancePercent}%</Badge>
		</div>
		{#if dataset.topic_category.length > 0}
			<Badge class="category-badge">{dataset.topic_category[0]}</Badge>
		{/if}
	</CardHeader>

	<CardContent class="card-content-wrapper">
		<CardDescription class="dataset-abstract">
			{truncatedAbstract}
		</CardDescription>

		<div class="keywords-wrapper">
			{#each displayKeywords as keyword}
				<Badge variant="secondary" class="keyword-badge">{keyword}</Badge>
			{/each}
			{#if extraKeywordCount > 0}
				<Badge variant="secondary" class="keyword-badge">+{extraKeywordCount}</Badge>
			{/if}
		</div>

		<a href={cehUrl} target="_blank" rel="noopener noreferrer" class="ceh-link">
			<span>View in CEH Catalogue</span>
			<ExternalLink size={16} />
		</a>
	</CardContent>
</Card>

<style>
	.dataset-card {
		transition: box-shadow 200ms ease, transform 200ms ease;
		height: 100%;
		display: flex;
		flex-direction: column;
	}

	.dataset-card:hover {
		box-shadow: 0 10px 25px rgb(0 0 0 / 0.1);
		transform: translateY(-2px);
	}

	.dark .dataset-card:hover {
		box-shadow: 0 10px 25px rgb(0 0 0 / 0.3);
	}

	.card-title-wrapper {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: 1rem;
	}

	.dataset-title {
		flex: 1;
		display: -webkit-box;
		-webkit-line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
		font-size: 1.125rem;
		line-height: 1.4;
		margin: 0;
	}

	.relevance-badge {
		flex-shrink: 0;
		font-weight: 600;
	}

	.category-badge {
		margin-top: 0.5rem;
		font-size: 0.75rem;
	}

	.card-content-wrapper {
		flex: 1;
		display: flex;
		flex-direction: column;
		gap: 1rem;
		padding-top: 0;
	}

	.dataset-abstract {
		line-height: 1.5;
		color: var(--muted-foreground);
		margin: 0;
	}

	.keywords-wrapper {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
	}

	.keyword-badge {
		font-size: 0.75rem;
	}

	.ceh-link {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		margin-top: auto;
		color: var(--primary);
		text-decoration: none;
		font-size: 0.875rem;
		font-weight: 500;
		transition: opacity 200ms;
	}

	.ceh-link:hover {
		opacity: 0.8;
	}

	@media (max-width: 768px) {
		.dataset-title {
			font-size: 1rem;
		}

		.keywords-wrapper {
			gap: 0.25rem;
		}

		.keyword-badge {
			font-size: 0.7rem;
			padding: 0.25rem 0.5rem;
		}
	}
</style>
