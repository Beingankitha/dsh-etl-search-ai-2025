// place files you want to import through the `$lib` alias in this folder.

// Export API
export * from './api/client';
export * from './api/types';
export * from './api/errors';
export { HttpClient } from './api/http-client';

// Export services
export { DefaultSearchApiService, type SearchApiService } from './services/search.service';
export { DefaultChatApiService, type ChatApiService } from './services/chat.service';
export {
	SearchQueryValidator,
	ChatMessageValidator,
	ResponseValidator,
	ValidationError as ServiceValidationError
} from './services/validation.service';

// Export stores factory functions
export { createSearchStore } from './stores/searchStore';
export { createChatStore } from './stores/chatStore';

// Export container
export { container, getSearchStore, getChatStore, getSearchService, getChatService } from './container';
// Export logging utilities
export { logger, initializeLogger, getLogger } from './logger';
export type { LogLevel } from './logger';