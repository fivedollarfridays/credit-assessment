/**
 * Credit Assessment API client.
 */

import type { Auth } from "./auth.js";
import {
  ApiError,
  AuthenticationError,
  RateLimitError,
  ValidationError,
} from "./errors.js";
import { AssessmentResult, type CreditProfile } from "./models.js";

export interface ClientOptions {
  auth?: Auth;
  timeout?: number;
}

export class CreditAssessmentClient {
  readonly baseUrl: string;
  readonly timeout: number;
  private readonly auth?: Auth;

  constructor(baseUrl: string, options: ClientOptions = {}) {
    this.baseUrl = baseUrl.replace(/\/+$/, "");
    this.auth = options.auth;
    this.timeout = options.timeout ?? 30_000;
  }

  /** @internal */
  _headers(): Record<string, string> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    if (this.auth) {
      Object.assign(headers, this.auth.headers());
    }
    return headers;
  }

  private handleError(status: number, body: string, headers: Headers): never {
    if (status === 401 || status === 403) {
      throw new AuthenticationError(body);
    }
    if (status === 422) {
      const data = JSON.parse(body);
      throw new ValidationError("Validation error", data.detail ?? []);
    }
    if (status === 429) {
      const retry = headers.get("Retry-After");
      throw new RateLimitError(
        body,
        retry ? parseInt(retry, 10) : undefined,
      );
    }
    throw new ApiError(body, status);
  }

  async assess(profile: CreditProfile): Promise<AssessmentResult> {
    const resp = await fetch(`${this.baseUrl}/v1/assess`, {
      method: "POST",
      headers: this._headers(),
      body: JSON.stringify(profile.toDict()),
      signal: AbortSignal.timeout(this.timeout),
    });
    if (!resp.ok) {
      this.handleError(resp.status, await resp.text(), resp.headers);
    }
    return AssessmentResult.fromDict(await resp.json());
  }

  async health(): Promise<Record<string, unknown>> {
    const resp = await fetch(`${this.baseUrl}/health`, {
      signal: AbortSignal.timeout(this.timeout),
    });
    return resp.json();
  }

  async getDisclosures(): Promise<Record<string, unknown>> {
    const resp = await fetch(`${this.baseUrl}/v1/disclosures`, {
      signal: AbortSignal.timeout(this.timeout),
    });
    return resp.json();
  }
}
