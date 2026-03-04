/**
 * Base API error.
 */
export class ApiError extends Error {
  readonly statusCode: number;

  constructor(message: string, statusCode: number = 500) {
    super(message);
    this.name = "ApiError";
    this.statusCode = statusCode;
  }
}

/**
 * Authentication failure (401/403).
 */
export class AuthenticationError extends ApiError {
  constructor(message: string) {
    super(message, 401);
    this.name = "AuthenticationError";
  }
}

/**
 * Rate limit exceeded (429).
 */
export class RateLimitError extends ApiError {
  readonly retryAfter?: number;

  constructor(message: string, retryAfter?: number) {
    super(message, 429);
    this.name = "RateLimitError";
    this.retryAfter = retryAfter;
  }
}

/**
 * Validation failure (422).
 */
export class ValidationError extends ApiError {
  readonly details: Record<string, unknown>[];

  constructor(message: string, details: Record<string, unknown>[] = []) {
    super(message, 422);
    this.name = "ValidationError";
    this.details = details;
  }
}
