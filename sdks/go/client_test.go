package creditassessment

import (
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"
)

// --- Auth ---

func TestApiKeyAuthHeaders(t *testing.T) {
	auth := NewApiKeyAuth("test-key")
	h := auth.Headers()
	if h["X-API-Key"] != "test-key" {
		t.Fatalf("expected X-API-Key=test-key, got %s", h["X-API-Key"])
	}
}

func TestApiKeyAuthString(t *testing.T) {
	auth := NewApiKeyAuth("secret")
	if s := auth.String(); s != "ApiKeyAuth(***)" {
		t.Fatalf("unexpected String(): %s", s)
	}
}

func TestBearerAuthHeaders(t *testing.T) {
	auth := NewBearerAuth("jwt-token")
	h := auth.Headers()
	if h["Authorization"] != "Bearer jwt-token" {
		t.Fatalf("expected Bearer jwt-token, got %s", h["Authorization"])
	}
}

func TestBearerAuthString(t *testing.T) {
	auth := NewBearerAuth("secret")
	if s := auth.String(); s != "BearerAuth(***)" {
		t.Fatalf("unexpected String(): %s", s)
	}
}

// --- Models ---

func TestAccountSummaryJSON(t *testing.T) {
	s := AccountSummary{TotalAccounts: 10, OpenAccounts: 5}
	data, err := json.Marshal(s)
	if err != nil {
		t.Fatal(err)
	}
	var m map[string]any
	json.Unmarshal(data, &m)
	if m["total_accounts"] != float64(10) {
		t.Fatalf("expected 10, got %v", m["total_accounts"])
	}
}

func TestCreditProfileJSON(t *testing.T) {
	p := CreditProfile{
		CurrentScore:            720,
		ScoreBand:               "good",
		OverallUtilization:      0.3,
		AccountSummary:          AccountSummary{TotalAccounts: 5, OpenAccounts: 3},
		PaymentHistoryPct:       0.98,
		AverageAccountAgeMonths: 48,
		NegativeItems:           []string{},
	}
	data, _ := json.Marshal(p)
	var m map[string]any
	json.Unmarshal(data, &m)
	if m["current_score"] != float64(720) {
		t.Fatalf("expected 720, got %v", m["current_score"])
	}
	if m["score_band"] != "good" {
		t.Fatalf("expected good, got %v", m["score_band"])
	}
}

func TestAssessmentResultUnmarshal(t *testing.T) {
	raw := `{
		"barrier_severity": "low",
		"readiness": {"score": 85, "label": "ready"},
		"barrier_details": [],
		"thresholds": [],
		"dispute_pathway": {},
		"eligibility": [],
		"disclaimer": "Test"
	}`
	var r AssessmentResult
	if err := json.Unmarshal([]byte(raw), &r); err != nil {
		t.Fatal(err)
	}
	if r.BarrierSeverity != "low" {
		t.Fatalf("expected low, got %s", r.BarrierSeverity)
	}
	if r.Readiness.Score != 85 {
		t.Fatalf("expected 85, got %d", r.Readiness.Score)
	}
}

// --- Errors ---

func TestApiErrorInterface(t *testing.T) {
	var err error = &ApiError{Message: "fail", StatusCode: 500}
	if err.Error() != "API error 500: fail" {
		t.Fatalf("unexpected: %s", err.Error())
	}
}

func TestAuthenticationErrorType(t *testing.T) {
	err := &AuthenticationError{ApiError{Message: "denied", StatusCode: 401}}
	var apiErr *ApiError
	if !errors.As(err, &apiErr) {
		t.Fatal("AuthenticationError should unwrap to ApiError")
	}
}

func TestRateLimitRetryAfter(t *testing.T) {
	ra := 60
	err := &RateLimitError{
		ApiError:   ApiError{Message: "slow down", StatusCode: 429},
		RetryAfter: &ra,
	}
	if *err.RetryAfter != 60 {
		t.Fatalf("expected 60, got %d", *err.RetryAfter)
	}
}

