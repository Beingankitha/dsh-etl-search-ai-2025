<script lang="ts">
	import '../app.css';
	import './layout.css';
	import favicon from '$lib/assets/favicon.svg';
	import { page } from '$app/stores';
	import { Search, MessageSquare } from 'lucide-svelte';

	let { children } = $props();

	const navItems = [
		{ icon: Search, href: '/', title: 'Search' },
		{ icon: MessageSquare, href: '/chat', title: 'Chat' }
	];

	function isActive(href: string) {
		return $page.url.pathname === href;
	}
</script>

<svelte:head><link rel="icon" href={favicon} /></svelte:head>

<div class="layout-container">
	<!-- Header -->
	<header class="header">
		<div class="header-content">
			<div class="logo">
				<h1 class="logo-text">CEH Dataset Search</h1>
			</div>

			<!-- Navigation Icons -->
			<nav class="nav-icons">
				{#each navItems as item (item.href)}
					<a
						href={item.href}
						class="nav-icon"
						class:active={isActive(item.href)}
						title={item.title}
					>
						<svelte:component this={item.icon} size={20} />
					</a>
				{/each}
			</nav>
		</div>
	</header>

	<!-- Main Content -->
	<main class="main-content">
		{@render children()}
	</main>

	<!-- Footer -->
	<footer class="footer">
		<div class="footer-content">
			<p class="footer-text">CEH Dataset Discovery System | Data from <a href="https://catalogue.ceh.ac.uk" target="_blank" rel="noopener noreferrer">CEH Environmental Data Centre</a></p>
		</div>
	</footer>
</div>

<style>
	:global(body) {
		margin: 0;
		padding: 0;
	}
</style>
