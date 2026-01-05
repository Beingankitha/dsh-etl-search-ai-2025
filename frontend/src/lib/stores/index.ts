// Export store factory functions
export { createSearchStore } from './searchStore';
export { createChatStore } from './chatStore';

// For backward compatibility, also export from container
export { getSearchStore, getChatStore } from '$lib/container';
