<script lang="ts">
	import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '$lib/components/ui/card';
	import { Badge } from '$lib/components/ui/badge';
	import { ExternalLink } from 'lucide-svelte';
	import type { SearchResult } from '$lib/api/types';

	interface Props {
		result: SearchResult;
	}

	let { result } = $props();

	let dataset = $derived(result.dataset);
	let relevancePercent = $derived(Math.round(result.score * 100));

	// Get display keywords (max 4)
	let displayKeywords = $derived(dataset.keywords.slice(0, 4));
	let extraKeywordCount = $derived(Math.max(0, dataset.keywords.length - 4));

	// Truncate abstract to 200 chars
	let truncatedAbstract = $derived(
		dataset.abstract.length > 200 
			? dataset.abstract.substring(0, 200) + '...' 
			: dataset.abstract
	);

	// Build CEH catalogue URL
	let cehUrl = $derived(`https://catalogue.ceh.ac.uk/documents/${dataset.file_identifier}`);
</script>

<Card class="dataset-card">
	<CardHeader>
		<div class="card-title-wrapper">
			<CardTitle>{dataset.title}</CardTitle>
			<Badge class="relevance-badge">{relevancePercent}%</Badge>
		</div>
		{#if dataset.topic_category.length > 0}
			<Badge class="category-badge">{dataset.topic_category[0]}</Badge>
		{/if}
	</CardHeader>

	<CardContent class="card-content-wrapper">
		<CardDescription>
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
	:global(.dataset-card) {
		transition: box-shadow 200ms ease, transform 200ms ease, border-color 200ms ease !important;
		height: 100%;
		display: flex;
		flex-direction: column;
		border: 2px solid #1a5c47 !important;
	}

	:global(.dataset-card:hover) {
		box-shadow: 0 10px 25px rgb(0 0 0 / 0.1) !important;
		transform: translateY(-2px);
		border-color: #0d3a2e !important;
	}

	:global(.dark .dataset-card) {
		border-color: #4ade80 !important;
	}

	:global(.dark .dataset-card:hover) {
		box-shadow: 0 10px 25px rgb(0 0 0 / 0.3) !important;
		border-color: #22c55e !important;
	}

	.card-title-wrapper {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: 1rem;
	}

	:global(.dataset-title) {
		flex: 1;
		display: -webkit-box;
		-webkit-line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
		font-size: 1.125rem;
		line-height: 1.4;
		margin: 0;
	}

	:global(.relevance-badge) {
		flex-shrink: 0;
		font-weight: 600;
		background-color: #1a5c47 !important;
		color: white !important;
		border: none !important;
	}

	:global(.dark .relevance-badge) {
		background-color: #4ade80 !important;
		color: #0f172a !important;
	}

	:global(.category-badge) {
		margin-top: 0.5rem;
		font-size: 0.75rem;
	}

	:global(.card-content-wrapper) {
		flex: 1;
		display: flex;
		flex-direction: column;
		gap: 1rem;
		padding-top: 0;
	}

	:global(.dataset-abstract) {
		line-height: 1.5;
		color: var(--muted-foreground);
		margin: 0;
	}

	.keywords-wrapper {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
	}

	:global(.keyword-badge) {
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
		:global(.dataset-title) {
			font-size: 1rem;
		}

		.keywords-wrapper {
			gap: 0.25rem;
		}

		:global(.keyword-badge) {
			font-size: 0.7rem;
			padding: 0.25rem 0.5rem;
		}
	}
</style>
