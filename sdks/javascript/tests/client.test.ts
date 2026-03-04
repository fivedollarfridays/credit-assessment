import { describe, it, expect } from "vitest";
import {
  CreditAssessmentClient,
  ApiKeyAuth,
  BearerAuth,
  AccountSummary,
  CreditProfile,
  AssessmentResult,
  ApiError,
  AuthenticationError,
  RateLimitError,
  ValidationError,
} from "../src/index.js";

// --- Auth ---

describe("ApiKeyAuth", () => {
  it("returns X-API-Key header", () => {
    const auth = new ApiKeyAuth("test-key-123");
    expect(auth.headers()).toEqual({ "X-API-Key": "test-key-123" });
  });

  it("hides key in toString", () => {
    const auth = new ApiKeyAuth("secret");
    expect(String(auth)).not.toContain("secret");
  });
});

describe("BearerAuth", () => {
  it("returns Authorization header", () => {
    const auth = new BearerAuth("jwt-token");
    expect(auth.headers()).toEqual({ Authorization: "Bearer jwt-token" });
  });

  it("hides token in toString", () => {
    const auth = new BearerAuth("secret-token");
    expect(String(auth)).not.toContain("secret-token");
  });
});

// --- Models ---

describe("AccountSummary", () => {
  it("creates with required fields", () => {
    const summary = new AccountSummary({ totalAccounts: 10, openAccounts: 5 });
    expect(summary.totalAccounts).toBe(10);
    expect(summary.openAccounts).toBe(5);
    expect(summary.closedAccounts).toBe(0);
    expect(summary.totalBalance).toBe(0);
  });

  it("serializes to dict with snake_case keys", () => {
    const summary = new AccountSummary({ totalAccounts: 3, openAccounts: 2 });
    const dict = summary.toDict();
    expect(dict).toHaveProperty("total_accounts", 3);
    expect(dict).toHaveProperty("open_accounts", 2);
    expect(dict).toHaveProperty("closed_accounts", 0);
  });
});

describe("CreditProfile", () => {
  it("creates with all fields", () => {
    const summary = new AccountSummary({ totalAccounts: 5, openAccounts: 3 });
    const profile = new CreditProfile({
      currentScore: 720,
      scoreBand: "good",
      overallUtilization: 0.3,
      accountSummary: summary,
      paymentHistoryPct: 0.98,
      averageAccountAgeMonths: 48,
    });
    expect(profile.currentScore).toBe(720);
    expect(profile.scoreBand).toBe("good");
    expect(profile.negativeItems).toEqual([]);
  });

  it("serializes to dict with snake_case keys", () => {
    const summary = new AccountSummary({ totalAccounts: 1, openAccounts: 1 });
    const profile = new CreditProfile({
      currentScore: 650,
      scoreBand: "fair",
      overallUtilization: 0.5,
      accountSummary: summary,
      paymentHistoryPct: 0.9,
      averageAccountAgeMonths: 24,
      negativeItems: ["late_payment"],
    });
    const dict = profile.toDict();
    expect(dict).toHaveProperty("current_score", 650);
    expect(dict).toHaveProperty("score_band", "fair");
    expect(dict).toHaveProperty("negative_items", ["late_payment"]);
    expect(dict.account_summary).toHaveProperty("total_accounts", 1);
  });
});

describe("AssessmentResult", () => {
  it("creates from API response dict", () => {
    const data = {
      barrier_severity: "low",
      readiness: { score: 85, label: "ready" },
      barrier_details: [],
      thresholds: [],
      dispute_pathway: {},
      eligibility: [],
      disclaimer: "Test disclaimer",
    };
    const result = AssessmentResult.fromDict(data);
    expect(result.barrierSeverity).toBe("low");
    expect(result.readinessScore).toBe(85);
    expect(result.disclaimer).toBe("Test disclaimer");
  });

  it("defaults missing fields", () => {
    const result = AssessmentResult.fromDict({});
    expect(result.barrierSeverity).toBe("");
    expect(result.readinessScore).toBe(0);
    expect(result.barrierDetails).toEqual([]);
    expect(result.disclaimer).toBe("");
  });
});

// --- Exceptions ---

describe("ApiError", () => {
  it("has message and status code", () => {
    const err = new ApiError("server error", 500);
    expect(err.message).toBe("server error");
    expect(err.statusCode).toBe(500);
    expect(err).toBeInstanceOf(Error);
  });
});

describe("AuthenticationError", () => {
  it("extends ApiError with 401 status", () => {
    const err = new AuthenticationError("unauthorized");
    expect(err.statusCode).toBe(401);
    expect(err).toBeInstanceOf(ApiError);
  });
});

describe("RateLimitError", () => {
  it("includes retryAfter", () => {
    const err = new RateLimitError("too many requests", 60);
    expect(err.statusCode).toBe(429);
    expect(err.retryAfter).toBe(60);
    expect(err).toBeInstanceOf(ApiError);
  });

  it("retryAfter is undefined when not provided", () => {
    const err = new RateLimitError("too many requests");
    expect(err.retryAfter).toBeUndefined();
  });
});

describe("ValidationError", () => {
  it("includes details array", () => {
    const details = [{ loc: ["body", "score"], msg: "required" }];
    const err = new ValidationError("invalid input", details);
    expect(err.statusCode).toBe(422);
    expect(err.details).toEqual(details);
    expect(err).toBeInstanceOf(ApiError);
  });
});

// --- Client ---

describe("CreditAssessmentClient", () => {
  it("stores base URL without trailing slash", () => {
    const client = new CreditAssessmentClient("https://api.example.com/");
    expect(client.baseUrl).toBe("https://api.example.com");
  });

  it("defaults timeout to 30s", () => {
    const client = new CreditAssessmentClient("https://api.example.com");
    expect(client.timeout).toBe(30000);
  });

  it("accepts auth option", () => {
    const auth = new ApiKeyAuth("key");
    const client = new CreditAssessmentClient("https://api.example.com", {
      auth,
    });
    expect(client).toBeDefined();
  });

  it("accepts custom timeout", () => {
    const client = new CreditAssessmentClient("https://api.example.com", {
      timeout: 5000,
    });
    expect(client.timeout).toBe(5000);
  });

  it("builds headers with auth", () => {
    const auth = new ApiKeyAuth("my-key");
    const client = new CreditAssessmentClient("https://api.example.com", {
      auth,
    });
    const headers = client["_headers"]();
    expect(headers).toHaveProperty("Content-Type", "application/json");
    expect(headers).toHaveProperty("X-API-Key", "my-key");
  });

  it("builds headers without auth", () => {
    const client = new CreditAssessmentClient("https://api.example.com");
    const headers = client["_headers"]();
    expect(headers).toHaveProperty("Content-Type", "application/json");
    expect(headers).not.toHaveProperty("X-API-Key");
    expect(headers).not.toHaveProperty("Authorization");
  });
});
