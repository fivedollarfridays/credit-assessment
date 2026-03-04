package creditassessment

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strconv"
	"strings"
	"time"
)

// ClientOption configures the Client.
type ClientOption func(*Client)

// WithAuth sets the authentication method.
func WithAuth(auth Auth) ClientOption {
	return func(c *Client) { c.auth = auth }
}

// WithTimeout sets the HTTP timeout.
func WithTimeout(d time.Duration) ClientOption {
	return func(c *Client) { c.httpClient.Timeout = d }
}

// Client is a typed Go client for the Credit Assessment API.
type Client struct {
	baseURL    string
	auth       Auth
	httpClient *http.Client
}

// NewClient creates a new API client.
func NewClient(baseURL string, opts ...ClientOption) *Client {
	c := &Client{
		baseURL:    strings.TrimRight(baseURL, "/"),
		httpClient: &http.Client{Timeout: 30 * time.Second},
	}
	for _, opt := range opts {
		opt(c)
	}
	return c
}

func (c *Client) headers() http.Header {
	h := http.Header{"Content-Type": {"application/json"}}
	if c.auth != nil {
		for k, v := range c.auth.Headers() {
			h.Set(k, v)
		}
	}
	return h
}

func (c *Client) handleError(resp *http.Response, body []byte) error {
	switch {
	case resp.StatusCode == 401 || resp.StatusCode == 403:
		return &AuthenticationError{ApiError{Message: string(body), StatusCode: resp.StatusCode}}
	case resp.StatusCode == 422:
		var parsed struct {
			Detail []map[string]any `json:"detail"`
		}
		_ = json.Unmarshal(body, &parsed)
		return &ValidationError{
			ApiError: ApiError{Message: string(body), StatusCode: 422},
			Details:  parsed.Detail,
		}
	case resp.StatusCode == 429:
		var retryAfter *int
		if ra := resp.Header.Get("Retry-After"); ra != "" {
			if v, err := strconv.Atoi(ra); err == nil {
				retryAfter = &v
			}
		}
		return &RateLimitError{
			ApiError:   ApiError{Message: string(body), StatusCode: 429},
			RetryAfter: retryAfter,
		}
	default:
		return &ApiError{Message: string(body), StatusCode: resp.StatusCode}
	}
}

// Assess runs a credit assessment.
func (c *Client) Assess(profile CreditProfile) (*AssessmentResult, error) {
	payload, err := json.Marshal(profile)
	if err != nil {
		return nil, fmt.Errorf("marshal profile: %w", err)
	}

	req, err := http.NewRequest("POST", c.baseURL+"/v1/assess", bytes.NewReader(payload))
	if err != nil {
		return nil, fmt.Errorf("create request: %w", err)
	}
	req.Header = c.headers()

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("http request: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("read body: %w", err)
	}

	if resp.StatusCode >= 400 {
		return nil, c.handleError(resp, body)
	}

	var result AssessmentResult
	if err := json.Unmarshal(body, &result); err != nil {
		return nil, fmt.Errorf("unmarshal result: %w", err)
	}
	return &result, nil
}

// Health checks the API health endpoint.
func (c *Client) Health() (map[string]any, error) {
	resp, err := c.httpClient.Get(c.baseURL + "/health")
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var data map[string]any
	if err := json.NewDecoder(resp.Body).Decode(&data); err != nil {
		return nil, err
	}
	return data, nil
}

// GetDisclosures retrieves FCRA disclosures.
func (c *Client) GetDisclosures() (map[string]any, error) {
	resp, err := c.httpClient.Get(c.baseURL + "/v1/disclosures")
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var data map[string]any
	if err := json.NewDecoder(resp.Body).Decode(&data); err != nil {
		return nil, err
	}
	return data, nil
}
