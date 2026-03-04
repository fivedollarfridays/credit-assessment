/**
 * Authentication helpers for the Credit Assessment API.
 */

export interface Auth {
  headers(): Record<string, string>;
}

/**
 * API key authentication via X-API-Key header.
 */
export class ApiKeyAuth implements Auth {
  private readonly apiKey: string;

  constructor(apiKey: string) {
    this.apiKey = apiKey;
  }

  headers(): Record<string, string> {
    return { "X-API-Key": this.apiKey };
  }

  toString(): string {
    return "ApiKeyAuth(***)";
  }
}

/**
 * JWT Bearer token authentication.
 */
export class BearerAuth implements Auth {
  private readonly token: string;

  constructor(token: string) {
    this.token = token;
  }

  headers(): Record<string, string> {
    return { Authorization: `Bearer ${this.token}` };
  }

  toString(): string {
    return "BearerAuth(***)";
  }
}
