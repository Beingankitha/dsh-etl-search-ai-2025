<script lang="ts">
	import { Badge } from '$lib/components/ui/badge';
	import { ExternalLink, Database } from 'lucide-svelte';
	import type { SearchResult } from '$lib/api/types';

	interface Props {
		sources: SearchResult[];
	}

	let { sources = [] } = $props();

	// Build CEH catalogue URL
	function getCehUrl(fileIdentifier: string): string {
		return `https://catalogue.ceh.ac.uk/documents/${fileIdentifier}`;
	}

	// Truncate text to specified length
	function truncateText(text: string, maxLength: number): string {
		if (text.length <= maxLength) return text;
		return text.substring(0, maxLength) + '...';
	}
</script>

{#if sources.length > 0}
	<div class="sources-container">
		<div class="sources-header">
			<Database size={16} />
			<span class="sources-title">Sources ({sources.length})</span>
		</div>

		<div class="sources-list">
			{#each sources as source, index}
				<div class="source-item">
					<div class="source-number">{index + 1}</div>

					<div class="source-content">
						<h4 class="source-title">
							<a href={getCehUrl(source.dataset.file_identifier)} target="_blank" rel="noopener noreferrer" class="source-link">
								{truncateText(source.dataset.title, 100)}
								<ExternalLink size={14} />
							</a>
						</h4>

						{#if source.dataset.abstract}
							<p class="source-abstract">
								{truncateText(source.dataset.abstract, 150)}
							</p>
						{/if}

						<div class="source-meta">
							<span class="relevance-score">
								<Badge variant="outline" class="score-badge">{Math.round(source.score * 100)}% relevant</Badge>
							</span>

							{#if source.dataset.topic_category.length > 0}
								<span class="category">
									<Badge class="category-badge">{source.dataset.topic_category[0]}</Badge>
								</span>
							{/if}
						</div>

						{#if source.dataset.keywords.length > 0}
							<div class="keywords">
								{#each source.dataset.keywords.slice(0, 3) as keyword}
									<Badge variant="secondary" class="keyword-badge">{keyword}</Badge>
								{/each}
								{#if source.dataset.keywords.length > 3}
									<Badge variant="secondary" class="keyword-badge">+{source.dataset.keywords.length - 3}</Badge>
								{/if}
							</div>
						{/if}
					</div>
				</div>
			{/each}
		</div>
	</div>
{/if}

<style>
	.sources-container {
		margin-top: 1.5rem;
		padding: 1rem;
		background: linear-gradient(135deg, #f0fdf4 0%, #ecfdf5 100%);
		border: 1px solid #86efac;
		border-radius: 0.75rem;
	}

	:global(.dark) .sources-container {
		background: linear-gradient(135deg, #064e3b 0%, #0d3a2e 100%);
		border-color: #10b981;
	}

	.sources-header {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		margin-bottom: 1rem;
		padding-bottom: 0.75rem;
		border-bottom: 2px solid #86efac;
	}

	:global(.dark) .sources-header {
		border-bottom-color: #10b981;
	}

	.sources-title {
		font-weight: 600;
		font-size: 0.95rem;
		color: #15803d;
	}

	:global(.dark) .sources-title {
		color: #86efac;
	}

	.sources-list {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.source-item {
		display: flex;
		gap: 0.75rem;
		padding: 0.75rem;
		background: white;
		border: 1px solid #d1fae5;
		border-radius: 0.5rem;
		transition: all 0.2s ease;
	}

	:global(.dark) .source-item {
		background: #1f2937;
		border-color: #059669;
	}

	.source-item:hover {
		box-shadow: 0 2px 8px rgba(16, 185, 129, 0.1);
		border-color: #10b981;
	}

	:global(.dark) .source-item:hover {
		box-shadow: 0 2px 8px rgba(16, 185, 129, 0.2);
	}

	.source-number {
		flex-shrink: 0;
		display: flex;
		align-items: center;
		justify-content: center;
		width: 2rem;
		height: 2rem;
		background: linear-gradient(135deg, #86efac 0%, #6ee7b7 100%);
		color: white;
		border-radius: 50%;
		font-weight: 600;
		font-size: 0.875rem;
	}

	:global(.dark) .source-number {
		background: linear-gradient(135deg, #10b981 0%, #059669 100%);
	}

	.source-content {
		flex: 1;
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.source-title {
		margin: 0;
		font-size: 0.95rem;
		font-weight: 600;
		color: #1f2937;
	}

	:global(.dark) .source-title {
		color: #e5e7eb;
	}

	.source-link {
		display: inline-flex;
		align-items: center;
		gap: 0.375rem;
		color: #0891b2;
		text-decoration: none;
		transition: all 0.2s ease;
		word-break: break-word;
	}

	:global(.dark) .source-link {
		color: #06b6d4;
	}

	.source-link:hover {
		color: #0369a1;
		text-decoration: underline;
	}

	:global(.dark) .source-link:hover {
		color: #0891b2;
	}

	.source-abstract {
		margin: 0;
		font-size: 0.8rem;
		line-height: 1.4;
		color: #666;
	}

	:global(.dark) .source-abstract {
		color: #d1d5db;
	}

	.source-meta {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		flex-wrap: wrap;
	}

	.relevance-score {
		display: flex;
	}

	:global(.score-badge) {
		background: #dbeafe;
		border-color: #93c5fd;
		color: #1e40af;
		font-size: 0.75rem;
		padding: 0.25rem 0.5rem;
	}

	.category {
		display: flex;
	}

	.keywords {
		display: flex;
		gap: 0.375rem;
		flex-wrap: wrap;
	}

	/* Global styles for dynamically applied Badge classes */
	:global(.score-badge) {
		background: #eff6ff;
		border: 1px solid #bfdbfe;
		color: #1e40af;
		font-size: 0.75rem;
		padding: 0.25rem 0.5rem;
	}

	:global(.dark .score-badge) {
		background: #1e3a8a;
		border-color: #3b82f6;
		color: #93c5fd;
	}

	:global(.category-badge) {
		background: #f0e4ff;
		color: #6d28d9;
		font-size: 0.75rem;
		padding: 0.25rem 0.5rem;
	}

	:global(.dark .category-badge) {
		background: #4c1d95;
		color: #d8b4fe;
	}

	:global(.keyword-badge) {
		font-size: 0.7rem;
		padding: 0.2rem 0.4rem;
		background: #fef3c7;
		color: #92400e;
	}

	:global(.dark .keyword-badge) {
		background: #78350f;
		color: #fcd34d;
	}

	@media (max-width: 640px) {
		.sources-container {
			padding: 0.75rem;
			margin-top: 1rem;
		}

		.source-item {
			flex-direction: column;
			gap: 0.5rem;
		}

		.source-number {
			width: 1.75rem;
			height: 1.75rem;
			font-size: 0.8rem;
		}

		.source-title {
			font-size: 0.875rem;
		}

		.source-abstract {
			font-size: 0.75rem;
		}
	}
</style>