func TestValidationErrorDetails(t *testing.T) {
	details := []map[string]any{{"loc": []any{"body", "score"}, "msg": "required"}}
	err := &ValidationError{
		ApiError: ApiError{Message: "invalid", StatusCode: 422},
		Details:  details,
	}
	if len(err.Details) != 1 {
		t.Fatalf("expected 1 detail, got %d", len(err.Details))
	}
}

// --- Client ---

func TestClientBaseURL(t *testing.T) {
	c := NewClient("https://api.example.com/")
	if c.baseURL != "https://api.example.com" {
		t.Fatalf("expected trimmed URL, got %s", c.baseURL)
	}
}

func TestClientDefaultTimeout(t *testing.T) {
	c := NewClient("https://api.example.com")
	if c.httpClient.Timeout != 30*time.Second {
		t.Fatalf("expected 30s, got %s", c.httpClient.Timeout)
	}
}

func TestClientCustomTimeout(t *testing.T) {
	c := NewClient("https://api.example.com", WithTimeout(5*time.Second))
	if c.httpClient.Timeout != 5*time.Second {
		t.Fatalf("expected 5s, got %s", c.httpClient.Timeout)
	}
}

func TestClientHeadersWithAuth(t *testing.T) {
	auth := NewApiKeyAuth("my-key")
	c := NewClient("https://api.example.com", WithAuth(auth))
	h := c.headers()
	if h.Get("X-API-Key") != "my-key" {
		t.Fatalf("expected X-API-Key=my-key, got %s", h.Get("X-API-Key"))
	}
	if h.Get("Content-Type") != "application/json" {
		t.Fatal("missing Content-Type header")
	}
}

func TestClientAssessSuccess(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/v1/assess" {
			t.Fatalf("unexpected path: %s", r.URL.Path)
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]any{
			"barrier_severity": "none",
			"readiness":        map[string]any{"score": 90, "label": "ready"},
			"barrier_details":  []any{},
			"thresholds":       []any{},
			"dispute_pathway":  map[string]any{},
			"eligibility":      []any{},
			"disclaimer":       "Test",
		})
	}))
	defer srv.Close()

	c := NewClient(srv.URL)
	result, err := c.Assess(CreditProfile{
		CurrentScore:       750,
		ScoreBand:          "excellent",
		OverallUtilization: 0.1,
		AccountSummary:     AccountSummary{TotalAccounts: 3, OpenAccounts: 2},
		PaymentHistoryPct:  1.0,
	})
	if err != nil {
		t.Fatal(err)
	}
	if result.BarrierSeverity != "none" {
		t.Fatalf("expected none, got %s", result.BarrierSeverity)
	}
	if result.Readiness.Score != 90 {
		t.Fatalf("expected 90, got %d", result.Readiness.Score)
	}
}

func TestClientAssess401(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(401)
		w.Write([]byte("unauthorized"))
	}))
	defer srv.Close()

	c := NewClient(srv.URL)
	_, err := c.Assess(CreditProfile{})
	var authErr *AuthenticationError
	if !errors.As(err, &authErr) {
		t.Fatalf("expected AuthenticationError, got %T: %v", err, err)
	}
}

func TestClientAssess429(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Retry-After", "30")
		w.WriteHeader(429)
		w.Write([]byte("rate limited"))
	}))
	defer srv.Close()

	c := NewClient(srv.URL)
	_, err := c.Assess(CreditProfile{})
	var rlErr *RateLimitError
	if !errors.As(err, &rlErr) {
		t.Fatalf("expected RateLimitError, got %T", err)
	}
	if *rlErr.RetryAfter != 30 {
		t.Fatalf("expected RetryAfter=30, got %d", *rlErr.RetryAfter)
	}
}

func TestClientHealth(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/health" {
			t.Fatalf("unexpected path: %s", r.URL.Path)
		}
		json.NewEncoder(w).Encode(map[string]any{"status": "ok"})
	}))
	defer srv.Close()

	c := NewClient(srv.URL)
	data, err := c.Health()
	if err != nil {
		t.Fatal(err)
	}
	if data["status"] != "ok" {
		t.Fatalf("expected ok, got %v", data["status"])
	}
}
