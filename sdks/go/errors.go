package creditassessment

import "fmt"

// ApiError is the base error for all API failures.
type ApiError struct {
	Message    string
	StatusCode int
}

func (e *ApiError) Error() string {
	return fmt.Sprintf("API error %d: %s", e.StatusCode, e.Message)
}

// AuthenticationError indicates a 401/403 response.
type AuthenticationError struct {
	ApiError
}

func (e *AuthenticationError) Unwrap() error { return &e.ApiError }

// RateLimitError indicates a 429 response with an optional Retry-After hint.
type RateLimitError struct {
	ApiError
	RetryAfter *int
}

func (e *RateLimitError) Unwrap() error { return &e.ApiError }

// ValidationError indicates a 422 response with detail items.
type ValidationError struct {
	ApiError
	Details []map[string]any
}

func (e *ValidationError) Unwrap() error { return &e.ApiError }
