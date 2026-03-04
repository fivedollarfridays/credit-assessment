package creditassessment

// AccountSummary represents a credit account summary.
type AccountSummary struct {
	TotalAccounts      int     `json:"total_accounts"`
	OpenAccounts       int     `json:"open_accounts"`
	ClosedAccounts     int     `json:"closed_accounts"`
	NegativeAccounts   int     `json:"negative_accounts"`
	CollectionAccounts int     `json:"collection_accounts"`
	TotalBalance       float64 `json:"total_balance"`
	TotalCreditLimit   float64 `json:"total_credit_limit"`
	MonthlyPayments    float64 `json:"monthly_payments"`
}

// CreditProfile is the request body for /v1/assess.
type CreditProfile struct {
	CurrentScore           int            `json:"current_score"`
	ScoreBand              string         `json:"score_band"`
	OverallUtilization     float64        `json:"overall_utilization"`
	AccountSummary         AccountSummary `json:"account_summary"`
	PaymentHistoryPct      float64        `json:"payment_history_pct"`
	AverageAccountAgeMonths int           `json:"average_account_age_months"`
	NegativeItems          []string       `json:"negative_items"`
}

// Readiness holds the readiness sub-object of an assessment response.
type Readiness struct {
	Score int    `json:"score"`
	Label string `json:"label"`
}

// AssessmentResult is the response from /v1/assess.
type AssessmentResult struct {
	BarrierSeverity string           `json:"barrier_severity"`
	Readiness       Readiness        `json:"readiness"`
	BarrierDetails  []map[string]any `json:"barrier_details"`
	Thresholds      []map[string]any `json:"thresholds"`
	DisputePathway  map[string]any   `json:"dispute_pathway"`
	Eligibility     []map[string]any `json:"eligibility"`
	Disclaimer      string           `json:"disclaimer"`
}
