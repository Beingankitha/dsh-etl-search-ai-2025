<script lang="ts">
	import ChatInterface from '$lib/custom/ChatInterface.svelte';
</script>

<svelte:head>
	<title>Chat Assistant - Dataset Explorer</title>
	<meta name="description" content="Chat with the dataset discovery assistant" />
</svelte:head>

<div class="chat-page">
	<!-- Page Header -->
	<div class="page-header">
		<div class="header-content">
			<h1 class="page-title">Dataset Assistant</h1>
			<p class="page-subtitle">Ask questions about environmental datasets in the CEH catalogue</p>
		</div>
	</div>

	<!-- Chat Interface -->
	<div class="chat-wrapper">
		<ChatInterface />
	</div>

	<!-- Tips Section -->
	<div class="tips-section">
		<div class="tips-content">
			<h3 class="tips-title">💡 Tips for Better Results</h3>
			<ul class="tips-list">
				<li>Be specific in your queries - mention topics or geographic areas</li>
				<li>Ask about dataset characteristics like format, time range, or resolution</li>
				<li>Reference previous questions in the conversation for more accurate results</li>
				<li>Request datasets by specific themes or sectors</li>
				<li>Ask the assistant to explain relationships between datasets</li>
			</ul>
		</div>
	</div>
</div>

<style>
	.chat-page {
		display: flex;
		flex-direction: column;
		height: 100%;
		gap: 0;
	}

	.page-header {
		background: linear-gradient(135deg, var(--primary) 0%, var(--primary) 100%);
		color: white;
		padding: 1.5rem 1rem;
		text-align: center;
		flex-shrink: 0;
	}

	.header-content {
		max-width: 42rem;
		margin: 0 auto;
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.page-title {
		font-size: 2.5rem;
		font-weight: bold;
		margin: 0;
		line-height: 1.2;
	}

	.page-subtitle {
		font-size: 1rem;
		margin: 0;
		opacity: 0.95;
		line-height: 1.4;
	}

	.chat-wrapper {
		flex: 1;
		display: flex;
		flex-direction: column;
		padding: 1.5rem 1rem;
		max-width: 64rem;
		margin: 0 auto;
		width: 100%;
		overflow: hidden;
	}

	.tips-section {
		background-color: var(--secondary);
		border-top: 1px solid var(--border);
		padding: 1rem;
		flex-shrink: 0;
		max-height: 200px;
		overflow-y: auto;
	}

	.tips-content {
		max-width: 64rem;
		margin: 0 auto;
	}

	.tips-title {
		margin: 0 0 0.5rem 0;
		font-size: 1rem;
		font-weight: 600;
	}

	.tips-list {
		list-style: none;
		padding: 0;
		margin: 0;
		font-size: 0.85rem;
	}

	.tips-list li {
		padding: 0.25rem 0 0.25rem 1.5rem;
		position: relative;
	}

	.tips-list li:before {
		content: "✓";
		position: absolute;
		left: 0;
		color: var(--primary);
		font-weight: bold;
	}

	@media (max-width: 768px) {
		.page-header {
			padding: 1.25rem 0.75rem;
		}

		.page-title {
			font-size: 1.75rem;
		}

		.page-subtitle {
			font-size: 0.9rem;
		}

		.chat-wrapper {
			padding: 1rem 0.75rem;
		}

		.tips-section {
			padding: 0.75rem;
		}

		.tips-title {
			font-size: 0.9rem;
		}

		.tips-list {
			font-size: 0.75rem;
		}
	}

	@media (max-width: 480px) {
		.page-header {
			padding: 1rem 0.5rem;
		}

		.page-title {
			font-size: 1.5rem;
		}

		.page-subtitle {
			font-size: 0.85rem;
		}

		.chat-wrapper {
			padding: 0.75rem 0.5rem;
		}

		.tips-section {
			padding: 0.5rem;
		}
	}
</style>
