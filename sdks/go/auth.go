package creditassessment

// Auth provides request headers for authentication.
type Auth interface {
	Headers() map[string]string
}

// ApiKeyAuth authenticates via X-API-Key header.
type ApiKeyAuth struct {
	apiKey string
}

// NewApiKeyAuth creates an API key authenticator.
func NewApiKeyAuth(apiKey string) *ApiKeyAuth {
	return &ApiKeyAuth{apiKey: apiKey}
}

func (a *ApiKeyAuth) Headers() map[string]string {
	return map[string]string{"X-API-Key": a.apiKey}
}

func (a *ApiKeyAuth) String() string {
	return "ApiKeyAuth(***)"
}

// BearerAuth authenticates via Authorization: Bearer header.
type BearerAuth struct {
	token string
}

// NewBearerAuth creates a bearer token authenticator.
func NewBearerAuth(token string) *BearerAuth {
	return &BearerAuth{token: token}
}

func (b *BearerAuth) Headers() map[string]string {
	return map[string]string{"Authorization": "Bearer " + b.token}
}

func (b *BearerAuth) String() string {
	return "BearerAuth(***)"
}
